"""
Synthetic dataset generator for INGRES.
Produces ~200 wells × 8 seasonal readings + quality samples + assessment units,
covering normal, edge, and incomplete cases.

Run directly:  py -3 data/synthetic/generate_synthetic.py
"""
from __future__ import annotations

import random
import uuid
from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd
import numpy as np

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ingres.schema.db_setup import get_connection, load_dataframe

random.seed(42)
np.random.seed(42)

# ── Geographic data ──────────────────────────────────────────────────────────
STATES_DISTRICTS = {
    "Rajasthan":    [("Jaipur", 26.9, 75.8), ("Bikaner", 28.0, 73.3),
                     ("Jodhpur", 26.3, 73.0), ("Nagaur", 27.2, 73.7),
                     ("Barmer", 25.7, 71.4)],
    "Maharashtra":  [("Pune", 18.5, 73.9), ("Nashik", 20.0, 73.8),
                     ("Aurangabad", 19.9, 75.3), ("Osmanabad", 18.2, 76.1),
                     ("Latur", 18.4, 76.6)],
    "Gujarat":      [("Ahmedabad", 23.0, 72.6), ("Mehsana", 23.6, 72.4),
                     ("Banaskantha", 24.2, 72.4), ("Surat", 21.2, 72.8),
                     ("Anand", 22.6, 72.9)],
    "Punjab":       [("Ludhiana", 30.9, 75.9), ("Amritsar", 31.6, 74.9),
                     ("Patiala", 30.3, 76.4), ("Sangrur", 30.2, 75.8),
                     ("Bathinda", 30.2, 74.9)],
    "Uttar Pradesh":[("Lucknow", 26.8, 80.9), ("Agra", 27.2, 78.0),
                     ("Varanasi", 25.3, 83.0), ("Allahabad", 25.4, 81.8),
                     ("Meerut", 29.0, 77.7)],
    "Bihar":        [("Patna", 25.6, 85.1), ("Gaya", 24.8, 85.0),
                     ("Bhagalpur", 25.3, 87.0), ("Muzaffarpur", 26.1, 85.4),
                     ("Nalanda", 25.1, 85.5)],
    "Andhra Pradesh":[("Guntur", 16.3, 80.4), ("Nalgonda", 17.1, 79.3),
                      ("Prakasam", 15.4, 80.0), ("Kurnool", 15.8, 78.1),
                      ("Krishna", 16.6, 81.1)],
    "Tamil Nadu":   [("Chennai", 13.1, 80.3), ("Madurai", 9.9, 78.1),
                     ("Coimbatore", 11.0, 76.9), ("Salem", 11.7, 78.1),
                     ("Tiruchirapalli", 10.8, 78.7)],
    "Karnataka":    [("Bengaluru Rural", 13.1, 77.6), ("Tumkur", 13.3, 77.1),
                     ("Kolar", 13.1, 78.1), ("Mysuru", 12.3, 76.6),
                     ("Dharwad", 15.5, 75.0)],
    "Telangana":    [("Hyderabad", 17.4, 78.5), ("Warangal", 18.0, 79.6),
                     ("Karimnagar", 18.4, 79.1), ("Khammam", 17.2, 80.2),
                     ("Medak", 18.0, 78.3)],
}

WELL_TYPES = ["open_well", "piezometer", "borewell", "dug_well"]
AQUIFER_TYPES = ["unconfined", "confined", "semi-confined"]
SEASONS = ["pre_monsoon", "post_monsoon", "rabi", "kharif"]
YEARS = list(range(2015, 2024))

# BIS violation regions (edge/incomplete)
HIGH_FLUORIDE_DISTRICTS = {"Nalgonda", "Guntur", "Barmer"}
HIGH_ARSENIC_DISTRICTS   = {"Bhagalpur", "Patna", "Varanasi"}
OVER_EXPLOITED_DISTRICTS = {"Bikaner", "Mehsana", "Sangrur", "Kolar"}
SALINE_DISTRICTS         = {"Barmer", "Banaskantha"}


def _make_well_id(state: str, district: str, idx: int) -> str:
    abbr = "".join(w[0] for w in state.split()[:2]).upper()
    dist = district[:3].upper()
    return f"GW_{abbr}_{dist}_{idx:03d}"


def generate_wells(n_per_district: int = 4) -> pd.DataFrame:
    rows = []
    for state, districts in STATES_DISTRICTS.items():
        for district, lat, lon in districts:
            for i in range(n_per_district):
                well_id = _make_well_id(state, district, i + 1)
                # Edge case: artesian well (confined, very deep)
                is_artesian = (district in {"Patna", "Lucknow"} and i == 0)
                rows.append({
                    "well_id": well_id,
                    "state": state,
                    "district": district,
                    "block": f"{district}_Block_{chr(65+i)}",
                    "latitude": round(lat + random.uniform(-0.2, 0.2), 4),
                    "longitude": round(lon + random.uniform(-0.2, 0.2), 4),
                    "well_type": "piezometer" if is_artesian else random.choice(WELL_TYPES),
                    "aquifer_type": "confined" if is_artesian else random.choice(AQUIFER_TYPES),
                    "depth_mbgl": round(random.uniform(150, 300), 1) if is_artesian
                                  else round(random.uniform(10, 120), 1),
                    "installation_year": random.randint(1985, 2020),
                    "data_source": "CGWB-NWIC",
                })
    return pd.DataFrame(rows)


def generate_levels(wells_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, well in wells_df.iterrows():
        wid = well["well_id"]
        district = well["district"]
        state = well["state"]

        # Determine base depth (deeper = worse)
        base_depth = 5.0 if district in {"Patna", "Lucknow"} else 8.0
        if district in OVER_EXPLOITED_DISTRICTS:
            base_depth = 18.0
        if state == "Rajasthan":
            base_depth = 15.0

        for year in YEARS:
            for season in SEASONS:
                # Incomplete case: skip 20% of quality-impaired districts
                if district in HIGH_FLUORIDE_DISTRICTS and random.random() < 0.25:
                    continue  # Intentional data gap

                # Single-reading edge case: only pre_monsoon for some wells
                if wid.endswith("004") and season != "pre_monsoon":
                    continue

                depth = base_depth + random.gauss(0, 1.5)
                # Declining trend: +0.3 mbgl per year
                depth += 0.3 * (year - 2015)
                if season in ("post_monsoon", "kharif"):
                    depth -= 3.0  # monsoon recovery
                depth = max(0.1, round(depth, 2))

                # Edge: artesian → negative (below sea level expressed differently)
                if district in {"Patna", "Lucknow"} and wid.endswith("001"):
                    depth = round(random.uniform(0.5, 2.0), 2)  # very shallow artesian

                # Suspect flag
                quality = "good"
                if random.random() < 0.07:
                    quality = "suspect"
                elif random.random() < 0.03:
                    quality = "estimated"

                measurement_date = date(year, 4 if season == "pre_monsoon" else
                                        10 if season == "post_monsoon" else
                                        1 if season == "rabi" else 7, 15)

                rows.append({
                    "record_id": f"LVL_{wid}_{year}_{season[:3].upper()}",
                    "well_id": wid,
                    "measurement_date": measurement_date,
                    "season": season,
                    "depth_to_water_mbgl": depth,
                    "water_level_mbsl": None,
                    "measurement_method": "telemetry" if "PIE" in wid else "manual",
                    "data_quality_flag": quality,
                    "remarks": "Artesian condition observed" if depth < 1.0 else None,
                })
    return pd.DataFrame(rows)


def generate_quality(wells_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, well in wells_df.iterrows():
        wid = well["well_id"]
        district = well["district"]

        # Incomplete case: quality data missing for ~40% wells (only 60% sampled)
        if random.random() < 0.40:
            continue

        for year in [2019, 2021, 2023]:
            sample_date = date(year, 3, 10)

            fluoride = None
            if district in HIGH_FLUORIDE_DISTRICTS:
                fluoride = round(random.uniform(1.0, 4.5), 2)
            elif random.random() < 0.5:
                fluoride = round(random.uniform(0.2, 1.2), 2)

            arsenic = None
            if district in HIGH_ARSENIC_DISTRICTS:
                arsenic = round(random.uniform(5, 50), 1)
            elif random.random() < 0.3:
                arsenic = round(random.uniform(0.5, 8), 1)

            tds = round(random.uniform(200, 2500) if district in SALINE_DISTRICTS
                        else random.uniform(150, 800), 1)

            nitrate = round(random.uniform(5, 80), 1) if random.random() < 0.6 else None
            ph = round(random.uniform(6.5, 8.5), 1)
            iron = round(random.uniform(0.1, 2.5), 2) if random.random() < 0.4 else None

            rows.append({
                "record_id": f"QAL_{wid}_{year}",
                "well_id": wid,
                "sample_date": sample_date,
                "ph": ph,
                "tds_mg_l": tds,
                "nitrate_mg_l": nitrate,
                "fluoride_mg_l": fluoride,
                "arsenic_ug_l": arsenic,
                "iron_mg_l": iron,
                "hardness_mg_l": round(random.uniform(100, 600), 1),
                "potability": None,   # Will be auto-derived by validator
                "lab_id": f"LAB_{random.randint(100, 999)}",
            })
    return pd.DataFrame(rows)


def generate_assessment_units(wells_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for state, districts in STATES_DISTRICTS.items():
        for district, _, _ in districts:
            for year in [2020, 2022]:
                recharge = round(random.uniform(30, 500), 2)
                extractable = round(recharge * random.uniform(0.6, 0.95), 2)

                if district in OVER_EXPLOITED_DISTRICTS:
                    extraction = round(extractable * random.uniform(1.05, 1.4), 2)
                elif district in SALINE_DISTRICTS:
                    extraction = round(extractable * random.uniform(0.8, 0.9), 2)
                else:
                    extraction = round(extractable * random.uniform(0.4, 0.98), 2)

                stage = round((extraction / extractable) * 100, 1) if extractable > 0 else None

                cat = None
                if stage is not None:
                    if district in SALINE_DISTRICTS:
                        cat = "saline"
                    elif stage > 100:
                        cat = "over_exploited"
                    elif stage > 90:
                        cat = "critical"
                    elif stage > 70:
                        cat = "semi_critical"
                    else:
                        cat = "safe"

                rows.append({
                    "unit_id": f"AU_{state[:2].upper()}_{district[:5].upper()}_{year}",
                    "state": state,
                    "district": district,
                    "block_taluk": f"{district}_Block_A",
                    "annual_gw_recharge_mcm": recharge,
                    "extractable_gw_mcm": extractable,
                    "total_extraction_mcm": extraction,
                    "stage_of_extraction_pct": stage,
                    "category": cat,
                    "assessment_year": year,
                    "methodology": "GEC-2015",
                })
    return pd.DataFrame(rows)


def main():
    print("🌊 INGRES Synthetic Data Generator")
    print("=" * 44)

    con = get_connection()

    wells = generate_wells(n_per_district=4)
    levels = generate_levels(wells)
    quality = generate_quality(wells)
    units = generate_assessment_units(wells)

    # Derive potability for quality records using BIS limits
    def derive_potability(row):
        violations = []
        if pd.notna(row.get("tds_mg_l")) and row["tds_mg_l"] > 500:
            violations.append("tds")
        if pd.notna(row.get("fluoride_mg_l")) and row["fluoride_mg_l"] > 1.5:
            violations.append("fluoride")
        if pd.notna(row.get("nitrate_mg_l")) and row["nitrate_mg_l"] > 45:
            violations.append("nitrate")
        if pd.notna(row.get("arsenic_ug_l")) and row["arsenic_ug_l"] > 10:
            violations.append("arsenic")
        if violations:
            return "non_potable"
        no_data = all(pd.isna(row.get(p)) for p in
                      ["tds_mg_l", "fluoride_mg_l", "nitrate_mg_l", "arsenic_ug_l"])
        return "unknown" if no_data else "potable"

    if not quality.empty:
        quality["potability"] = quality.apply(derive_potability, axis=1)

    load_dataframe(con, "wells", wells)
    load_dataframe(con, "gw_levels", levels)
    load_dataframe(con, "gw_quality", quality)
    load_dataframe(con, "assessment_units", units)

    # Summary
    print(f"\n✅ Database populated:")
    for tbl in ["wells", "gw_levels", "gw_quality", "assessment_units"]:
        cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"   {tbl:<25} {cnt:>6} records")

    con.close()
    print("\n🗄️  Database saved to: data/synthetic/ingres.duckdb")


if __name__ == "__main__":
    main()

