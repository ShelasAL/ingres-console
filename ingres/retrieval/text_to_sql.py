"""
Text-to-SQL engine with two-pass LLM generation + safety validation.
Executes read-only queries against the DuckDB groundwater database.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

import duckdb
import pandas as pd
from loguru import logger

from ingres.schema.db_setup import get_schema_context

# Columns that exist in each table (for basic validation)
VALID_COLUMNS = {
    "wells": {"well_id", "state", "district", "block", "latitude", "longitude",
              "well_type", "aquifer_type", "depth_mbgl", "installation_year", "data_source"},
    "gw_levels": {"record_id", "well_id", "measurement_date", "season",
                  "depth_to_water_mbgl", "water_level_mbsl", "measurement_method",
                  "data_quality_flag", "remarks"},
    "gw_quality": {"record_id", "well_id", "sample_date", "ph", "tds_mg_l",
                   "nitrate_mg_l", "fluoride_mg_l", "arsenic_ug_l", "iron_mg_l",
                   "hardness_mg_l", "potability", "lab_id"},
    "assessment_units": {"unit_id", "state", "district", "block_taluk",
                         "annual_gw_recharge_mcm", "extractable_gw_mcm",
                         "total_extraction_mcm", "stage_of_extraction_pct",
                         "category", "assessment_year", "methodology"},
}

DANGEROUS_KEYWORDS = re.compile(
    r"\b(DROP|INSERT|UPDATE|DELETE|ALTER|TRUNCATE|CREATE|REPLACE|MERGE)\b",
    re.IGNORECASE,
)


@dataclass
class SQLResult:
    sql: str
    explanation: str
    rows: list[dict]
    columns: list[str]
    row_count: int
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=self.columns)


def _validate_sql(sql: str) -> Optional[str]:
    """Return an error message if SQL is unsafe, else None."""
    if DANGEROUS_KEYWORDS.search(sql):
        return "Generated SQL contains disallowed DML/DDL keyword."
    if not re.search(r"\bSELECT\b", sql, re.IGNORECASE):
        return "Generated SQL is not a SELECT statement."
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        # Auto-append LIMIT to prevent runaway queries
        logger.warning("SQL missing LIMIT — will append LIMIT 500")
    return None


def _append_limit(sql: str, limit: int = 500) -> str:
    """Append LIMIT if not already present."""
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = sql.rstrip(";").rstrip() + f"\nLIMIT {limit};"
    return sql


# ── Template SQL for common query patterns ────────────────────────────────────
TEMPLATES = {
    "level_district_season_year": """
SELECT w.district, w.state, l.season, l.measurement_date,
       l.depth_to_water_mbgl, l.data_quality_flag, w.well_id
FROM gw_levels l
JOIN wells w ON l.well_id = w.well_id
WHERE LOWER(w.district) = LOWER('{district}')
  AND EXTRACT(YEAR FROM l.measurement_date) = {year}
  AND l.season = '{season}'
  AND l.data_quality_flag != 'missing'
ORDER BY l.measurement_date
LIMIT 500;
""",
    "quality_district": """
SELECT w.district, w.state, q.sample_date, q.ph, q.tds_mg_l,
       q.fluoride_mg_l, q.arsenic_ug_l, q.nitrate_mg_l, q.potability, w.well_id
FROM gw_quality q
JOIN wells w ON q.well_id = w.well_id
WHERE LOWER(w.district) = LOWER('{district}')
ORDER BY q.sample_date DESC
LIMIT 500;
""",
    "assessment_state": """
SELECT district, state, category, stage_of_extraction_pct,
       annual_gw_recharge_mcm, total_extraction_mcm, assessment_year
FROM assessment_units
WHERE LOWER(state) = LOWER('{state}')
ORDER BY assessment_year DESC, stage_of_extraction_pct DESC
LIMIT 500;
""",
    "assessment_district": """
SELECT district, state, category, stage_of_extraction_pct,
       annual_gw_recharge_mcm, total_extraction_mcm, assessment_year
FROM assessment_units
WHERE LOWER(district) = LOWER('{district}')
ORDER BY assessment_year DESC, stage_of_extraction_pct DESC
LIMIT 500;
""",
    "over_exploited_all": """
SELECT district, state, category, stage_of_extraction_pct, assessment_year
FROM assessment_units
WHERE category = 'over_exploited'
ORDER BY stage_of_extraction_pct DESC
LIMIT 500;
""",
    "level_trend": """
SELECT w.district, l.season, EXTRACT(YEAR FROM l.measurement_date) AS year,
       AVG(l.depth_to_water_mbgl) AS avg_depth_mbgl,
       COUNT(*) AS n_readings
FROM gw_levels l
JOIN wells w ON l.well_id = w.well_id
WHERE LOWER(w.district) = LOWER('{district}')
  AND l.data_quality_flag != 'missing'
GROUP BY w.district, l.season, year
ORDER BY year, l.season
LIMIT 500;
""",
    "quality_state": """
SELECT w.district, w.state, q.sample_date, q.ph, q.tds_mg_l,
       q.fluoride_mg_l, q.arsenic_ug_l, q.nitrate_mg_l, q.potability, w.well_id
FROM gw_quality q
JOIN wells w ON q.well_id = w.well_id
WHERE LOWER(w.state) = LOWER('{state}')
ORDER BY q.sample_date DESC
LIMIT 500;
""",
    "potable_ranking": """
SELECT w.well_id, w.district, w.state, COUNT(*) AS samples,
       SUM(CASE WHEN q.potability = 'potable' THEN 1 ELSE 0 END) AS potable_samples,
       ROUND(SUM(CASE WHEN q.potability = 'potable' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS potable_pct
FROM gw_quality q
JOIN wells w ON q.well_id = w.well_id
WHERE LOWER({column}) = LOWER('{location}')
GROUP BY w.well_id, w.district, w.state
ORDER BY potable_pct DESC, samples DESC
LIMIT 500;
""",
    "potable_count": """
WITH latest AS (
    SELECT well_id, potability,
           ROW_NUMBER() OVER (PARTITION BY well_id ORDER BY sample_date DESC) AS rn
    FROM gw_quality
)
SELECT COUNT(*) AS wells,
       SUM(CASE WHEN l.potability = 'potable' THEN 1 ELSE 0 END) AS potable_wells,
       SUM(CASE WHEN l.potability = 'non_potable' THEN 1 ELSE 0 END) AS non_potable_wells,
       SUM(CASE WHEN l.potability IS NULL THEN 1 ELSE 0 END) AS without_sample
FROM wells w
LEFT JOIN latest l ON l.well_id = w.well_id AND l.rn = 1
WHERE LOWER({column}) = LOWER('{location}')
LIMIT 500;
""",
    "level_state_trend": """
SELECT w.state, l.season, EXTRACT(YEAR FROM l.measurement_date) AS year,
       AVG(l.depth_to_water_mbgl) AS avg_depth_mbgl,
       COUNT(*) AS n_readings
FROM gw_levels l
JOIN wells w ON l.well_id = w.well_id
WHERE LOWER(w.state) = LOWER('{state}')
  AND l.data_quality_flag != 'missing'
GROUP BY w.state, l.season, year
ORDER BY year, l.season
LIMIT 500;
""",
    "level_state_year": """
SELECT w.district, w.state, l.season, l.measurement_date,
       l.depth_to_water_mbgl, l.data_quality_flag, w.well_id
FROM gw_levels l
JOIN wells w ON l.well_id = w.well_id
WHERE LOWER(w.state) = LOWER('{state}')
  AND EXTRACT(YEAR FROM l.measurement_date) = {year}
  AND l.data_quality_flag != 'missing'
ORDER BY l.measurement_date
LIMIT 500;
""",
}



def _llm_to_sql(query: str, entities: dict, schema_ctx: str, llm_client) -> dict:
    """Use LLM to generate SQL from a natural language query."""
    SQL_PROMPT = f"""
You are a SQL expert for a groundwater database. Generate a READ-ONLY DuckDB SQL query.

Database Schema:
{schema_ctx}

Units and domain rules:
- depth_to_water_mbgl: meters below ground level (higher number = deeper water table)
- tds_mg_l: Total Dissolved Solids in mg/L (BIS limit: 500 mg/L)
- fluoride_mg_l: Fluoride in mg/L (BIS limit: 1.5 mg/L)
- nitrate_mg_l: Nitrate in mg/L (BIS limit: 45 mg/L)
- arsenic_ug_l: Arsenic in micrograms/L (BIS limit: 10 µg/L)
- stage_of_extraction_pct: >100% = over-exploited
- season values: pre_monsoon, post_monsoon, rabi, kharif
- data_quality_flag values: good, suspect, missing, estimated

STRICT RULES:
- NEVER use DROP, INSERT, UPDATE, DELETE, ALTER, TRUNCATE
- Always include LIMIT 500
- JOIN wells table when filtering by district/state
- Filter out data_quality_flag = 'missing' unless user asks for missing data
- Use LOWER() for string comparisons
- Return column aliases in snake_case

User query: "{query}"
Extracted entities: {json.dumps(entities)}

Return ONLY valid JSON (no markdown):
{{
  "sql": "<complete SQL>",
  "explanation": "<one sentence about what the SQL retrieves>",
  "required_tables": ["<table names used>"]
}}
"""
    try:
        text = llm_client.generate(SQL_PROMPT, temperature=0.0)
        clean = re.sub(r"```(?:json|sql)?|```", "", text).strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"LLM SQL generation failed: {e}")
        return {}


def _location_kind(con, loc):
    """Return 'state', 'district' or 'unknown' for a location name."""
    if con is None or not loc:
        return "district"
    try:
        district_hits = con.execute(
            "SELECT COUNT(*) FROM wells WHERE LOWER(district) = ?", [str(loc).lower()]
        ).fetchone()[0]
        state_hits = con.execute(
            "SELECT COUNT(*) FROM wells WHERE LOWER(state) = ?", [str(loc).lower()]
        ).fetchone()[0]
    except Exception:
        return "district"
    if district_hits:
        return "district"
    if state_hits:
        return "state"
    return "unknown"


def _template_sql(entities: dict, intent: str, con=None, query: str = "") -> Optional[str]:
    """Match the question to a reviewed SQL template.

    Resolves whether the extracted location is a state or a district, and
    special-cases potability questions (ranking and counts).
    """
    locs = entities.get("locations", [])
    loc = locs[0] if locs else None
    year = None
    time_range = entities.get("time_range", "")
    if time_range:
        years = re.findall(r"\d{4}", str(time_range))
        if years:
            year = int(years[0])

    q = (query or "").lower()
    kind = _location_kind(con, loc) if loc else "unknown"
    column = "w.state" if kind == "state" else "w.district"

    if intent == "STRUCTURED_ASSESSMENT" and not loc:
        return TEMPLATES["over_exploited_all"]
    if intent == "STRUCTURED_ASSESSMENT" and loc:
        if kind == "state":
            return TEMPLATES["assessment_state"].format(state=loc)
        return TEMPLATES["assessment_district"].format(district=loc)

    if loc and intent == "STRUCTURED_QUALITY" and "potable" in q:
        count_words = ("how many" in q or "number of" in q or "count" in q)
        if count_words and "well" in q:
            return TEMPLATES["potable_count"].format(column=column, location=loc)
        return TEMPLATES["potable_ranking"].format(column=column, location=loc)

    if intent == "STRUCTURED_QUALITY" and loc:
        if kind == "state":
            return TEMPLATES["quality_state"].format(state=loc)
        return TEMPLATES["quality_district"].format(district=loc)

    if intent == "STRUCTURED_LEVEL" and loc and year:
        if kind == "state":
            return TEMPLATES["level_state_year"].format(state=loc, year=year)
        return TEMPLATES["level_district_season_year"].format(
            district=loc, year=year, season="pre_monsoon"
        )
    if intent == "STRUCTURED_LEVEL" and loc:
        if kind == "state":
            return TEMPLATES["level_state_trend"].format(state=loc)
        return TEMPLATES["level_trend"].format(district=loc)
    return None


def execute_query(
    query: str,
    entities: dict,
    intent: str,
    con: duckdb.DuckDBPyConnection,
    llm_client=None,
) -> SQLResult:
    """
    Generate and execute a SQL query. Uses templates first, then LLM fallback.
    """
    schema_ctx = get_schema_context(con)
    sql = None
    explanation = "Template-generated query"

    # 1. Try template
    sql = _template_sql(entities, intent, con, query)

    # 2. LLM fallback
    if sql is None and llm_client is not None:
        llm_data = _llm_to_sql(query, entities, schema_ctx, llm_client)
        sql = llm_data.get("sql", "")
        explanation = llm_data.get("explanation", "LLM-generated query")

    if not sql:
        return SQLResult(
            sql="", explanation="Could not generate SQL",
            rows=[], columns=[], row_count=0,
            error="No SQL could be generated for this query",
        )

    # 3. Validate
    err = _validate_sql(sql)
    if err:
        logger.error(f"SQL validation failed: {err}")
        return SQLResult(sql=sql, explanation=explanation,
                         rows=[], columns=[], row_count=0, error=err)

    sql = _append_limit(sql)
    logger.debug(f"Executing SQL:\n{sql}")

    # 4. Execute
    try:
        result = con.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows_raw = result.fetchall()
        rows = [dict(zip(columns, r)) for r in rows_raw]
        return SQLResult(sql=sql, explanation=explanation,
                         rows=rows, columns=columns, row_count=len(rows))
    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        return SQLResult(sql=sql, explanation=explanation,
                         rows=[], columns=[], row_count=0, error=str(e))

