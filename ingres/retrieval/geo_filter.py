"""
Geospatial filter: resolves location names and applies spatial queries.
Uses a GeoJSON boundary file for district-level lookups.
Falls back to coordinate bounding boxes from the database.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

GEOJSON_PATH = Path(__file__).resolve().parents[2] / "data" / "geospatial" / "india_districts.geojson"

# Bounding boxes for common vague regions (fallback)
REGION_BOUNDS = {
    "marathwada": {"states": ["Maharashtra"],
                   "districts": ["Aurangabad", "Latur", "Osmanabad", "Nanded",
                                  "Parbhani", "Hingoli", "Beed", "Jalna"]},
    "vidarbha":   {"states": ["Maharashtra"],
                   "districts": ["Nagpur", "Amravati", "Wardha", "Yavatmal"]},
    "bundelkhand":{"states": ["Uttar Pradesh", "Madhya Pradesh"],
                   "districts": ["Jhansi", "Banda", "Chitrakoot"]},
    "telangana":  {"states": ["Telangana"]},
}


@dataclass
class GeoResult:
    resolved_districts: list[str]
    resolved_states: list[str]
    bbox: Optional[tuple[float, float, float, float]] = None  # lat_min, lat_max, lon_min, lon_max
    region_type: str = "district"  # district, state, region


def resolve_location(location_str: str, con) -> GeoResult:
    """
    Resolve a location string to districts/states in the database.
    """
    loc = location_str.strip().lower()

    # Check known regions first
    for region, bounds in REGION_BOUNDS.items():
        if region in loc:
            districts = bounds.get("districts", [])
            states = bounds.get("states", [])
            return GeoResult(
                resolved_districts=districts,
                resolved_states=states,
                region_type="region",
            )

    # Exact district match
    rows = con.execute(
        "SELECT DISTINCT district, state FROM wells WHERE LOWER(district)=?",
        [loc]
    ).fetchall()
    if rows:
        return GeoResult(
            resolved_districts=[r[0] for r in rows],
            resolved_states=list({r[1] for r in rows}),
            region_type="district",
        )

    # Exact state match
    rows = con.execute(
        "SELECT DISTINCT state FROM wells WHERE LOWER(state)=?",
        [loc]
    ).fetchall()
    if rows:
        districts = con.execute(
            "SELECT DISTINCT district FROM wells WHERE LOWER(state)=?",
            [loc]
        ).fetchall()
        return GeoResult(
            resolved_districts=[r[0] for r in districts],
            resolved_states=[r[0] for r in rows],
            region_type="state",
        )

    # Fuzzy match using LIKE
    rows = con.execute(
        "SELECT DISTINCT district, state FROM wells WHERE LOWER(district) LIKE ?",
        [f"%{loc[:5]}%"]
    ).fetchall()
    if rows:
        logger.info(f"Fuzzy match for '{location_str}': {[r[0] for r in rows]}")
        return GeoResult(
            resolved_districts=[r[0] for r in rows[:3]],
            resolved_states=list({r[1] for r in rows[:3]}),
            region_type="district",
        )

    return GeoResult(resolved_districts=[], resolved_states=[], region_type="unknown")


def get_well_coordinates(districts: list[str], con) -> list[dict]:
    """Return lat/lon for all wells in the given districts."""
    if not districts:
        return []
    placeholders = ", ".join("?" * len(districts))
    rows = con.execute(
        f"""SELECT well_id, district, state, latitude, longitude, well_type
            FROM wells WHERE LOWER(district) IN ({placeholders})""",
        [d.lower() for d in districts]
    ).fetchall()
    return [
        {"well_id": r[0], "district": r[1], "state": r[2],
         "latitude": r[3], "longitude": r[4], "well_type": r[5]}
        for r in rows
    ]

