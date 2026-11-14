"""
Tests for Coverage Detector module: temporal bounds, location ambiguity, parameter gaps, and well density rules.
"""
import sys
from pathlib import Path
import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingres.retrieval.coverage_detector import check_coverage
from ingres.schema.db_setup import SCHEMA_SQL, load_dataframe
import pandas as pd


@pytest.fixture
def mock_db():
    con = duckdb.connect(":memory:")
    con.execute(SCHEMA_SQL)
    wells_df = pd.DataFrame([
        {
            "well_id": "GW_RJ_JAI_001",
            "state": "Rajasthan",
            "district": "Jaipur",
            "block": "Jaipur_A",
            "latitude": 26.9,
            "longitude": 75.8,
            "well_type": "piezometer",
            "aquifer_type": "unconfined",
            "depth_mbgl": 50.0,
            "installation_year": 2018,
            "data_source": "CGWB-NWIC"
        },
        {
            "well_id": "GW_RJ_JAI_002",
            "state": "Rajasthan",
            "district": "Jaipur",
            "block": "Jaipur_B",
            "latitude": 26.95,
            "longitude": 75.85,
            "well_type": "open_well",
            "aquifer_type": "unconfined",
            "depth_mbgl": 40.0,
            "installation_year": 2019,
            "data_source": "CGWB-NWIC"
        }
    ])
    levels_df = pd.DataFrame([
        {
            "record_id": f"LVL_{yr}",
            "well_id": "GW_RJ_JAI_001",
            "measurement_date": f"{yr}-04-15",
            "season": "pre_monsoon",
            "depth_to_water_mbgl": 14.0 + yr - 2018,
            "water_level_mbsl": None,
            "measurement_method": "manual",
            "data_quality_flag": "good",
            "remarks": None
        }
        for yr in range(2018, 2024)
    ])
    load_dataframe(con, "wells", wells_df)
    load_dataframe(con, "gw_levels", levels_df)
    yield con
    con.close()


def test_temporal_out_of_range_past(mock_db):
    res = check_coverage(
        query="What was the water level in Jaipur in 1982?",
        entities={"locations": ["Jaipur"]},
        con=mock_db
    )
    assert res.status == "OUT_OF_SCOPE"
    assert "1982" in res.message or "Data is only available" in res.message


def test_temporal_out_of_range_future(mock_db):
    res = check_coverage(
        query="What will the water level be in Jaipur in 2035?",
        entities={"locations": ["Jaipur"]},
        con=mock_db
    )
    assert res.status == "OUT_OF_SCOPE"
    assert "future" in res.message.lower()


def test_ambiguous_location_vague_phrase(mock_db):
    res = check_coverage(
        query="What is the water level in north India near river?",
        entities={},
        con=mock_db
    )
    assert res.status == "INSUFFICIENT"
    assert "vague" in res.message.lower()


def test_unknown_location(mock_db):
    res = check_coverage(
        query="Water level in Atlantis?",
        entities={"locations": ["Atlantis"]},
        con=mock_db
    )
    assert res.status == "INSUFFICIENT"
    assert "not found" in res.message.lower()


def test_full_coverage_valid_query(mock_db):
    res = check_coverage(
        query="What is the pre-monsoon water level in Jaipur in 2022?",
        entities={"locations": ["Jaipur"]},
        con=mock_db
    )
    assert res.status == "FULL"

