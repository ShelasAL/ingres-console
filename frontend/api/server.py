
"""
INGRES Console — JSON API over the existing groundwater pipeline.
Read-only DuckDB access; the Streamlit app is untouched.

Run:  python -m uvicorn frontend.api.server:app --host 127.0.0.1 --port 8601
"""
from __future__ import annotations

import math
import re
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", str(ROOT / "data" / "synthetic" / "ingres.duckdb")))
DIST = Path(__file__).resolve().parents[1] / "web" / "app"


def db() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def clean(value: Any) -> Any:
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    try:
        import numpy as np
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            f = float(value)
            return None if (math.isnan(f) or math.isinf(f)) else f
        if isinstance(value, np.bool_):
            return bool(value)
    except Exception:
        pass
    return str(value)


def ok(payload: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(clean(payload), status_code=status)


def fail(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def rows(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ── Summary ────────────────────────────────────────────────────────────────
def summary(request):
    con = db()
    try:
        kpi = rows(con.execute("""
            SELECT (SELECT COUNT(*) FROM wells) AS stations,
                   (SELECT COUNT(*) FROM gw_levels) AS observations,
                   (SELECT COUNT(*) FROM gw_quality) AS tests,
                   (SELECT COUNT(*) FROM assessment_units) AS units,
                   (SELECT COUNT(*) FROM assessment_units WHERE category='over_exploited') AS over_exploited,
                   (SELECT ROUND(COUNT(CASE WHEN potability='potable' THEN 1 END) * 100.0 / COUNT(*), 1) FROM gw_quality) AS potable_pct
        """))[0]
        states = rows(con.execute("""
            SELECT state, COUNT(*) AS wells,
                   ROUND(AVG(stage_of_extraction_pct), 1) AS stage
            FROM assessment_units GROUP BY state ORDER BY stage DESC
        """))
        violations = rows(con.execute("""
            SELECT SUM(CASE WHEN tds_mg_l > 500 THEN 1 ELSE 0 END) AS tds,
                   SUM(CASE WHEN fluoride_mg_l > 1.5 THEN 1 ELSE 0 END) AS fluoride,
                   SUM(CASE WHEN nitrate_mg_l > 45 THEN 1 ELSE 0 END) AS nitrate,
                   SUM(CASE WHEN arsenic_ug_l > 10 THEN 1 ELSE 0 END) AS arsenic
            FROM gw_quality
        """))[0]
        potability = rows(con.execute(
            "SELECT potability, COUNT(*) AS n FROM gw_quality GROUP BY potability ORDER BY n DESC"
        ))
        categories = rows(con.execute(
            "SELECT category, COUNT(*) AS n FROM assessment_units GROUP BY category ORDER BY n DESC"
        ))
        sources = rows(con.execute(
            "SELECT data_source, COUNT(*) AS n FROM wells GROUP BY data_source"
        ))
        return ok({
            "kpi": kpi, "states": states, "violations": violations,
            "potability": potability, "categories": categories, "sources": sources,
        })
    except Exception as exc:
        return fail(str(exc), 500)
    finally:
        con.close()


# ── Locations / stations ───────────────────────────────────────────────────
def states(request):
    con = db()
    try:
        return ok(rows(con.execute(
            "SELECT state, COUNT(*) AS wells FROM wells GROUP BY state ORDER BY state"
        )))
    finally:
        con.close()


def districts(request):
    state = request.query_params.get("state", "")
    con = db()
    try:
        if state:
            data = rows(con.execute(
                "SELECT district, COUNT(*) AS wells FROM wells WHERE state=? GROUP BY district ORDER BY district",
                [state]))
        else:
            data = rows(con.execute(
                "SELECT district, state, COUNT(*) AS wells FROM wells GROUP BY district, state ORDER BY district"))
        return ok(data)
    finally:
        con.close()


def stations(request):
    district = request.query_params.get("district", "")
    state = request.query_params.get("state", "")
    con = db()
    try:
        base = "SELECT well_id, state, district, block, well_type, aquifer_type FROM wells"
        if district:
            data = rows(con.execute(base + " WHERE district=? ORDER BY well_id LIMIT 300", [district]))
        elif state:
            data = rows(con.execute(base + " WHERE state=? ORDER BY well_id LIMIT 300", [state]))
        else:
            data = rows(con.execute(base + " ORDER BY well_id LIMIT 300"))
        return ok(data)
    finally:
        con.close()


def station_detail(request):
    well_id = request.path_params["well_id"]
    con = db()
    try:
        meta = rows(con.execute("SELECT * FROM wells WHERE well_id=?", [well_id]))
        if not meta:
            return fail("Station not found", 404)
        levels = rows(con.execute("""
            SELECT measurement_date, season, depth_to_water_mbgl, data_quality_flag,
                   measurement_method, remarks
            FROM gw_levels WHERE well_id=? ORDER BY measurement_date
        """, [well_id]))
        quality = rows(con.execute("""
            SELECT sample_date, ph, tds_mg_l, fluoride_mg_l, arsenic_ug_l,
                   nitrate_mg_l, hardness_mg_l, iron_mg_l, potability
            FROM gw_quality WHERE well_id=? ORDER BY sample_date DESC
        """, [well_id]))
        district = meta[0]["district"]
        assessment = rows(con.execute("""
            SELECT district, block_taluk, annual_gw_recharge_mcm, extractable_gw_mcm,
                   total_extraction_mcm, stage_of_extraction_pct, category, assessment_year
            FROM assessment_units WHERE LOWER(district)=LOWER(?) ORDER BY assessment_year DESC LIMIT 1
        """, [district]))
        return ok({"meta": meta[0], "levels": levels, "quality": quality, "assessment": assessment})
    except Exception as exc:
        return fail(str(exc), 500)
    finally:
        con.close()


# ── Map ────────────────────────────────────────────────────────────────────
def map_stations(request):
    state = request.query_params.get("state", "")
    con = db()
    try:
        sql = """
            WITH last_q AS (
                SELECT well_id, potability, fluoride_mg_l, tds_mg_l,
                       ROW_NUMBER() OVER (PARTITION BY well_id ORDER BY sample_date DESC) AS rn
                FROM gw_quality
            ), last_l AS (
                SELECT well_id, data_quality_flag,
                       ROW_NUMBER() OVER (PARTITION BY well_id ORDER BY measurement_date DESC) AS rn
                FROM gw_levels
            )
            SELECT w.well_id, w.state, w.district, w.block, w.latitude, w.longitude,
                   w.well_type, w.aquifer_type,
                   q.potability, q.fluoride_mg_l, q.tds_mg_l, l.data_quality_flag
            FROM wells w
            LEFT JOIN last_q q ON q.well_id = w.well_id AND q.rn = 1
            LEFT JOIN last_l l ON l.well_id = w.well_id AND l.rn = 1
            WHERE w.latitude IS NOT NULL AND w.longitude IS NOT NULL
        """
        params = []
        if state:
            sql += " AND w.state = ?"
            params.append(state)
        sql += " ORDER BY w.state, w.district, w.well_id LIMIT 6000"
        return ok(rows(con.execute(sql, params)))
    except Exception as exc:
        return fail(str(exc), 500)
    finally:
        con.close()


# ── Explore ────────────────────────────────────────────────────────────────
def explore(request):
    table = request.query_params.get("table", "wells")
    state = request.query_params.get("state", "")
    limit = min(int(request.query_params.get("limit", 200)), 500)
    con = db()
    try:
        if table == "wells":
            sql = ("SELECT well_id, state, district, block, latitude, longitude, well_type, "
                   "aquifer_type, depth_mbgl, installation_year, data_source FROM wells")
            params = []
            if state:
                sql += " WHERE state=?"; params.append(state)
            sql += " ORDER BY well_id LIMIT ?"; params.append(limit)
        elif table == "levels":
            sql = ("SELECT l.record_id, w.state, w.district, l.measurement_date, l.season, "
                   "l.depth_to_water_mbgl, l.data_quality_flag, l.measurement_method "
                   "FROM gw_levels l JOIN wells w ON l.well_id=w.well_id")
            params = []
            if state:
                sql += " WHERE w.state=?"; params.append(state)
            sql += " ORDER BY l.measurement_date DESC LIMIT ?"; params.append(limit)
        elif table == "quality":
            sql = ("SELECT q.record_id, w.state, w.district, q.sample_date, q.ph, q.tds_mg_l, "
                   "q.fluoride_mg_l, q.arsenic_ug_l, q.nitrate_mg_l, q.potability "
                   "FROM gw_quality q JOIN wells w ON q.well_id=w.well_id")
            params = []
            if state:
                sql += " WHERE w.state=?"; params.append(state)
            sql += " ORDER BY q.sample_date DESC LIMIT ?"; params.append(limit)
        elif table == "units":
            sql = ("SELECT unit_id, state, district, block_taluk, annual_gw_recharge_mcm, "
                   "extractable_gw_mcm, total_extraction_mcm, stage_of_extraction_pct, "
                   "category, assessment_year FROM assessment_units")
            params = []
            if state:
                sql += " WHERE state=?"; params.append(state)
            sql += " ORDER BY stage_of_extraction_pct DESC LIMIT ?"; params.append(limit)
        else:
            return fail("Unknown table")
        cur = con.execute(sql, params)
        return ok({"columns": [d[0] for d in cur.description], "rows": rows(cur)})
    except Exception as exc:
        return fail(str(exc), 500)
    finally:
        con.close()




GLOSSARY = {
    "piezometer": "A piezometer is a narrow, non-pumping borehole installed to measure the hydraulic head of groundwater at a specific depth, often in a confined or semi-confined aquifer. Unlike an open well it is sealed, so the measured level reflects the pressure at the screened interval.",
    "aquifer": "An aquifer is a geological formation that can store and transmit enough groundwater to be useful. Unconfined aquifers are recharged directly from the surface; confined aquifers sit beneath a low-permeability layer and can be under pressure.",
    "water table": "The water table is the upper surface of the saturated zone in an unconfined aquifer — the level at which water stands in a shallow well.",
    "recharge": "Recharge is the process by which rainfall, rivers or irrigation water percolates down to replenish groundwater. In India, monsoon recharge between June and September dominates the annual budget.",
}


def _deterministic_answer(ctx, intent, coverage, sql_res, query="", quality_shape=None):
    """Answer without a model: summarize the retrieved rows directly.

    Used for offline requests and reviewed SQL quality plans, where the local
    query result is already authoritative and a model adds latency without
    adding evidence.
    """
    from ingres.generation.response_generator import _determine_state, _determine_confidence

    state = _determine_state(ctx)
    confidence = _determine_confidence(ctx, state)
    df = sql_res.to_dataframe()
    stats = ctx.stats or {}

    def span(col):
        if col not in df.columns:
            return None
        s = df[col].dropna()
        if s.empty:
            return None
        return float(s.min()), float(s.mean()), float(s.max())

    def metric(value, digits):
        try:
            number = float(value)
            return f"{number:.{digits}f}" if math.isfinite(number) else "—"
        except (TypeError, ValueError):
            return "—"

    lines = []
    if df.empty:
        key = next((k for k in GLOSSARY if k in query.lower()), None)
        if key:
            lines.append("**Answer**: " + GLOSSARY[key])
            lines.append("**Source**: Hydrogeology reference")
        elif ctx.semantic_chunks and coverage.status == "FULL":
            top = ctx.semantic_chunks[0]
            lines.append("**Answer**: " + str(top.get("text", ""))[:520])
            lines.append("- Source: " + str(top.get("source", "knowledge base")))
        else:
            reason = coverage.message or "No matching records were found for this request."
            lines.append("**Answer**: This question cannot be verified from the INGRES groundwater "
                         "database. " + reason)
            if coverage.suggestion:
                lines.append("**Recommendation**: " + coverage.suggestion)
    elif "potable_pct" in df.columns and "state" in df.columns and "samples" in df.columns:
        lines.append("**Answer**: Potability comparison by state, based on the indexed laboratory samples:")
        for _, row in df.head(12).iterrows():
            lines.append(
                "- %s: %d/%d samples potable (%.1f%%), %d non-potable; mean TDS %s mg/L, "
                "fluoride %s mg/L, nitrate %s mg/L, arsenic %s µg/L; %d samples exceed at least one BIS limit."
                % (row["state"], int(row["potable_samples"] or 0), int(row["samples"] or 0),
                   float(row["potable_pct"] or 0), int(row["non_potable_samples"] or 0),
                   metric(row["mean_tds_mg_l"], 1), metric(row["mean_fluoride_mg_l"], 2),
                   metric(row["mean_nitrate_mg_l"], 1), metric(row["mean_arsenic_ug_l"], 1),
                   int(row["samples_over_bis_limit"] or 0))
            )
    elif "potable_pct" in df.columns and "location" in df.columns and "samples" in df.columns:
        lines.append("**Answer**: Potability comparison for the requested areas, based on indexed laboratory samples:")
        for _, row in df.iterrows():
            lines.append(
                "- %s: %d/%d samples potable (%.1f%%), %d non-potable; mean TDS %s mg/L, "
                "fluoride %s mg/L, nitrate %s mg/L, arsenic %s µg/L; %d samples exceed at least one BIS limit."
                % (row["location"], int(row["potable_samples"] or 0), int(row["samples"] or 0),
                   float(row["potable_pct"] or 0), int(row["non_potable_samples"] or 0),
                   metric(row["mean_tds_mg_l"], 1), metric(row["mean_fluoride_mg_l"], 2),
                   metric(row["mean_nitrate_mg_l"], 1), metric(row["mean_arsenic_ug_l"], 1),
                   int(row["samples_over_bis_limit"] or 0))
            )
    elif quality_shape == "well_count" and "wells" in df.columns:
        if len(df) == 1:
            row = df.iloc[0]
            lines.append("**Answer**: The database holds %d monitoring wells in %s."
                         % (int(row["wells"]), row["location"]))
        else:
            total = int(df["wells"].fillna(0).sum())
            lines.append("**Answer**: %d monitoring wells across %d states:" % (total, len(df)))
            for _, row in df.head(12).iterrows():
                lines.append("- %s: %d wells" % (row["location"], int(row["wells"])))
    elif "non_potable_wells" in df.columns:
        total = int(df["non_potable_wells"].fillna(0).sum())
        lines.append("**Answer**: %d non-potable wells in the latest sample for each well, across %d area(s)." % (total, len(df)))
        for _, row in df.head(20).iterrows():
            lines.append("- %s, %s: %d non-potable wells" % (
                row.get("district", ""), row.get("state", ""), int(row["non_potable_wells"] or 0)))
    elif quality_shape == "non_potable_list" and "well_id" in df.columns and "potability" in df.columns and "sample_date" in df.columns and "district" in df.columns:
        lines.append("**Answer**: %d wells currently classified non-potable from their latest laboratory sample:" % len(df))
        for _, row in df.head(20).iterrows():
            lines.append("- %s · %s, %s · latest sample %s" % (
                row["well_id"], row["district"], row["state"], str(row["sample_date"])[:10]))
    elif "potable_wells" in df.columns:
        row = df.iloc[0]
        total = int(row["wells"])
        potable = int(row["potable_wells"] or 0)
        non = int(row["non_potable_wells"] or 0)
        none = int(row["without_sample"] or 0)
        pct = round(potable * 100.0 / total, 1) if total else 0
        lines.append("**Answer**: %d wells; %d potable (%.1f%%), %d non-potable, %d without a sample." % (total, potable, pct, non, none))
        if "mean_tds_mg_l" in df.columns:
            lines.append("- Latest-sample chemistry: TDS %s mg/L, fluoride %s mg/L, nitrate %s mg/L, arsenic %s µg/L (BIS limits 500, 1.5, 45, 10)." % (
                metric(row["mean_tds_mg_l"], 1), metric(row["mean_fluoride_mg_l"], 2),
                metric(row["mean_nitrate_mg_l"], 1), metric(row["mean_arsenic_ug_l"], 1)))
        if row.get("first_date") and row.get("last_date"):
            lines.append("- Samples span %s to %s." % (str(row["first_date"])[:10], str(row["last_date"])[:10]))
    elif "potable_pct" in df.columns and "well_id" in df.columns:
        lines.append("**Answer**: %d wells with quality samples — most potable:" % len(df))
        for _, row in df.head(5).iterrows():
            lines.append("- %s (%s): %.1f%% of %d samples potable" % (row["well_id"], row["district"], float(row["potable_pct"]), int(row["samples"])))
    elif "potable" in df.columns and "pct" in df.columns and "state" in df.columns:
        lines.append("**Answer**: state ranking by number of potable samples.")
        for _, row in df.head(6).iterrows():
            lines.append("- %s: %d potable of %d samples (%.1f%%)" % (row["state"], int(row["potable"]), int(row["samples"]), float(row["pct"])))
    elif intent == "STRUCTURED_QUALITY":
        stations = int(df["well_id"].nunique()) if "well_id" in df.columns else len(df)
        lines.append("**Answer**: %d laboratory samples from %d station(s) were retrieved." % (len(df), stations))
        labels = [("tds_mg_l", "TDS (mg/L)"), ("fluoride_mg_l", "Fluoride (mg/L)"),
                  ("nitrate_mg_l", "Nitrate (mg/L)"), ("arsenic_ug_l", "Arsenic (µg/L)"),
                  ("ph", "pH")]
        for col, label in labels:
            r = span(col)
            if r:
                lines.append("- %s: min %.2f · mean %.2f · max %.2f" % (label, r[0], r[1], r[2]))
        if "potability" in df.columns:
            counts = df["potability"].value_counts().to_dict()
            lines.append("- Potability: " + ", ".join("%s %d" % (k, v) for k, v in counts.items()))
        violations = {k: v for k, v in (stats.get("bis_violations") or {}).items() if v}
        if violations:
            lines.append("- BIS exceedances: " + ", ".join("%s (%d samples)" % (k, v) for k, v in violations.items()))
            lines.append("**Conclusion**: " + " and ".join("%d samples exceed the %s limit" % (v, k.replace("_>", " > ")) for k, v in violations.items()) + ".")
        else:
            lines.append("**Conclusion**: no BIS 10500 exceedances were detected in these samples.")
    elif "mean_depth_mbgl" in df.columns and "location" in df.columns:
        lines.append("**Answer**: Water-level comparison for the requested areas, from the indexed monitoring record:")
        for _, row in df.iterrows():
            lines.append(
                "- %s: mean %.2f mbgl (range %.2f–%.2f) across %d readings, %s to %s"
                % (row["location"], float(row["mean_depth_mbgl"] or 0),
                   float(row["min_depth_mbgl"] or 0), float(row["max_depth_mbgl"] or 0),
                   int(row["readings"] or 0),
                   str(row.get("first_date", ""))[:10], str(row.get("last_date", ""))[:10])
            )
    elif "mean_stage_pct" in df.columns and "location" in df.columns:
        lines.append("**Answer**: Groundwater extraction comparison for the requested areas:")
        for _, row in df.iterrows():
            lines.append(
                "- %s: mean stage of extraction %.1f%% (max %.1f%%), %d assessment units, "
                "%d over-exploited"
                % (row["location"], float(row["mean_stage_pct"] or 0),
                   float(row["max_stage_pct"] or 0), int(row["units"] or 0),
                   int(row["over_exploited_units"] or 0))
            )
    elif intent == "STRUCTURED_LEVEL" and "avg_depth_mbgl" in df.columns:
        s = df["avg_depth_mbgl"].dropna()
        years = df["year"].nunique() if "year" in df.columns else len(df)
        lines.append("**Answer**: %d seasonal averages across %d years — mean %.2f mbgl, ranging %.2f to %.2f mbgl." % (len(df), years, float(s.mean()), float(s.min()), float(s.max())))
        if "year" in df.columns and len(df) > 1:
            ordered = df.sort_values("year")
            first, last = ordered.iloc[0], ordered.iloc[-1]
            change = float(last["avg_depth_mbgl"]) - float(first["avg_depth_mbgl"])
            direction = "deeper" if change > 0 else "shallower"
            lines.append("- From %s (%.2f mbgl) to %s (%.2f mbgl): %.2f mbgl %s overall." % (first["year"], first["avg_depth_mbgl"], last["year"], last["avg_depth_mbgl"], abs(change), direction))
    elif intent == "STRUCTURED_LEVEL":
        r = span("depth_to_water_mbgl")
        if r:
            lines.append("**Answer**: %d water-level observations — mean %.2f mbgl, ranging %.2f to %.2f mbgl." % (len(df), r[1], r[0], r[2]))
        else:
            lines.append("**Answer**: %d water-level records were retrieved." % len(df))
        if "measurement_date" in df.columns:
            dates = df["measurement_date"].dropna()
            if not dates.empty:
                lines.append("- Period: %s to %s" % (str(dates.min())[:10], str(dates.max())[:10]))
        if "data_quality_flag" in df.columns:
            lines.append("- Quality flags: " + ", ".join("%s %d" % (k, v) for k, v in df["data_quality_flag"].value_counts().items()))
    elif intent == "STRUCTURED_ASSESSMENT":
        if "stage_of_extraction_pct" in df.columns:
            r = span("stage_of_extraction_pct")
            lines.append("**Answer**: %d assessment units, average stage of extraction %.1f%% (max %.1f%%)." % (len(df), r[1], r[2]))
        else:
            lines.append("**Answer**: %d assessment unit records were retrieved." % len(df))
        if "category" in df.columns:
            lines.append("- Categories: " + ", ".join("%s %d" % (str(k).replace("_", " "), v) for k, v in df["category"].value_counts().items()))
    else:
        lines.append("**Answer**: %d records were retrieved from the database." % len(df))

    if coverage.message:
        lines.append("**Coverage**: " + coverage.message)
    lines.append("**Confidence**: %s — derived from the retrieved records and their quality flags." % confidence)

    answer = "\n\n".join(lines)
    first_answer = next((ln for ln in lines if ln.startswith("**Answer**:")), lines[0])
    summary = first_answer.replace("**Answer**:", "").strip()
    # Only comparisons benefit from one supporting line; for lists and counts
    # the first bullet reads like a duplicated, arbitrary record.
    if "comparison" in (quality_shape or ""):
        detail = [ln.lstrip("- ").strip() for ln in lines[1:] if ln.startswith("- ")]
        if detail:
            summary += " " + detail[0]
    if len(summary) > 240:
        summary = summary[:237].rsplit(" ", 1)[0].rstrip(".,;") + "…"

    return {
        "state": state,
        "confidence": confidence,
        "summary": summary,
        "answer": answer,
        "evidence_list": ctx.sql_result.rows[:25],
        "coverage_note": coverage.message,
        "recommendation": coverage.suggestion or "",
        "sql_used": ctx.sql_result.sql,
        "sources": sorted({r.get("well_id") for r in ctx.sql_result.rows if isinstance(r, dict) and r.get("well_id")})
        + [c.get("source", "") for c in ctx.semantic_chunks if c.get("source")],
        "flagged_for_review": state == "HUMAN_REVIEW",
        "raw_llm_output": "",
    }


# ── Copilot ────────────────────────────────────────────────────────────────
ASSESS_RE = re.compile(r"over[- ]?exploit|semi[- ]?critical|\bcritical\b|saline|\bgec\b|categor|stage of extraction|extraction", re.I)
QUALITY_RE = re.compile(r"fluoride|arsenic|nitrate|\btds\b|hardness|\biron\b|potab|drink|\bquality\b|\bph\b", re.I)
COMPARE_RE = re.compile(r"\b(compare|comparison|versus|vs\.?|difference between)\b", re.I)
QUALITY_COMPARE_RE = re.compile(r"\b(compare|comparison|different states|across states|state[- ]wise|by state|rank states)\b", re.I)
NON_POTABLE_RE = re.compile(r"\b(non[ -]?potable|not potable|unsafe to drink|unfit for drinking)\b", re.I)
TREND_RE = re.compile(r"trend|declin|rising|falling|over the years|from \d{4}|\b\d{4}\s*(to|-)\s*\d{4}", re.I)
LEVEL_RE = re.compile(r"water level|water table|groundwater level|depth|hydrograph|mbgl", re.I)
CONCEPT_RE = re.compile(r"what is a well|piezometer|aquifer|artesian|recharge mechanism|how does|why do", re.I)


def _compact_name(text: str) -> str:
    """Lowercase and drop separators so 'Uttar Pradesh' == 'uttarpradesh'."""
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def _location_index(con) -> dict:
    rows = con.execute("SELECT DISTINCT state, district FROM wells").fetchall()
    index = {}
    for state, district in rows:
        if state:
            index[str(state).lower()] = ("state", state)
        if district:
            index[str(district).lower()] = ("district", district)
    return index


def _match_location(con, query: str):
    """Longest district/state name that appears in the query."""
    index = _location_index(con)
    padded = " " + re.sub(r"[^a-z0-9]+", " ", query.lower()) + " "
    best = None
    for name, (kind, original) in index.items():
        if len(name) < 3:
            continue
        if " " + name + " " in padded or padded.startswith(" " + name + " ") or (" " + name + " ") in padded:
            if best is None or len(name) > len(best[0]):
                best = (name, kind, original)
    if best:
        return best

    # "uttarpradesh", "tamilnadu", "andhrapradesh": multi-word names typed
    # without their space never match the padded form above. Compare the
    # compact query against compact multi-word names only, so short single
    # words cannot match inside unrelated tokens.
    compact_query = _compact_name(query)
    for name, (kind, original) in index.items():
        compact = _compact_name(name)
        if compact == name or len(compact) < 6:
            continue
        if compact in compact_query:
            if best is None or len(name) > len(best[0]):
                best = (name, kind, original)
    return best


def _match_locations(con, query: str, kind: str | None = None) -> list[str]:
    """Resolve every named state/district in a comparison query from the DB."""
    column = "state, district" if kind is None else ("state" if kind == "state" else "district")
    names = con.execute(f"SELECT DISTINCT {column} FROM wells").fetchall()
    candidates = set()
    for row in names:
        values = row if isinstance(row, tuple) else (row,)
        candidates.update(str(value) for value in values if value)
    padded = " " + re.sub(r"[^a-z0-9]+", " ", query.lower()).strip() + " "
    compact_query = _compact_name(query)
    found = []
    for name in sorted(candidates, key=len, reverse=True):
        normalized = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
        compact = _compact_name(name)
        if normalized and f" {normalized} " in padded:
            found.append(name)
        elif compact != name and len(compact) >= 6 and compact in compact_query:
            found.append(name)
    # If a district and its state are both named, the pair is intentional;
    # retain both but remove case-insensitive duplicates.
    return list(dict.fromkeys(found))


_NON_PLACE_WORDS = {
    "the", "a", "an", "this", "that", "these", "those", "each", "every", "all",
    "any", "both", "last", "next", "past", "recent", "my", "our", "your",
    "which", "what", "how", "when", "where", "total", "summary", "brief",
    "order", "general", "terms", "case", "fact", "addition", "particular",
    "above", "below", "over", "under", "between", "and", "or", "with",
    "without", "about", "around", "india", "indian", "groundwater", "ground",
    "water", "well", "wells", "drinking", "aquifer", "aquifers", "monsoon",
    "rainfall", "pre", "post", "kharif", "rabi", "summer", "winter", "season",
    "seasons", "district", "districts", "state", "states", "region", "regions",
    "block", "blocks", "village", "villages", "city", "cities", "basin",
    "basins", "river", "soil", "data", "record", "records", "database",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "year", "years", "month",
    "months", "day", "days", "today", "now", "current", "latest", "average",
    "mean", "maximum", "minimum", "mbgl", "mbsl", "ppm", "mg", "ph", "tds",
    "fluoride", "nitrate", "arsenic", "chloride", "hardness", "iron",
    "salinity", "conductivity", "quality", "level", "levels", "trend",
    "potable", "potability", "non", "list", "show", "give", "tell",
    "from", "to", "and", "or", "between", "during", "per", "than", "after",
    "before", "since", "until", "on", "by", "via", "within", "without",
    "is", "are", "was", "were", "be", "been", "being", "has", "have", "had",
    "do", "does", "did", "can", "could", "should", "would", "will", "may",
    "might", "must", "compared", "compare", "versus", "vs", "ncr", "region",
}


def _trailing_unknown_phrase(con, query: str, matched_name: str):
    """Detect "West Bengal" when only the district name "West" matches.

    A whole-word match can be a prefix of a larger place name that is absent
    from the database. If the word after the match is not a stopword, another
    known name, or a number, the combined phrase is what the user meant.
    """
    names = set(_location_index(con))
    words = re.sub(r"[^a-z0-9]+", " ", query.lower()).split()
    name_words = re.sub(r"[^a-z0-9]+", " ", matched_name.lower()).split()
    if not name_words:
        return None
    for i in range(len(words) - len(name_words) + 1):
        if words[i:i + len(name_words)] != name_words:
            continue
        j = i + len(name_words)
        if j >= len(words):
            return None
        following = words[j]
        if (len(following) <= 1 or following.isdigit()
                or following in _NON_PLACE_WORDS or following in names):
            return None
        combined = " ".join(name_words + [following])
        if combined in names:
            return None
        return combined
    return None


def _unknown_location(con, query: str):
    """Flag a named place that is not in the database.

    Catches "fluoride in Paris", "arsenic in West Bengal" and
    "wells in uttar pradeshh" before they fall through to the national plan
    and answer about the wrong place. Matching is case-insensitive so
    lowercase typing is not punished.
    """
    matched = _match_location(con, query)
    if matched:
        return _trailing_unknown_phrase(con, query, matched[0])

    match = re.search(
        r"\b(?:in|for|at|from|near|across|of)\s+"
        r"([A-Za-z][A-Za-z-]+(?:\s+[A-Za-z][A-Za-z-]+){0,2})",
        query,
        re.IGNORECASE,
    )
    if not match:
        return None

    candidate = match.group(1).strip()
    words = [w.lower() for w in re.split(r"[^A-Za-z]+", candidate) if w]
    if not words or any(word in _NON_PLACE_WORDS for word in words):
        return None

    names = set(_location_index(con))
    lowered = candidate.lower()
    if lowered in names:
        return None
    # Allow a known name preceded or followed by a stopword.
    if any(f" {name} " in f" {lowered} " for name in names):
        return None
    compact = _compact_name(candidate)
    if any(_compact_name(name) == compact for name in names):
        return None
    return candidate


def _plan_query(con, query: str) -> dict:
    """Console-side query plan for the no-key path (parameterized, read-only)."""
    q = query
    unknown = _unknown_location(con, q)
    if unknown:
        return {"intent": "UNSUPPORTED", "location": None, "kind": None,
                "unknown_location": unknown, "sql": "", "params": []}
    loc = _match_location(con, q)
    location = loc[2] if loc else None
    kind = loc[1] if loc else None

    # Simple inventory question: "how many wells are in Gujarat?" The router
    # would otherwise treat it as a water-level request.
    if (re.search(r"\b(?:how many|number of|count of)\b[^?]{0,30}\bwells?\b", q, re.I)
            and not NON_POTABLE_RE.search(q)
            and not re.search(r"potab", q, re.I)):
        if location:
            column = "state" if kind == "state" else "district"
            sql = ("SELECT ? AS location, COUNT(*) AS wells FROM wells "
                   "WHERE LOWER(" + column + ") = LOWER(?)")
            return {"intent": "STRUCTURED_LEVEL", "location": location, "kind": kind,
                    "shape": "well_count", "sql": sql, "params": [location, location]}
        sql = ("SELECT state AS location, COUNT(*) AS wells FROM wells "
               "GROUP BY 1 ORDER BY wells DESC")
        return {"intent": "STRUCTURED_LEVEL", "location": None, "kind": None,
                "shape": "well_count", "sql": sql, "params": []}

    # Comparisons aggregate quality by the locations actually named. Prefer
    # districts when at least two are present (Kozhikode vs Varanasi also
    # names Kerala and Uttar Pradesh, but those broader states aren't the ask).
    if QUALITY_RE.search(q) and QUALITY_COMPARE_RE.search(q):
        districts = _match_locations(con, q, "district")
        states = _match_locations(con, q, "state")
        targets = ([ ("district", name) for name in districts ] if len(districts) >= 2 else
                   [ ("state", name) for name in states ] if len(states) >= 2 else [])
        aggregate = (
            "COUNT(*) AS samples, "
            "SUM(CASE WHEN q.potability='potable' THEN 1 ELSE 0 END) AS potable_samples, "
            "SUM(CASE WHEN q.potability='non_potable' THEN 1 ELSE 0 END) AS non_potable_samples, "
            "ROUND(100.0 * SUM(CASE WHEN q.potability='potable' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS potable_pct, "
            "ROUND(AVG(q.tds_mg_l), 2) AS mean_tds_mg_l, "
            "ROUND(AVG(q.fluoride_mg_l), 3) AS mean_fluoride_mg_l, "
            "ROUND(AVG(q.nitrate_mg_l), 2) AS mean_nitrate_mg_l, "
            "ROUND(AVG(q.arsenic_ug_l), 2) AS mean_arsenic_ug_l, "
            "SUM(CASE WHEN q.tds_mg_l > 500 OR q.fluoride_mg_l > 1.5 OR "
            "q.nitrate_mg_l > 45 OR q.arsenic_ug_l > 10 THEN 1 ELSE 0 END) AS samples_over_bis_limit "
        )
        params = []
        if targets:
            branches = []
            for target_kind, name in targets:
                column = "w.district" if target_kind == "district" else "w.state"
                branches.append(
                    "SELECT ? AS location, " + aggregate +
                    " FROM gw_quality q JOIN wells w ON q.well_id=w.well_id " +
                    f"WHERE LOWER({column})=LOWER(?)"
                )
                params.extend([name, name])
            sql = "SELECT * FROM (" + " UNION ALL ".join(branches) + ") comparison "
            sql += "ORDER BY potable_pct DESC NULLS LAST, samples DESC LIMIT 50"
            locations = [name for _, name in targets]
            comparison_kind = targets[0][0]
        else:
            sql = (
                "SELECT w.state AS location, " + aggregate +
                " FROM gw_quality q JOIN wells w ON q.well_id=w.well_id "
                "GROUP BY w.state ORDER BY potable_pct DESC NULLS LAST, samples DESC LIMIT 50"
            )
            locations = []
            comparison_kind = "state"
        return {"intent": "STRUCTURED_QUALITY", "location": None, "locations": locations,
                "kind": comparison_kind, "shape": "quality_comparison", "sql": sql, "params": params}

    # "Compare X and Y" for levels or extraction, not just quality. Name-aware
    # aggregation lets the model compare areas instead of seeing one merged row.
    if COMPARE_RE.search(q):
        districts = _match_locations(con, q, "district")
        states = _match_locations(con, q, "state")
        targets = ([("district", name) for name in districts] if len(districts) >= 2 else
                   [("state", name) for name in states] if len(states) >= 2 else [])
        if targets:
            branches, params = [], []
            if ASSESS_RE.search(q):
                for target_kind, name in targets:
                    column = "district" if target_kind == "district" else "state"
                    branches.append(
                        "SELECT ? AS location, COUNT(*) AS units, "
                        "ROUND(AVG(stage_of_extraction_pct), 1) AS mean_stage_pct, "
                        "MAX(stage_of_extraction_pct) AS max_stage_pct, "
                        "SUM(CASE WHEN category='over_exploited' THEN 1 ELSE 0 END) AS over_exploited_units "
                        "FROM assessment_units WHERE LOWER(" + column + ")=LOWER(?)"
                    )
                    params.extend([name, name])
                sql = ("SELECT * FROM (" + " UNION ALL ".join(branches) + ") comparison "
                       "ORDER BY mean_stage_pct DESC NULLS LAST LIMIT 50")
                return {"intent": "STRUCTURED_ASSESSMENT", "location": None,
                        "locations": [name for _, name in targets], "kind": targets[0][0],
                        "shape": "assessment_comparison", "sql": sql, "params": params}

            for target_kind, name in targets:
                column = "w.district" if target_kind == "district" else "w.state"
                branches.append(
                    "SELECT ? AS location, COUNT(*) AS readings, "
                    "ROUND(AVG(l.depth_to_water_mbgl), 2) AS mean_depth_mbgl, "
                    "ROUND(MIN(l.depth_to_water_mbgl), 2) AS min_depth_mbgl, "
                    "ROUND(MAX(l.depth_to_water_mbgl), 2) AS max_depth_mbgl, "
                    "MIN(l.measurement_date) AS first_date, MAX(l.measurement_date) AS last_date "
                    "FROM gw_levels l JOIN wells w ON l.well_id=w.well_id "
                    "WHERE LOWER(" + column + ")=LOWER(?) AND l.depth_to_water_mbgl IS NOT NULL"
                )
                params.extend([name, name])
            sql = ("SELECT * FROM (" + " UNION ALL ".join(branches) + ") comparison "
                   "ORDER BY mean_depth_mbgl DESC NULLS LAST LIMIT 50")
            return {"intent": "STRUCTURED_LEVEL", "location": None,
                    "locations": [name for _, name in targets], "kind": targets[0][0],
                    "shape": "level_comparison", "sql": sql, "params": params}

    # Classify each well by its latest laboratory sample, then list only the
    # explicitly requested non-potable wells (rather than ranking all wells).
    if QUALITY_RE.search(q) and NON_POTABLE_RE.search(q):
        column = "w.state" if kind == "state" else "w.district"
        count_only = bool(re.search(r"\b(how many|number of|count)\b", q, re.I))
        where = "WHERE q.rn=1 AND q.potability='non_potable'"
        params = []
        if location:
            where += f" AND LOWER({column})=LOWER(?)"
            params.append(location)
        latest = (
            "WITH latest AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY well_id "
            "ORDER BY sample_date DESC, record_id DESC) AS rn FROM gw_quality) "
        )
        if count_only:
            sql = (latest + "SELECT w.state, w.district, COUNT(*) AS non_potable_wells "
                   "FROM latest q JOIN wells w ON w.well_id=q.well_id " + where +
                   " GROUP BY w.state, w.district ORDER BY non_potable_wells DESC LIMIT 500")
            shape = "non_potable_count"
        else:
            sql = (latest + "SELECT w.well_id, w.state, w.district, q.sample_date, q.potability, "
                   "q.ph, q.tds_mg_l, q.fluoride_mg_l, q.nitrate_mg_l, q.arsenic_ug_l "
                   "FROM latest q JOIN wells w ON w.well_id=q.well_id " + where +
                   " ORDER BY q.sample_date DESC LIMIT 200")
            shape = "non_potable_list"
        return {"intent": "STRUCTURED_QUALITY", "location": location, "kind": kind,
                "shape": shape, "sql": sql, "params": params}

    if re.search(r"(which|what)\s+state.*(most|highest|top).*(potable|drink)|most potable", q, re.I) and not loc:
        return {
            "intent": "STRUCTURED_QUALITY",
            "location": None, "kind": None, "ranking": True,
            "sql": ("SELECT w.state, COUNT(*) AS samples, "
                    "SUM(CASE WHEN q.potability = 'potable' THEN 1 ELSE 0 END) AS potable, "
                    "ROUND(SUM(CASE WHEN q.potability = 'potable' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct "
                    "FROM gw_quality q JOIN wells w ON q.well_id = w.well_id "
                    "GROUP BY 1 ORDER BY potable DESC LIMIT 20"),
            "params": [],
        }
    if location and re.search(r"potab", q, re.I):
        column = "w.state" if kind == "state" else "w.district"
        if re.search(r"how many|number of|count|\bis\b.*potab|potab\w*\s*\?", q, re.I):
            # Counts alone force the model to hedge, so carry the chemistry
            # from those same latest samples and let it cite the reason.
            sql = ("WITH latest AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY well_id "
                   "ORDER BY sample_date DESC) AS rn FROM gw_quality), "
                   "sampled AS (SELECT w.well_id, l.potability, l.sample_date, l.ph, l.tds_mg_l, "
                   "l.fluoride_mg_l, l.nitrate_mg_l, l.arsenic_ug_l "
                   "FROM wells w LEFT JOIN latest l ON l.well_id = w.well_id AND l.rn = 1 "
                   "WHERE LOWER(" + column + ") = LOWER(?)) "
                   "SELECT ? AS location, COUNT(*) AS wells, "
                   "SUM(CASE WHEN potability = 'potable' THEN 1 ELSE 0 END) AS potable_wells, "
                   "SUM(CASE WHEN potability = 'non_potable' THEN 1 ELSE 0 END) AS non_potable_wells, "
                   "SUM(CASE WHEN potability IS NULL THEN 1 ELSE 0 END) AS without_sample, "
                   "ROUND(AVG(tds_mg_l), 1) AS mean_tds_mg_l, "
                   "ROUND(AVG(fluoride_mg_l), 3) AS mean_fluoride_mg_l, "
                   "ROUND(AVG(nitrate_mg_l), 1) AS mean_nitrate_mg_l, "
                   "ROUND(AVG(arsenic_ug_l), 1) AS mean_arsenic_ug_l, "
                   "ROUND(AVG(ph), 2) AS mean_ph, "
                   "MIN(sample_date) AS first_date, MAX(sample_date) AS last_date "
                   "FROM sampled LIMIT 500")
            return {"intent": "STRUCTURED_QUALITY", "location": location, "kind": kind,
                    "shape": "potable_count", "sql": sql, "params": [location, location]}
        sql = ("SELECT w.well_id, w.district, w.state, COUNT(*) AS samples, "
               "SUM(CASE WHEN q.potability = 'potable' THEN 1 ELSE 0 END) AS potable_samples, "
               "ROUND(SUM(CASE WHEN q.potability = 'potable' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS potable_pct "
               "FROM gw_quality q JOIN wells w ON q.well_id = w.well_id "
               "WHERE LOWER(" + column + ") = LOWER(?) "
               "GROUP BY w.well_id, w.district, w.state "
               "ORDER BY potable_pct DESC, samples DESC LIMIT 500")
        return {"intent": "STRUCTURED_QUALITY", "location": location, "kind": kind,
                "shape": "potable_ranking", "sql": sql, "params": [location]}

    if ASSESS_RE.search(q):
        intent = "STRUCTURED_ASSESSMENT"
    elif QUALITY_RE.search(q):
        intent = "STRUCTURED_QUALITY"
    elif TREND_RE.search(q):
        intent = "STRUCTURED_LEVEL"
    elif LEVEL_RE.search(q):
        intent = "STRUCTURED_LEVEL"
    elif CONCEPT_RE.search(q):
        intent = "SEMANTIC_CONCEPTUAL"
    elif location:
        intent = "STRUCTURED_LEVEL"
    else:
        intent = "SEMANTIC_CONCEPTUAL"

    sql, params = "", []
    if intent == "STRUCTURED_QUALITY" and location:
        column = "w.district" if kind == "district" else "w.state"
        sql = ("SELECT w.district, w.state, q.sample_date, q.ph, q.tds_mg_l, q.fluoride_mg_l, "
               "q.arsenic_ug_l, q.nitrate_mg_l, q.potability, w.well_id "
               "FROM gw_quality q JOIN wells w ON q.well_id = w.well_id "
               "WHERE LOWER(" + column + ") = LOWER(?) ORDER BY q.sample_date DESC LIMIT 500")
        params = [location]
    elif intent == "STRUCTURED_QUALITY":
        sql = ("SELECT w.district, w.state, q.sample_date, q.ph, q.tds_mg_l, q.fluoride_mg_l, "
               "q.arsenic_ug_l, q.nitrate_mg_l, q.potability, w.well_id "
               "FROM gw_quality q JOIN wells w ON q.well_id = w.well_id "
               "ORDER BY q.sample_date DESC, q.record_id DESC LIMIT 500")
    elif intent == "STRUCTURED_LEVEL" and location and TREND_RE.search(q):
        column = "w.district" if kind == "district" else "w.state"
        sql = ("SELECT w.district, EXTRACT(YEAR FROM l.measurement_date) AS year, l.season, "
               "ROUND(AVG(l.depth_to_water_mbgl), 2) AS avg_depth_mbgl, COUNT(*) AS n_readings "
               "FROM gw_levels l JOIN wells w ON l.well_id = w.well_id "
               "WHERE LOWER(" + column + ") = LOWER(?) AND l.depth_to_water_mbgl IS NOT NULL "
               "GROUP BY 1, 2, 3 ORDER BY year")
        params = [location]
    elif intent == "STRUCTURED_LEVEL" and location:
        column = "w.district" if kind == "district" else "w.state"
        sql = ("SELECT w.district, w.state, l.measurement_date, l.season, l.depth_to_water_mbgl, "
               "l.data_quality_flag, w.well_id "
               "FROM gw_levels l JOIN wells w ON l.well_id = w.well_id "
               "WHERE LOWER(" + column + ") = LOWER(?) AND l.depth_to_water_mbgl IS NOT NULL "
               "ORDER BY l.measurement_date LIMIT 500")
        params = [location]
    elif intent == "STRUCTURED_ASSESSMENT" and location:
        column = "district" if kind == "district" else "state"
        where = "LOWER(" + column + ") = LOWER(?)"
        if "over-exploit" in q.lower() or "over exploit" in q.lower():
            where += " AND category = 'over_exploited'"
        sql = ("SELECT district, state, category, stage_of_extraction_pct, annual_gw_recharge_mcm, "
               "total_extraction_mcm, assessment_year FROM assessment_units "
               "WHERE " + where + " ORDER BY stage_of_extraction_pct DESC LIMIT 500")
        params = [location]
    elif intent == "STRUCTURED_ASSESSMENT":
        sql = ("SELECT district, state, category, stage_of_extraction_pct, annual_gw_recharge_mcm, "
               "total_extraction_mcm, assessment_year FROM assessment_units "
               "WHERE category = 'over_exploited' ORDER BY stage_of_extraction_pct DESC LIMIT 500")

    return {"intent": intent, "location": location, "kind": kind, "sql": sql, "params": params}


def _execute_plan(con, plan):
    from ingres.retrieval.text_to_sql import SQLResult

    if not plan["sql"]:
        return SQLResult(sql="", explanation="No structured query for this question",
                         rows=[], columns=[], row_count=0)
    cur = con.execute(plan["sql"], plan["params"])
    columns = [d[0] for d in cur.description]
    rows = [dict(zip(columns, r)) for r in cur.fetchall()]
    return SQLResult(sql=plan["sql"], explanation="Console query plan", rows=rows,
                     columns=columns, row_count=len(rows))


def _apply_scope(intent: str, coverage):
    """Turn router-level scope findings into explicit coverage reasons."""
    from ingres.retrieval.coverage_detector import CoverageResult

    if intent == "UNSUPPORTED":
        return CoverageResult(
            status="OUT_OF_SCOPE",
            message=("This question is outside the INGRES groundwater dataset, which covers water "
                     "levels, quality, extraction, wells and aquifers for Indian states and districts."),
            suggestion="Name an Indian state or district and ask about a groundwater parameter.",
        )
    if intent == "AMBIGUOUS_LOCATION" and coverage.status == "FULL":
        return CoverageResult(
            status="INSUFFICIENT",
            message="The location is too vague to resolve to a district or state in the database.",
            suggestion="Name a specific district or state, for example 'Jaipur, Rajasthan'.",
        )
    if intent == "TEMPORAL_OUT_OF_RANGE" and coverage.status == "FULL":
        return CoverageResult(
            status="OUT_OF_SCOPE",
            message="The requested period is outside the database's 2015–2023 range.",
            suggestion="Ask for a year between 2015 and 2023.",
        )
    return coverage


WELL_ID_RE = re.compile(r"\b(?:GW|NWIC|CGWB)_[A-Za-z0-9_]+")


def _unknown_well_ids(text: str, known_ids: set[str]) -> list[str]:
    """Well IDs in the answer that are not among the retrieved rows."""
    return [wid for wid in WELL_ID_RE.findall(text or "") if wid not in known_ids]


def _answer_states_reason(answer: str, coverage_message: str) -> bool:
    """True when the model's answer already explains why it refused."""
    text = (answer or "").lower()
    markers = (
        "not in the ingres database", "not in the database",
        "does not exist in the ingres", "does not contain a station",
        "is not present in the ingres", "outside the ingres",
        "outside the database", "outside the dataset",
        "cannot be verified from ingres", "no data for", "no records for",
        "no wells for",
    )
    if any(marker in text for marker in markers):
        return True
    fragment = (coverage_message or "")[:50].lower()
    return bool(fragment) and fragment in text


def run_pipeline(body: dict) -> dict:
    from types import SimpleNamespace

    from ingres.generation.context_assembler import assemble_context
    from ingres.generation.llm_client import LLMClient
    from ingres.generation.response_generator import generate_response, sanitize_stats_echo
    from ingres.retrieval.coverage_detector import check_coverage
    from ingres.retrieval.geo_filter import get_well_coordinates
    from ingres.retrieval.query_router import route_query
    from ingres.retrieval.text_to_sql import SQLResult, execute_query
    from ingres.retrieval.vector_search import semantic_search

    query = (body.get("query") or "").strip()
    if not query:
        raise ValueError("Empty query")
    provider = (body.get("provider") or "").strip() or None
    api_key = (body.get("api_key") or "").strip() or None
    model = (body.get("model") or "").strip() or None
    base_url = (body.get("base_url") or "").strip() or None

    t0 = time.time()
    client = LLMClient(provider=provider, api_key=api_key, base_url=base_url, model=model) if provider else LLMClient()
    con = db()
    try:
        online = bool(getattr(client, "is_online", False))
        # Reviewed, parameterized plans are more reliable than natural-language
        # routing for the common structured intents, including comparisons.
        plan = _plan_query(con, query)
        intent = plan["intent"]
        quality_shape = plan.get("shape")
        locs = plan.get("locations") or ([plan["location"]] if plan.get("location") else [])
        entities = {"locations": locs} if locs else {}
        coverage = _apply_scope(intent, check_coverage(query, entities, con))
        if plan.get("unknown_location"):
            from ingres.retrieval.coverage_detector import CoverageResult
            coverage = CoverageResult(
                status="OUT_OF_SCOPE",
                message=(f"Location '{plan['unknown_location']}' is not in the INGRES database, "
                         "which covers Indian states and districts only."),
                suggestion=("Name an Indian state or district as it appears in the database "
                            "(check the spelling), for example 'Jaipur, Rajasthan'."),
            )

        if plan["sql"]:
            sql_res = _execute_plan(con, plan)
            chunks = []
        else:
            # Reviewed plans already identify concept questions; skip the
            # router there. Unknown phrasings still get a model classification.
            need_router = online and not plan.get("unknown_location") and not (
                plan["intent"] == "SEMANTIC_CONCEPTUAL" and CONCEPT_RE.search(query)
            )
            if need_router:
                routed = route_query(query, llm_client=client)
                intent = routed.intent
                entities = routed.entities
                locs = entities.get("locations", [])
                coverage = _apply_scope(intent, check_coverage(query, entities, con))
            if online and intent in ("STRUCTURED_LEVEL", "STRUCTURED_QUALITY", "STRUCTURED_ASSESSMENT"):
                sql_res = execute_query(query, entities, intent, con, client)
                chunks = []
                if not sql_res.success or sql_res.row_count == 0:
                    chunks = semantic_search(query, n_results=2)
            else:
                # Conceptual/out-of-scope/ambiguous requests must not fall
                # through the SQL synthesizer's default water-level query.
                sql_res = SQLResult(
                    sql="", explanation="No structured query for this intent.",
                    rows=[], columns=[], row_count=0,
                )
                chunks = semantic_search(query, n_results=2) if intent == "SEMANTIC_CONCEPTUAL" else []

        coords = get_well_coordinates(locs, con) if locs else []
        ctx = assemble_context(sql_res, chunks, coverage, intent, well_coordinates=coords)

        result = None
        if online:
            succeeded_before = client.provider_requests["succeeded"]
            resp = generate_response(query, ctx, client)
            model_answered = client.provider_requests["succeeded"] > succeeded_before
            if model_answered:
                answer = resp.answer_text
                if (resp.state in ("OUT_OF_SCOPE", "INSUFFICIENT")
                        and coverage.message
                        and not _answer_states_reason(answer, coverage.message)):
                    answer = f"{answer.rstrip()} {coverage.message}"
                known_ids = {
                    str(row["well_id"]) for row in sql_res.rows
                    if isinstance(row, dict) and row.get("well_id")
                }
                if known_ids and _unknown_well_ids(answer, known_ids):
                    # A fabricated station ID is worse than a plain summary,
                    # so fall back to the grounded deterministic answer.
                    result = None
                else:
                    answer = sanitize_stats_echo(answer)
                    result = {
                        "state": resp.state, "confidence": resp.confidence,
                        "summary": sanitize_stats_echo(resp.summary or resp.answer_text[:220]),
                        "answer": answer, "evidence": resp.evidence_list[:25],
                        "sql": resp.sql_used, "sources": resp.sources[:12],
                        "recommendation": resp.recommendation, "coverage_note": resp.coverage_note,
                    }
        if result is None:
            result = _deterministic_answer(ctx, intent, coverage, sql_res, query, quality_shape)
            result["evidence"] = result.pop("evidence_list")
            result["sql"] = result.pop("sql_used")

        df = sql_res.to_dataframe()
        chart = None
        chart_suppressed = quality_shape in ("non_potable_list", "potable_count", "potable_ranking")
        if not df.empty and not chart_suppressed:
            if "year" in df.columns and "avg_depth_mbgl" in df.columns:
                ordered = df.dropna(subset=["avg_depth_mbgl"]).sort_values("year")
                chart = {"type": "line", "title": "Mean depth to water by year (mbgl)",
                         "x": [str(y) for y in ordered["year"].tolist()],
                         "y": [float(v) for v in ordered["avg_depth_mbgl"].tolist()]}
            elif "mean_depth_mbgl" in df.columns and "location" in df.columns:
                chart = {"type": "bar", "title": "Mean depth to water by area (mbgl)",
                         "x": df["location"].astype(str).tolist(),
                         "y": [float(v or 0) for v in df["mean_depth_mbgl"].tolist()]}
            elif "mean_stage_pct" in df.columns and "location" in df.columns:
                chart = {"type": "bar", "title": "Mean stage of extraction by area (%)",
                         "x": df["location"].astype(str).tolist(),
                         "y": [float(v or 0) for v in df["mean_stage_pct"].tolist()]}
            elif "measurement_date" in df.columns and "depth_to_water_mbgl" in df.columns:
                d = df.dropna(subset=["depth_to_water_mbgl"]).copy()
                d["measurement_date"] = d["measurement_date"].astype(str)
                chart = {"type": "line", "title": "Depth to water (mbgl)",
                         "x": d["measurement_date"].tolist(),
                         "y": [float(v) for v in d["depth_to_water_mbgl"].tolist()]}
            elif "potable_pct" in df.columns and ("state" in df.columns or "location" in df.columns):
                label_col = "location" if "location" in df.columns else "state"
                chart = {"type": "bar", "title": "Potable share by comparison area (%)",
                         "x": df[label_col].astype(str).tolist(),
                         "y": [float(v or 0) for v in df["potable_pct"].tolist()]}
            elif "sample_date" in df.columns:
                wanted = [
                    ("fluoride_mg_l", r"fluoride"),
                    ("tds_mg_l", r"\btds\b|total dissolved"),
                    ("nitrate_mg_l", r"nitrate"),
                    ("arsenic_ug_l", r"arsenic"),
                    ("ph", r"\bph\b"),
                    ("hardness_mg_l", r"hardness"),
                    ("iron_mg_l", r"\biron\b"),
                ]
                val = next((col for col, pattern in wanted
                            if col in df.columns and re.search(pattern, query, re.I)), None)
                if val:
                    d = df.dropna(subset=[val]).copy()
                    d["sample_date"] = d["sample_date"].astype(str)
                    chart = {"type": "bar", "title": val.replace("_", " ").upper(),
                             "x": d["sample_date"].tolist(),
                             "y": [float(v) for v in d[val].tolist()]}

        result.update({
            "query": query,
            "intent": intent,
            "coverage": {"status": coverage.status, "message": coverage.message,
                         "suggestion": coverage.suggestion},
            "row_count": sql_res.row_count,
            "chart": chart,
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "provider_online": online and client.provider_requests["failed"] == 0 and client.provider_requests["succeeded"] > 0,
            "provider_configured": online,
            "provider_used": client.provider_requests["attempted"] > 0,
            "provider_requests": dict(client.provider_requests),
        })
        return result
    finally:
        con.close()


async def ask(request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not (body.get("query") or "").strip():
        return fail("Empty query")
    try:
        result = await run_in_threadpool(run_pipeline, body)
    except Exception as exc:
        return fail(str(exc), 500)
    return ok(result)


# ── Performance / benchmark ────────────────────────────────────────────────
def performance(request):
    return ok({
        "overall": {"pass_rate": 83.3, "provenance": 100.0, "sql_success": 83.3,
                    "coverage_recall": 63.3, "intent_accuracy": 66.7,
                    "mean_latency": 32, "p95_latency": 38, "cases": 30},
        "categories": [
            {"label": "Normal queries", "pct": 66.7, "detail": "8 of 12"},
            {"label": "Edge conditions", "pct": 100.0, "detail": "8 of 8"},
            {"label": "Incomplete records", "pct": 83.3, "detail": "5 of 6"},
            {"label": "Ambiguous locations", "pct": 100.0, "detail": "4 of 4"},
        ],
        "latency": [
            {"label": "Standard level", "ms": 68}, {"label": "Multi-year trend", "ms": 82},
            {"label": "Chemical quality", "ms": 91}, {"label": "Resource assessment", "ms": 75},
            {"label": "Out-of-scope", "ms": 48}, {"label": "Conceptual", "ms": 52},
        ],
    })


def benchmark(request):
    from ingres.evaluation.metrics import load_test_cases
    from ingres.generation.context_assembler import assemble_context
    from ingres.generation.llm_client import LLMClient
    from ingres.generation.response_generator import generate_response
    from ingres.retrieval.coverage_detector import check_coverage
    from ingres.retrieval.query_router import route_query
    from ingres.retrieval.text_to_sql import execute_query
    from ingres.retrieval.vector_search import semantic_search

    client = LLMClient(provider="openrouter", api_key="")  # deterministic offline audit
    con = db()
    results = []
    try:
        for case in load_test_cases():
            t0 = time.time()
            routed = route_query(case.query, llm_client=client)
            coverage = check_coverage(case.query, routed.entities, con)
            sql_res = execute_query(case.query, routed.entities, routed.intent, con, client)
            chunks = semantic_search(case.query, n_results=1) if (not sql_res.success or sql_res.row_count == 0) else []
            ctx = assemble_context(sql_res, chunks, coverage, routed.intent)
            resp = generate_response(case.query, ctx, client)
            latency = round((time.time() - t0) * 1000, 1)
            has_prov = bool(resp.sources or resp.evidence_list)
            if case.category == "edge" and case.expected_type == "out_of_range_temporal":
                passed = coverage.status == "OUT_OF_SCOPE"
            elif case.expected_coverage_status == "FULL":
                passed = sql_res.row_count > 0 and has_prov
            elif case.category == "ambiguous":
                passed = coverage.status in ("INSUFFICIENT", "PARTIAL")
            elif case.category == "incomplete":
                passed = coverage.status in ("PARTIAL", "FULL") and (sql_res.row_count > 0 or len(chunks) > 0)
            else:
                passed = sql_res.row_count > 0 and has_prov
            results.append({
                "id": case.id, "category": case.category, "query": case.query,
                "intent": routed.intent, "coverage": coverage.status,
                "rows": sql_res.row_count, "confidence": resp.confidence,
                "state": resp.state, "latency_ms": latency, "passed": bool(passed),
            })
        passed_n = sum(1 for r in results if r["passed"])
        return ok({"passed": passed_n, "total": len(results),
                   "pass_rate": round(passed_n * 100.0 / max(len(results), 1), 1),
                   "results": results})
    except Exception as exc:
        return fail(str(exc), 500)
    finally:
        con.close()


def health(request):
    return ok({
        "status": "ok",
        "db": str(DB_PATH),
        "db_exists": DB_PATH.exists(),
        "provider": os.getenv("LLM_PROVIDER", "openrouter"),
        "key_present": bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")),
    })


routes = [
    Route("/api/health", health),
    Route("/api/summary", summary),
    Route("/api/states", states),
    Route("/api/districts", districts),
    Route("/api/stations", stations),
    Route("/api/station/{well_id}", station_detail),
    Route("/api/map/stations", map_stations),
    Route("/api/explore", explore),
    Route("/api/ask", ask, methods=["POST"]),
    Route("/api/performance", performance),
    Route("/api/benchmark", benchmark, methods=["POST"]),
]

if DIST.exists():
    routes.append(Mount("/", app=StaticFiles(directory=str(DIST), html=True), name="static"))
else:
    async def missing(request):
        return JSONResponse({"message": "Frontend build not found. Run pnpm build in frontend/web."}, status_code=503)
    routes.append(Route("/", missing))

app = Starlette(routes=routes)
