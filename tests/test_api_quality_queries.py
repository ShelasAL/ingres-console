"""Regression coverage for the console's reviewed groundwater-quality plans."""
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.api.server import _apply_scope, _deterministic_answer, _execute_plan, _plan_query
from ingres.generation.context_assembler import assemble_context
from ingres.retrieval.coverage_detector import CoverageResult
from ingres.schema.db_setup import SCHEMA_SQL


@pytest.fixture
def quality_db():
    con = duckdb.connect(":memory:")
    con.execute(SCHEMA_SQL)
    con.executemany(
        "INSERT INTO wells (well_id,state,district) VALUES (?,?,?)",
        [("RJ_JAI_1", "Rajasthan", "Jaipur"), ("RJ_JAI_2", "Rajasthan", "Jaipur"),
         ("GJ_SUR_1", "Gujarat", "Surat")],
    )
    con.executemany(
        "INSERT INTO gw_quality (record_id,well_id,sample_date,ph,tds_mg_l,nitrate_mg_l,"
        "fluoride_mg_l,arsenic_ug_l,potability) VALUES (?,?,?,?,?,?,?,?,?)",
        [("Q1", "RJ_JAI_1", "2022-01-01", 7.1, 300, 10, 0.8, 2, "non_potable"),
         ("Q2", "RJ_JAI_1", "2023-01-01", 7.2, 700, 12, 0.9, 2, "non_potable"),
         ("Q3", "RJ_JAI_2", "2023-01-01", 7.4, 350, 12, 0.7, 1, "potable"),
         ("Q4", "GJ_SUR_1", "2023-01-01", 7.0, 500, 15, 1.0, 3, "potable")],
    )
    yield con
    con.close()


def test_quality_comparison_without_single_location_aggregates_states(quality_db):
    plan = _plan_query(quality_db, "Compare water quality of different states")
    result = _execute_plan(quality_db, plan)

    assert plan["shape"] == "quality_comparison"
    assert result.success and result.row_count == 2
    by_state = {row["location"]: row for row in result.rows}
    assert by_state["Rajasthan"]["samples"] == 3
    assert by_state["Rajasthan"]["non_potable_samples"] == 2
    assert by_state["Rajasthan"]["potable_pct"] == pytest.approx(33.3)
    assert by_state["Gujarat"]["potable_pct"] == 100.0


def test_quality_comparison_can_limit_to_named_states(quality_db):
    plan = _plan_query(quality_db, "Compare water potability between Rajasthan and Gujarat")
    result = _execute_plan(quality_db, plan)
    assert set(plan["locations"]) == {"Rajasthan", "Gujarat"}
    assert {row["location"] for row in result.rows} == {"Rajasthan", "Gujarat"}


def test_quality_comparison_prefers_named_districts_over_their_states(quality_db):
    plan = _plan_query(quality_db, "Compare water quality between Jaipur and Surat")
    result = _execute_plan(quality_db, plan)

    assert plan["kind"] == "district"
    assert set(plan["locations"]) == {"Jaipur", "Surat"}
    assert {row["location"] for row in result.rows} == {"Jaipur", "Surat"}


def test_non_potable_listing_filters_latest_result_and_location(quality_db):
    plan = _plan_query(quality_db, "Show non potable wells in Jaipur")
    result = _execute_plan(quality_db, plan)
    assert plan["shape"] == "non_potable_list"
    assert result.row_count == 1
    assert result.rows[0]["well_id"] == "RJ_JAI_1"
    assert result.rows[0]["sample_date"].isoformat() == "2023-01-01"


def test_non_potable_count_uses_latest_sample(quality_db):
    plan = _plan_query(quality_db, "How many non-potable wells are in Rajasthan?")
    result = _execute_plan(quality_db, plan)
    assert plan["shape"] == "non_potable_count"
    assert sum(row["non_potable_wells"] for row in result.rows) == 1


def test_general_quality_summary_does_not_label_every_sample_non_potable(quality_db):
    query = "Summarize water quality in Jaipur"
    plan = _plan_query(quality_db, query)
    result = _execute_plan(quality_db, plan)
    coverage = CoverageResult(status="FULL", message="Complete sample coverage")
    ctx = assemble_context(result, [], coverage, plan["intent"])

    answer = _deterministic_answer(
        ctx, plan["intent"], coverage, result, query, plan.get("shape")
    )["answer"]

    assert "3 laboratory samples" in answer
    assert "currently classified non-potable" not in answer


def test_national_quality_summary_uses_reviewed_sql_without_a_location(quality_db):
    plan = _plan_query(quality_db, "Summarize groundwater quality")

    assert plan["intent"] == "STRUCTURED_QUALITY"
    assert plan["sql"]
    assert _execute_plan(quality_db, plan).row_count == 4


def test_level_comparison_plan_aggregates_each_named_district():
    con = duckdb.connect(":memory:")
    con.execute(SCHEMA_SQL)
    con.executemany(
        "INSERT INTO wells (well_id,state,district) VALUES (?,?,?)",
        [("RJ_JAI_1", "Rajasthan", "Jaipur"), ("GJ_SUR_1", "Gujarat", "Surat")],
    )
    con.executemany(
        "INSERT INTO gw_levels (record_id,well_id,measurement_date,depth_to_water_mbgl) "
        "VALUES (?,?,?,?)",
        [("L1", "RJ_JAI_1", "2021-06-01", 20.0), ("L2", "RJ_JAI_1", "2022-06-01", 24.0),
         ("L3", "GJ_SUR_1", "2021-06-01", 8.0), ("L4", "GJ_SUR_1", "2022-06-01", 10.0)],
    )

    plan = _plan_query(con, "Compare water levels in Jaipur and Surat")
    result = _execute_plan(con, plan)

    assert plan["intent"] == "STRUCTURED_LEVEL"
    assert plan["shape"] == "level_comparison"
    rows = {row["location"]: row for row in result.rows}
    assert set(rows) == {"Jaipur", "Surat"}
    assert rows["Jaipur"]["mean_depth_mbgl"] == 22.0
    assert rows["Surat"]["readings"] == 2


def test_unsupported_intent_becomes_an_explicit_out_of_scope_reason():
    coverage = _apply_scope(
        "UNSUPPORTED", CoverageResult(status="FULL", message="Complete coverage"),
    )

    assert coverage.status == "OUT_OF_SCOPE"
    assert "outside the INGRES groundwater dataset" in coverage.message
    assert coverage.suggestion


def test_potability_question_uses_latest_sample_counts(quality_db):
    plan = _plan_query(quality_db, "Is Surat groundwater potable?")
    result = _execute_plan(quality_db, plan)

    assert plan["shape"] == "potable_count"
    row = result.rows[0]
    assert row["location"] == "Surat"
    assert row["wells"] == 1
    assert row["potable_wells"] == 1
    assert row["non_potable_wells"] == 0


def test_unknown_place_is_rejected_instead_of_answering_national_data(quality_db):
    plan = _plan_query(quality_db, "What is the fluoride level in Paris?")

    assert plan["intent"] == "UNSUPPORTED"
    assert plan["unknown_location"] == "Paris"
    assert plan["sql"] == ""




def test_non_potable_total_is_presummed_for_the_model(quality_db):
    plan = _plan_query(quality_db, "How many non-potable wells are in Rajasthan?")
    result = _execute_plan(quality_db, plan)
    coverage = CoverageResult(status="FULL", message="Complete coverage")
    ctx = assemble_context(result, [], coverage, plan["intent"])

    assert ctx.stats["total_non_potable_wells"] == 1

    answer = _deterministic_answer(ctx, plan["intent"], coverage, result,
                                   "How many non-potable wells are in Rajasthan?",
                                   plan.get("shape"))

    assert "1 non-potable wells" in answer["answer"]

def test_comparison_highlights_state_direction_per_metric(quality_db):
    plan = _plan_query(quality_db, "Compare water potability between Rajasthan and Gujarat")
    result = _execute_plan(quality_db, plan)
    coverage = CoverageResult(status="FULL", message="Complete coverage")
    ctx = assemble_context(result, [], coverage, plan["intent"])

    highlights = ctx.stats["comparison_highlights"]

    assert highlights["potable_pct"] == {"highest": "Gujarat", "lowest": "Rajasthan"}
    assert highlights["mean_tds_mg_l"]["highest"] == "Gujarat"

def test_multipart_state_name_without_a_space_still_resolves():
    con = duckdb.connect(":memory:")
    con.execute(SCHEMA_SQL)
    con.execute(
        "INSERT INTO wells (well_id,state,district) VALUES (?,?,?)",
        ("UP_LKO_1", "Uttar Pradesh", "Lucknow"),
    )
    con.execute(
        "INSERT INTO gw_quality (record_id,well_id,sample_date,ph,tds_mg_l,nitrate_mg_l,"
        "fluoride_mg_l,arsenic_ug_l,potability) VALUES (?,?,?,?,?,?,?,?,?)",
        ("Q1", "UP_LKO_1", "2023-01-01", 7.2, 700, 50, 1.9, 12, "non_potable"),
    )

    plan = _plan_query(con, "can u list the non potable well in uttarpradesh?")
    result = _execute_plan(con, plan)

    assert plan["location"] == "Uttar Pradesh"
    assert plan["shape"] == "non_potable_list"
    assert [row["well_id"] for row in result.rows] == ["UP_LKO_1"]


def test_lowercase_unknown_place_is_rejected(quality_db):
    plan = _plan_query(quality_db, "list non potable wells in paris")

    assert plan["intent"] == "UNSUPPORTED"
    assert plan["unknown_location"].lower() == "paris"


def test_misspelled_district_is_rejected_not_answered_nationally(quality_db):
    plan = _plan_query(quality_db, "list non potable wells in jaipr")

    assert plan["intent"] == "UNSUPPORTED"
    assert plan["unknown_location"] == "jaipr"


def test_phrase_with_a_stopword_is_not_treated_as_a_place(quality_db):
    plan = _plan_query(quality_db, "water level trend in the last decade")

    assert plan.get("unknown_location") is None

def test_exceedance_lists_name_only_wells_over_the_limit(quality_db):
    plan = _plan_query(quality_db, "Show non potable wells in Jaipur")
    result = _execute_plan(quality_db, plan)
    coverage = CoverageResult(status="FULL", message="Complete coverage")
    ctx = assemble_context(result, [], coverage, plan["intent"])

    exceedances = ctx.stats.get("bis_exceedances", {})

    # Fixture: Jaipur latest non-potable well has TDS 700 (limit 500),
    # fluoride 0.9 (limit 1.5), nitrate 12 (limit 45), arsenic 2 (limit 10).
    assert exceedances["tds_mg_l"]["well_count"] == 1
    assert exceedances["tds_mg_l"]["examples"][0]["well_id"] == "RJ_JAI_1"
    assert "fluoride_mg_l" not in exceedances
    assert "arsenic_ug_l" not in exceedances

def test_refusal_reason_is_not_repeated_when_paraphrased():
    from frontend.api.server import _answer_states_reason

    message = "Location 'jaipr' is not in the INGRES database, which covers Indian states and districts only."

    assert _answer_states_reason(
        "Not answerable. The location 'jaipr' does not exist in the INGRES database.", message)
    assert not _answer_states_reason("No wells matched the filters.", message)

def test_fabricated_well_ids_are_detected():
    from frontend.api.server import _unknown_well_ids

    known = {"GW_UP_AGR_001", "NWIC_UT_Badhni"}
    text = ("GW_UP_AGR_001 (Agra) and NWIC_UT_Badhni are non-potable; "
            "GW_UP_Mathura was also mentioned.")

    assert _unknown_well_ids(text, known) == ["GW_UP_Mathura"]
    assert _unknown_well_ids("GW_UP_AGR_001 only", known) == []

def test_well_inventory_question_returns_counts_not_water_levels(quality_db):
    plan = _plan_query(quality_db, "How many wells are in Rajasthan?")
    result = _execute_plan(quality_db, plan)

    assert plan["shape"] == "well_count"
    assert result.rows[0]["location"] == "Rajasthan"
    assert result.rows[0]["wells"] == 2


def test_state_name_prefix_does_not_fall_back_to_a_matching_district():
    con = duckdb.connect(":memory:")
    con.execute(SCHEMA_SQL)
    con.execute(
        "INSERT INTO wells (well_id,state,district) VALUES (?,?,?)",
        ("DL_WEST_1", "Delhi", "West"),
    )

    plan = _plan_query(con, "What is the arsenic level in West Bengal?")

    assert plan["intent"] == "UNSUPPORTED"
    assert plan["unknown_location"] == "west bengal"


def test_extraction_comparison_uses_assessment_units(quality_db):
    plan = _plan_query(quality_db, "Compare extraction in Jaipur and Surat")

    assert plan["intent"] == "STRUCTURED_ASSESSMENT"
    assert plan["shape"] == "assessment_comparison"
    assert set(plan["locations"]) == {"Jaipur", "Surat"}

def test_bare_not_answerable_still_gets_the_reason_appended():
    from frontend.api.server import _answer_states_reason

    message = ("This question is outside the INGRES groundwater dataset, which covers water "
               "levels, quality, extraction, wells and aquifers.")

    assert not _answer_states_reason("Not answerable from INGRES data.", message)


def test_potability_summary_disambiguates_unsampled_wells(quality_db):
    plan = _plan_query(quality_db, "Is Surat groundwater potable?")
    result = _execute_plan(quality_db, plan)
    coverage = CoverageResult(status="FULL", message="Complete coverage")
    ctx = assemble_context(result, [], coverage, plan["intent"])

    assert ctx.stats["potability_summary"] == (
        "1 well total: 1 potable, 0 non-potable, 0 without a laboratory sample"
    )
