"""
DuckDB schema creation and data-ingestion pipeline for INGRES.
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
from loguru import logger

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "ingres.duckdb"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wells (
    well_id          VARCHAR PRIMARY KEY,
    state            VARCHAR NOT NULL,
    district         VARCHAR NOT NULL,
    block            VARCHAR DEFAULT '',
    latitude         DOUBLE,
    longitude        DOUBLE,
    well_type        VARCHAR,
    aquifer_type     VARCHAR,
    depth_mbgl       DOUBLE,
    installation_year INTEGER,
    data_source      VARCHAR DEFAULT 'CGWB-NWIC'
);

CREATE TABLE IF NOT EXISTS gw_levels (
    record_id             VARCHAR PRIMARY KEY,
    well_id               VARCHAR NOT NULL,
    measurement_date      DATE NOT NULL,
    season                VARCHAR,
    depth_to_water_mbgl   DOUBLE,
    water_level_mbsl      DOUBLE,
    measurement_method    VARCHAR DEFAULT 'manual',
    data_quality_flag     VARCHAR DEFAULT 'good',
    remarks               VARCHAR,
    FOREIGN KEY (well_id) REFERENCES wells(well_id)
);

CREATE TABLE IF NOT EXISTS gw_quality (
    record_id     VARCHAR PRIMARY KEY,
    well_id       VARCHAR NOT NULL,
    sample_date   DATE NOT NULL,
    ph            DOUBLE,
    tds_mg_l      DOUBLE,
    nitrate_mg_l  DOUBLE,
    fluoride_mg_l DOUBLE,
    arsenic_ug_l  DOUBLE,
    iron_mg_l     DOUBLE,
    hardness_mg_l DOUBLE,
    potability    VARCHAR,
    lab_id        VARCHAR,
    FOREIGN KEY (well_id) REFERENCES wells(well_id)
);

CREATE TABLE IF NOT EXISTS assessment_units (
    unit_id                  VARCHAR PRIMARY KEY,
    state                    VARCHAR,
    district                 VARCHAR,
    block_taluk              VARCHAR,
    annual_gw_recharge_mcm   DOUBLE,
    extractable_gw_mcm       DOUBLE,
    total_extraction_mcm     DOUBLE,
    stage_of_extraction_pct  DOUBLE,
    category                 VARCHAR,
    assessment_year          INTEGER,
    methodology              VARCHAR DEFAULT 'GEC-2015'
);
"""


def get_connection(db_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection, creating the schema if needed."""
    path = Path(db_path or os.getenv("DB_PATH", str(_DEFAULT_DB)))
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(SCHEMA_SQL)
    return con


def load_dataframe(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame) -> int:
    """Upsert a DataFrame into a table; returns rows inserted."""
    if df.empty:
        return 0
    # DuckDB can register and insert from a DataFrame directly
    con.register("_tmp_df", df)
    con.execute(f"INSERT OR REPLACE INTO {table} SELECT * FROM _tmp_df")
    con.unregister("_tmp_df")
    count = len(df)
    logger.info(f"Loaded {count} rows into '{table}'")
    return count


def get_schema_context(con: duckdb.DuckDBPyConnection) -> str:
    """Return a human-readable schema description for LLM prompts."""
    tables = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()
    parts = []
    for (tbl,) in tables:
        cols = con.execute(
            f"SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_name='{tbl}' ORDER BY ordinal_position"
        ).fetchall()
        col_str = ", ".join(f"{c} {t}" for c, t in cols)
        parts.append(f"TABLE {tbl} ({col_str})")
    return "\n".join(parts)

