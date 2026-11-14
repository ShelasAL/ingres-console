"""
Coverage Detector: rule-based pre-answer check that identifies
incomplete coverage, ambiguous locations, or unsupported requests.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional

import duckdb
from loguru import logger

CoverageStatus = Literal["FULL", "PARTIAL", "INSUFFICIENT", "OUT_OF_SCOPE"]

# Data coverage constants
MIN_YEAR = 2015
MAX_YEAR = 2023
MIN_WELLS_FOR_TREND = 3
MIN_READINGS_FOR_TREND = 3
STATES_WITH_QUALITY_DATA = {
    "Rajasthan", "Maharashtra", "Gujarat", "Punjab",
    "Uttar Pradesh", "Bihar", "Andhra Pradesh", "Tamil Nadu",
    "Karnataka", "Telangana",
}


@dataclass
class CoverageResult:
    status: CoverageStatus
    message: str
    available_summary: dict = field(default_factory=dict)
    suggestion: str = ""
    missing_fraction: float = 0.0   # 0-1 fraction of missing data


def _extract_year(text: str) -> list[int]:
    return [int(y) for y in re.findall(r"\b(19\d{2}|2\d{3})\b", text)]


def _extract_locations(text: str, entities: dict) -> list[str]:
    locs = entities.get("locations", [])
    if not locs:
        # Try pattern match
        locs = re.findall(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)?\b", text)
    return [l.lower() for l in locs]


# ── Individual rules ──────────────────────────────────────────────────────────

def _check_temporal(query: str, entities: dict) -> Optional[CoverageResult]:
    """Rule 1: Temporal out-of-range."""
    years = _extract_year(query)
    if not years:
        return None
    too_old = [y for y in years if y < MIN_YEAR]
    future   = [y for y in years if y > MAX_YEAR]
    if too_old:
        return CoverageResult(
            status="OUT_OF_SCOPE",
            message=(f"Data is only available from {MIN_YEAR} onwards. "
                     f"Requested year(s) {too_old} are not in the database."),
            suggestion=f"Try the same query for {MIN_YEAR}–{MAX_YEAR}.",
            available_summary={"earliest_year": MIN_YEAR, "latest_year": MAX_YEAR},
        )
    if future:
        return CoverageResult(
            status="OUT_OF_SCOPE",
            message=f"Year(s) {future} are in the future. No forecast data is available.",
            suggestion=f"Try the same query for the most recent available year ({MAX_YEAR}).",
        )
    return None


def _check_location_ambiguity(query: str, entities: dict,
                               con: duckdb.DuckDBPyConnection) -> Optional[CoverageResult]:
    """Rule 2: Ambiguous or vague location."""
    vague_phrases = ["north india", "south india", "east india", "west india",
                     "central india", "near river", "near the river", "somewhere",
                     "rural area", "drought region", "the drought region"]
    q_lower = query.lower()
    if any(p in q_lower for p in vague_phrases):
        return CoverageResult(
            status="INSUFFICIENT",
            message="Location reference is too vague to retrieve specific data.",
            suggestion="Please specify a district or state name (e.g., 'Jaipur, Rajasthan').",
        )

    locs = entities.get("locations", [])
    if not locs:
        return None

    # Check if location exists in DB
    for loc in locs:
        count = con.execute(
            "SELECT COUNT(*) FROM wells WHERE LOWER(district)=? OR LOWER(state)=?",
            [loc.lower(), loc.lower()]
        ).fetchone()[0]
        if count == 0:
            # Check for close matches
            matches = con.execute(
                "SELECT DISTINCT district FROM wells WHERE LOWER(district) LIKE ?",
                [f"%{loc.lower()[:4]}%"]
            ).fetchall()
            candidates = [m[0] for m in matches[:5]]
            return CoverageResult(
                status="INSUFFICIENT",
                message=f"Location '{loc}' not found in the database.",
                suggestion=f"Did you mean: {', '.join(candidates)}?" if candidates else
                           "Please use a district or state name from the supported list.",
                available_summary={"candidates": candidates},
            )
    return None


def _check_parameter_availability(query: str, entities: dict,
                                   con: duckdb.DuckDBPyConnection) -> Optional[CoverageResult]:
    """Rule 3: Parameter exists in database for the requested region."""
    locs = entities.get("locations", [])
    q_lower = query.lower()

    # Arsenic check — only available in select states
    if "arsenic" in q_lower and locs:
        for loc in locs:
            count = con.execute(
                """SELECT COUNT(*) FROM gw_quality q
                   JOIN wells w ON q.well_id=w.well_id
                   WHERE (LOWER(w.district)=? OR LOWER(w.state)=?)
                     AND q.arsenic_ug_l IS NOT NULL""",
                [loc.lower(), loc.lower()]
            ).fetchone()[0]
            if count == 0:
                return CoverageResult(
                    status="PARTIAL",
                    message=f"Arsenic data is not available for '{loc}' in the database.",
                    suggestion="Arsenic data is available for Bihar, Andhra Pradesh, and select UP districts.",
                    missing_fraction=1.0,
                )
    return None


def _check_measurement_count(query: str, entities: dict,
                              con: duckdb.DuckDBPyConnection) -> Optional[CoverageResult]:
    """Rule 4: Ensure enough readings exist for trend analysis."""
    trend_keywords = ["trend", "rising", "falling", "declining", "increasing",
                      "over years", "change", "evolution"]
    q_lower = query.lower()
    if not any(kw in q_lower for kw in trend_keywords):
        return None

    locs = entities.get("locations", [])
    if not locs:
        return None

    for loc in locs:
        year_count = con.execute(
            """SELECT COUNT(DISTINCT EXTRACT(YEAR FROM l.measurement_date))
               FROM gw_levels l
               JOIN wells w ON l.well_id=w.well_id
               WHERE (LOWER(w.district)=? OR LOWER(w.state)=?)
                 AND l.data_quality_flag != 'missing'""",
            [loc.lower(), loc.lower()]
        ).fetchone()[0]

        if year_count < MIN_READINGS_FOR_TREND:
            return CoverageResult(
                status="INSUFFICIENT",
                message=(f"Only {year_count} year(s) of data available for '{loc}'. "
                         f"Trend analysis requires at least {MIN_READINGS_FOR_TREND} years."),
                suggestion="Choose a location with longer monitoring history.",
                available_summary={"available_years": year_count},
                missing_fraction=1.0 - (year_count / MIN_READINGS_FOR_TREND),
            )
        if year_count < 6:
            return CoverageResult(
                status="PARTIAL",
                message=(f"Only {year_count} years of data available for '{loc}'. "
                         "Trend may not be statistically robust."),
                suggestion="Interpret trend with caution given limited data.",
                available_summary={"available_years": year_count},
                missing_fraction=0.3,
            )
    return None


def _check_well_density(query: str, entities: dict,
                         con: duckdb.DuckDBPyConnection) -> Optional[CoverageResult]:
    """Rule 5: Warn if fewer than 2 wells cover the queried district."""
    locs = entities.get("locations", [])
    if not locs:
        return None
    for loc in locs:
        well_count = con.execute(
            "SELECT COUNT(*) FROM wells WHERE LOWER(district)=?",
            [loc.lower()]
        ).fetchone()[0]
        if 0 < well_count < 2:
            return CoverageResult(
                status="PARTIAL",
                message=(f"Only {well_count} monitoring well(s) exist for '{loc}'. "
                         "Spatial representativeness is limited."),
                suggestion="Results represent a single monitoring point; interpret with caution.",
                available_summary={"well_count": well_count},
                missing_fraction=0.5,
            )
    return None


RULES = [
    _check_temporal,
    _check_location_ambiguity,
    _check_parameter_availability,
    _check_measurement_count,
    _check_well_density,
]


def check_coverage(query: str, entities: dict,
                   con: duckdb.DuckDBPyConnection) -> CoverageResult:
    """
    Run all coverage rules and return the most severe finding.
    Priority: OUT_OF_SCOPE > INSUFFICIENT > PARTIAL > FULL
    """
    results: list[CoverageResult] = []
    for rule in RULES:
        try:
            result = rule(query, entities, con) if rule.__code__.co_argcount == 3 else \
                     rule(query, entities)
            if result is not None:
                results.append(result)
        except Exception as e:
            logger.warning(f"Coverage rule {rule.__name__} failed: {e}")

    if not results:
        return CoverageResult(
            status="FULL",
            message="Data coverage appears complete for this query.",
            available_summary={},
        )

    priority = {"OUT_OF_SCOPE": 0, "INSUFFICIENT": 1, "PARTIAL": 2, "FULL": 3}
    return min(results, key=lambda r: priority.get(r.status, 4))

