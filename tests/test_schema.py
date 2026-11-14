"""
Tests for the INGRES data schema and database setup.
"""
import sys
from pathlib import Path

import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingres.schema.db_setup import get_connection, get_schema_context, load_dataframe
from ingres.schema.models import (
    WellMetadata, GroundwaterLevel, GroundwaterQuality, AssessmentUnit
)
from datetime import date


# ── Schema / model validation tests ──────────────────────────────────────────

def test_well_metadata_valid():
    w = WellMetadata(
        well_id="GW_RJ_001",
        state="Rajasthan",
        district="Jaipur",
        latitude=26.9,
        longitude=75.8,
        well_type="piezometer",
    )
    assert w.state == "Rajasthan"


def test_well_metadata_invalid_lat():
    with pytest.raises(Exception):
        WellMetadata(
            well_id="GW_BAD",
            state="Rajasthan",
            district="Jaipur",
            latitude=90.0,  # Out of India bounds
            longitude=75.8,
            well_type="piezometer",
        )


def test_groundwater_level_missing_flags():
    rec = GroundwaterLevel(
        record_id="LVL_001",
        well_id="GW_RJ_001",
        measurement_date=date(2023, 4, 15),
        season="pre_monsoon",
        depth_to_water_mbgl=None,
        water_level_mbsl=None,
    )
    assert rec.data_quality_flag == "missing"


def test_quality_auto_potability_non_potable():
    q = GroundwaterQuality(
        record_id="QAL_001",
        well_id="GW_AP_NAL_001",
        sample_date=date(2023, 3, 10),
        fluoride_mg_l=3.5,  # > 1.5 BIS limit
        tds_mg_l=450.0,
    )
    assert q.potability == "non_potable"


def test_quality_auto_potability_potable():
    q = GroundwaterQuality(
        record_id="QAL_002",
        well_id="GW_RJ_001",
        sample_date=date(2023, 3, 10),
        fluoride_mg_l=0.8,
        tds_mg_l=300.0,
        nitrate_mg_l=20.0,
        arsenic_ug_l=5.0,
    )
    assert q.potability == "potable"


def test_assessment_unit_derives_category():
    au = AssessmentUnit(
        unit_id="AU_001",
        state="Rajasthan",
        district="Bikaner",
        block_taluk="Bikaner_A",
        annual_gw_recharge_mcm=50.0,
        extractable_gw_mcm=45.0,
        total_extraction_mcm=55.0,
        stage_of_extraction_pct=122.2,
        assessment_year=2022,
    )
    assert au.category == "over_exploited"


# ── Database setup tests ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_db():
    """In-memory DuckDB for tests."""
    import duckdb
    from ingres.schema.db_setup import SCHEMA_SQL
    con = duckdb.connect(":memory:")
    con.execute(SCHEMA_SQL)
    yield con
    con.close()


def test_schema_tables_exist(test_db):
    tables = test_db.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()
    names = {t[0] for t in tables}
    assert "wells" in names
    assert "gw_levels" in names
    assert "gw_quality" in names
    assert "assessment_units" in names


def test_load_dataframe(test_db):
    df = pd.DataFrame([{
        "well_id": "GW_TEST_001",
        "state": "Rajasthan",
        "district": "Jaipur",
        "block": "Block_A",
        "latitude": 26.9,
        "longitude": 75.8,
        "well_type": "piezometer",
        "aquifer_type": "unconfined",
        "depth_mbgl": 45.0,
        "installation_year": 2000,
        "data_source": "CGWB-NWIC",
    }])
    n = load_dataframe(test_db, "wells", df)
    assert n == 1
    count = test_db.execute("SELECT COUNT(*) FROM wells WHERE well_id='GW_TEST_001'").fetchone()[0]
    assert count == 1


def test_schema_context_string(test_db):
    ctx = get_schema_context(test_db)
    assert "wells" in ctx
    assert "gw_levels" in ctx


def test_synthetic_data_exists():
    """Check that the synthetic DB has been generated."""
    db_path = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "ingres.duckdb"
    if not db_path.exists():
        pytest.skip("Synthetic DB not yet generated. Run: py -3 data/synthetic/generate_synthetic.py")
    con = get_connection(db_path)
    well_count = con.execute("SELECT COUNT(*) FROM wells").fetchone()[0]
    assert well_count >= 100, f"Expected ≥100 wells, got {well_count}"
    level_count = con.execute("SELECT COUNT(*) FROM gw_levels").fetchone()[0]
    assert level_count >= 1000, f"Expected ≥1000 level records, got {level_count}"
    con.close()

