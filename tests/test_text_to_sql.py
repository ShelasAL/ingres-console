"""
Tests for Text-to-SQL module: template queries, validation, safety guards, and execution.
"""
import sys
from pathlib import Path
import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingres.retrieval.text_to_sql import (
    execute_query,
    _validate_sql,
    _append_limit,
    TEMPLATES
)
from ingres.schema.db_setup import SCHEMA_SQL, load_dataframe
import pandas as pd


@pytest.fixture
def mock_db():
    con = duckdb.connect(":memory:")
    con.execute(SCHEMA_SQL)
    # Seed a couple of records
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
        }
    ])
    levels_df = pd.DataFrame([
        {
            "record_id": "LVL_001",
            "well_id": "GW_RJ_JAI_001",
            "measurement_date": "2022-04-15",
            "season": "pre_monsoon",
            "depth_to_water_mbgl": 14.5,
            "water_level_mbsl": None,
            "measurement_method": "manual",
            "data_quality_flag": "good",
            "remarks": None
        }
    ])
    load_dataframe(con, "wells", wells_df)
    load_dataframe(con, "gw_levels", levels_df)
    yield con
    con.close()


def test_sql_safety_validation():
    # Dangerous statements must be blocked
    assert _validate_sql("DROP TABLE wells;") is not None
    assert _validate_sql("DELETE FROM gw_levels WHERE 1=1;") is not None
    assert _validate_sql("UPDATE wells SET state='Unknown';") is not None
    assert _validate_sql("INSERT INTO wells VALUES ('1');") is not None

    # Safe SELECT statement
    assert _validate_sql("SELECT * FROM wells LIMIT 10;") is None


def test_append_limit():
    sql = "SELECT * FROM wells"
    with_limit = _append_limit(sql, limit=100)
    assert "LIMIT 100" in with_limit

    # Should not duplicate if already present
    sql_existing = "SELECT * FROM wells LIMIT 50;"
    unchanged = _append_limit(sql_existing, limit=100)
    assert "LIMIT 50" in unchanged


def test_execute_query_template_match(mock_db):
    entities = {
        "locations": ["Jaipur"],
        "time_range": "2022"
    }
    result = execute_query(
        query="What is the pre-monsoon water level in Jaipur for 2022?",
        entities=entities,
        intent="STRUCTURED_LEVEL",
        con=mock_db
    )
    assert result.success is True
    assert result.row_count == 1
    assert result.rows[0]["district"] == "Jaipur"
    assert result.rows[0]["depth_to_water_mbgl"] == 14.5

