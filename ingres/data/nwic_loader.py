"""
NWIC (National Water Data Portal - CGWB) Data Ingestion Module.
Fetches, normalizes, and loads real-world groundwater monitoring data
from nwdp.nwic.gov.in into DuckDB.
"""
from __future__ import annotations

import io
import os
import re
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib3
import requests
import pandas as pd
import duckdb
from loguru import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Verified Live NWIC Resource URLs for requested states (CGWB official)
NWIC_RESOURCES = {
    "rajasthan": {
        "state_name": "Rajasthan",
        "level_url": "https://nwdp.nwic.gov.in/dataset/956add67-cba9-41a5-9d5c-96d73db44aef/resource/8111c3ef-5dc3-4aa9-9f37-f4f13d6099d5/download/gwl_manual_quarterly_cgwb_rj_2021_2025.csv",
        "quality_url": "https://nwdp.nwic.gov.in/dataset/7bb1e7c7-bcc1-48bb-8bcd-32c19473804a/resource/d81750a4-c383-43b1-96f1-b7cb13a176c8/download/gwq_chemical_parameter_manual_cgwb_rj_1961_2025.csv"
    },
    "punjab": {
        "state_name": "Punjab",
        "level_url": "https://nwdp.nwic.gov.in/dataset/956add67-cba9-41a5-9d5c-96d73db44aef/resource/862305d4-0384-4af2-9dca-122e6db0a1c2/download/gwl_manual_quarterly_cgwb_pb_2021_2025.csv",
        "quality_url": "https://nwdp.nwic.gov.in/dataset/7bb1e7c7-bcc1-48bb-8bcd-32c19473804a/resource/eb327ddc-bb2d-41e6-859a-95cf81a742cd/download/gwq_chemical_parameter_manual_cgwb_pb_1961_2025.csv"
    },
    "andhra": {
        "state_name": "Andhra Pradesh",
        "level_url": "https://nwdp.nwic.gov.in/dataset/956add67-cba9-41a5-9d5c-96d73db44aef/resource/31803a41-1025-4eae-8786-8efe29b1623c/download/gwl_manual_quarterly_cgwb_ap_2021_2025.csv",
        "quality_url": "https://nwdp.nwic.gov.in/dataset/7bb1e7c7-bcc1-48bb-8bcd-32c19473804a/resource/7b9cc751-839d-412d-b0e8-44b98c1b43aa/download/gwq_chemical_parameter_manual_cgwb_ap_1961_2025.csv"
    },
    "delhi": {
        "state_name": "Delhi",
        "level_url": "https://nwdp.nwic.gov.in/dataset/956add67-cba9-41a5-9d5c-96d73db44aef/resource/f9d6022f-934e-4835-a0ff-8abd30d20ed9/download/gwl_manual_quarterly_cgwb_dl_2021_2025.csv",
        "quality_url": "https://nwdp.nwic.gov.in/dataset/7bb1e7c7-bcc1-48bb-8bcd-32c19473804a/resource/a85f9294-d1a3-4f98-aed2-94a9d1cea32b/download/gwq_chemical_parameter_manual_cgwb_dl_1961_2025.csv"
    },
    "kerala": {
        "state_name": "Kerala",
        "level_url": "https://nwdp.nwic.gov.in/dataset/956add67-cba9-41a5-9d5c-96d73db44aef/resource/d32e6b72-9abf-4c80-b225-9d685398eb91/download/gwl_manual_quarterly_cgwb_kl_2021_2025.csv",
        "quality_url": "https://nwdp.nwic.gov.in/dataset/7bb1e7c7-bcc1-48bb-8bcd-32c19473804a/resource/6a04086c-2f1b-414e-8b28-6157d894cc39/download/gwq_chemical_parameter_manual_cgwb_kl_1961_2025.csv"
    },
    "tamil nadu": {
        "state_name": "Tamil Nadu",
        "level_url": "https://nwdp.nwic.gov.in/dataset/956add67-cba9-41a5-9d5c-96d73db44aef/resource/21cfbb8e-ac1b-4837-a463-317c05fb6f1b/download/gwl_manual_quarterly_cgwb_tn_2021_2025.csv",
        "quality_url": "https://nwdp.nwic.gov.in/dataset/7bb1e7c7-bcc1-48bb-8bcd-32c19473804a/resource/9946e904-573a-4fca-8eec-d259a27e8903/download/gwq_chemical_parameter_manual_cgwb_tn_1961_2025.csv"
    },
    "uttar pradesh": {
        "state_name": "Uttar Pradesh",
        "level_url": "https://nwdp.nwic.gov.in/dataset/956add67-cba9-41a5-9d5c-96d73db44aef/resource/3bfb326c-0aa6-45fa-aef4-bde87faa9810/download/gwl_manual_quarterly_cgwb_up_2021_2025.csv",
        "quality_url": "https://nwdp.nwic.gov.in/dataset/7bb1e7c7-bcc1-48bb-8bcd-32c19473804a/resource/5bddb48e-136f-49c9-8a35-37c75f981c66/download/gwq_chemical_parameter_manual_cgwb_up_1961_2025.csv"
    },
    "bihar": {
        "state_name": "Bihar",
        "level_url": "https://nwdp.nwic.gov.in/dataset/956add67-cba9-41a5-9d5c-96d73db44aef/resource/fdf501bd-064a-4a57-b620-79516782b7ff/download/gwl_manual_quarterly_cgwb_br_2021_2025.csv",
        "quality_url": "https://nwdp.nwic.gov.in/dataset/7bb1e7c7-bcc1-48bb-8bcd-32c19473804a/resource/1b8e3f68-4d04-49f3-8121-52bbe25f6323/download/gwq_chemical_parameter_manual_cgwb_br_1961_2025.csv"
    }
}


def _derive_season(dt: date) -> str:
    month = dt.month
    if month in (3, 4, 5):
        return "pre_monsoon"
    elif month in (6, 7, 8, 9):
        return "kharif"
    elif month in (10, 11):
        return "post_monsoon"
    return "rabi"


def _parse_date(val: str) -> Optional[date]:
    if not val or pd.isna(val):
        return None
    val = str(val).strip().split(" ")[0]
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except Exception:
            pass
    return None


def fetch_csv(url: str, max_rows: Optional[int] = None) -> pd.DataFrame:
    """Download and parse CSV from NWIC portal."""
    logger.info(f"Downloading from NWIC: {url}")
    resp = requests.get(url, timeout=60, verify=False)
    resp.raise_for_status()
    # Read into pandas
    df = pd.read_csv(io.StringIO(resp.text), nrows=max_rows, low_memory=False)
    # Strip whitespace from columns
    df.columns = [c.strip() for c in df.columns]
    return df


def ingest_state_data(state_key: str, con: duckdb.DuckDBPyConnection, max_rows: int = 5000) -> Dict[str, int]:
    """
    Ingest official CGWB water levels and water quality for a target state into DuckDB.
    Returns counts of inserted wells, levels, and quality records.
    """
    state_key = state_key.lower().strip()
    if state_key not in NWIC_RESOURCES:
        raise ValueError(f"State '{state_key}' not in supported NWIC list: {list(NWIC_RESOURCES.keys())}")

    config = NWIC_RESOURCES[state_key]
    state_name = config["state_name"]
    logger.info(f"Starting NWIC ingestion for: {state_name}")

    wells_to_insert = []
    levels_to_insert = []
    quality_to_insert = []

    # 1. Ingest Water Levels
    level_url = config.get("level_url")
    if level_url:
        try:
            ldf = fetch_csv(level_url, max_rows=max_rows)
            for _, row in ldf.iterrows():
                station = str(row.get("Station", "")).strip()
                if not station or station == "nan":
                    continue

                district = str(row.get("District", "")).strip().title()
                block = str(row.get("Block", "")).strip().title()
                lat = pd.to_numeric(row.get("Latitude"), errors="coerce")
                lon = pd.to_numeric(row.get("Longitude"), errors="coerce")

                # Validate India coordinates
                if pd.notna(lat) and pd.notna(lon) and 6.0 <= lat <= 38.0 and 68.0 <= lon <= 98.0:
                    well_id = f"NWIC_{state_name[:2].upper()}_{station.replace(' ', '_')[:25]}"
                    wells_to_insert.append({
                        "well_id": well_id,
                        "state": state_name,
                        "district": district or "Unknown",
                        "block": block if block != "-" else "",
                        "latitude": round(float(lat), 4),
                        "longitude": round(float(lon), 4),
                        "well_type": "piezometer" if "piezometer" in station.lower() else "open_well",
                        "aquifer_type": "unconfined",
                        "depth_mbgl": 40.0,
                        "installation_year": 2015,
                        "data_source": "CGWB-NWIC-Live"
                    })

                    # Parse depth
                    depth_val = pd.to_numeric(row.get("Groundwater Level Quarterly Manual (meter)"), errors="coerce")
                    meas_date = _parse_date(row.get("Data Acquisition Time"))

                    if pd.notna(depth_val) and meas_date:
                        levels_to_insert.append({
                            "record_id": f"LVL_{well_id}_{meas_date}_{len(levels_to_insert)}",
                            "well_id": well_id,
                            "measurement_date": meas_date,
                            "season": _derive_season(meas_date),
                            "depth_to_water_mbgl": round(float(depth_val), 2),
                            "water_level_mbsl": None,
                            "measurement_method": "manual",
                            "data_quality_flag": "good",
                            "remarks": f"CGWB Agency Source: {row.get('Agency', 'CGWB')}"
                        })
        except Exception as e:
            logger.error(f"Failed ingesting levels for {state_name}: {e}")

    # 2. Ingest Water Quality
    quality_url = config.get("quality_url")
    if quality_url:
        try:
            qdf = fetch_csv(quality_url, max_rows=max_rows)
            for _, row in qdf.iterrows():
                station = str(row.get("Station", "")).strip()
                if not station or station == "nan":
                    continue

                district = str(row.get("District", "")).strip().title()
                block = str(row.get("Block", "")).strip().title()
                lat = pd.to_numeric(row.get("Latitude"), errors="coerce")
                lon = pd.to_numeric(row.get("Longitude"), errors="coerce")
                sample_date = _parse_date(row.get("Data Acquisition Time"))

                if pd.notna(lat) and pd.notna(lon) and 6.0 <= lat <= 38.0 and 68.0 <= lon <= 98.0:
                    well_id = f"NWIC_{state_name[:2].upper()}_{station.replace(' ', '_')[:25]}"
                    wells_to_insert.append({
                        "well_id": well_id,
                        "state": state_name,
                        "district": district or "Unknown",
                        "block": block if block != "-" else "",
                        "latitude": round(float(lat), 4),
                        "longitude": round(float(lon), 4),
                        "well_type": "open_well",
                        "aquifer_type": "unconfined",
                        "depth_mbgl": 40.0,
                        "installation_year": 2010,
                        "data_source": "CGWB-NWIC-Live"
                    })

                    ph = pd.to_numeric(row.get("Potential of Hydrogen (pH)"), errors="coerce")
                    tds = pd.to_numeric(row.get("Total Dissolved Solids (mg/L)"), errors="coerce")
                    fluoride = pd.to_numeric(row.get("Fluoride (mg/L)"), errors="coerce")
                    arsenic = pd.to_numeric(row.get("Arsenic (mg/L)"), errors="coerce")
                    nitrate = pd.to_numeric(row.get("Nitrate N (mgN/L)"), errors="coerce")
                    hardness = pd.to_numeric(row.get("Total Hardness (mgCaCO3/L)"), errors="coerce")
                    iron = pd.to_numeric(row.get("Iron(mg/L)"), errors="coerce")

                    # Convert arsenic mg/L to µg/L
                    ars_ug = (float(arsenic) * 1000.0) if pd.notna(arsenic) else None

                    # Evaluate potability
                    potable = "potable"
                    if (pd.notna(tds) and tds > 500) or (pd.notna(fluoride) and fluoride > 1.5) or (pd.notna(ars_ug) and ars_ug > 10) or (pd.notna(nitrate) and nitrate > 45):
                        potable = "non_potable"

                    if sample_date:
                        quality_to_insert.append({
                            "record_id": f"QAL_{well_id}_{sample_date}_{len(quality_to_insert)}",
                            "well_id": well_id,
                            "sample_date": sample_date,
                            "ph": round(float(ph), 2) if pd.notna(ph) else None,
                            "tds_mg_l": round(float(tds), 1) if pd.notna(tds) else None,
                            "nitrate_mg_l": round(float(nitrate), 1) if pd.notna(nitrate) else None,
                            "fluoride_mg_l": round(float(fluoride), 2) if pd.notna(fluoride) else None,
                            "arsenic_ug_l": round(ars_ug, 1) if ars_ug is not None else None,
                            "iron_mg_l": round(float(iron), 2) if pd.notna(iron) else None,
                            "hardness_mg_l": round(float(hardness), 1) if pd.notna(hardness) else None,
                            "potability": potable,
                            "lab_id": "CGWB-Regional-Lab"
                        })
        except Exception as e:
            logger.error(f"Failed ingesting quality for {state_name}: {e}")

    # 3. Load into DuckDB using INSERT OR REPLACE
    inserted_wells = 0
    inserted_levels = 0
    inserted_quality = 0

    if wells_to_insert:
        w_df = pd.DataFrame(wells_to_insert).drop_duplicates(subset=["well_id"])
        con.register("_nwic_wells", w_df)
        con.execute("INSERT OR REPLACE INTO wells SELECT * FROM _nwic_wells")
        con.unregister("_nwic_wells")
        inserted_wells = len(w_df)

    if levels_to_insert:
        l_df = pd.DataFrame(levels_to_insert).drop_duplicates(subset=["record_id"])
        con.register("_nwic_levels", l_df)
        con.execute("INSERT OR REPLACE INTO gw_levels SELECT * FROM _nwic_levels")
        con.unregister("_nwic_levels")
        inserted_levels = len(l_df)

    if quality_to_insert:
        q_df = pd.DataFrame(quality_to_insert).drop_duplicates(subset=["record_id"])
        con.register("_nwic_quality", q_df)
        con.execute("INSERT OR REPLACE INTO gw_quality SELECT * FROM _nwic_quality")
        con.unregister("_nwic_quality")
        inserted_quality = len(q_df)

    logger.info(f"NWIC {state_name} Ingestion Complete: {inserted_wells} stations, {inserted_levels} levels, {inserted_quality} quality samples.")
    return {
        "state": state_name,
        "stations": inserted_wells,
        "levels": inserted_levels,
        "quality": inserted_quality
    }
