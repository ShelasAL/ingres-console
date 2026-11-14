"""
Tests for Response Generator: state determination, confidence calculation, and output structuring.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingres.generation.response_generator import (
    _determine_state,
    _determine_confidence,
    _format_comparison_facts,
    _format_evidence,
    generate_response
)
from ingres.generation.context_assembler import AssembledContext
from ingres.retrieval.coverage_detector import CoverageResult
from ingres.retrieval.text_to_sql import SQLResult
from ingres.generation.llm_client import GeminiClient


def test_determine_state_out_of_scope():
    coverage = CoverageResult(status="OUT_OF_SCOPE", message="Before 2015")
    sql_res = SQLResult(sql="", explanation="", rows=[], columns=[], row_count=0)
    ctx = AssembledContext(
        structured_summary="",
        semantic_chunks=[],
        coverage=coverage,
        sql_result=sql_res,
        well_coordinates=[],
        stats={}
    )
    state = _determine_state(ctx)
    assert state == "OUT_OF_SCOPE"


def test_determine_state_grounded():
    coverage = CoverageResult(status="FULL", message="Complete data")
    sql_res = SQLResult(
        sql="SELECT * FROM wells",
        explanation="Wells list",
        rows=[
            {"well_id": "GW_01", "depth_to_water_mbgl": 12.0, "data_quality_flag": "good"},
            {"well_id": "GW_02", "depth_to_water_mbgl": 12.5, "data_quality_flag": "good"},
            {"well_id": "GW_03", "depth_to_water_mbgl": 11.8, "data_quality_flag": "good"}
        ],
        columns=["well_id", "depth_to_water_mbgl", "data_quality_flag"],
        row_count=3
    )
    ctx = AssembledContext(
        structured_summary="rows",
        semantic_chunks=[],
        coverage=coverage,
        sql_result=sql_res,
        well_coordinates=[],
        stats={}
    )
    state = _determine_state(ctx)
    confidence = _determine_confidence(ctx, state)
    assert state == "GROUNDED"
    assert confidence == "HIGH"


def test_determine_state_human_review_high_variance():
    # If two wells in same query differ drastically (>15m)
    coverage = CoverageResult(status="FULL", message="Complete data")
    sql_res = SQLResult(
        sql="SELECT * FROM wells",
        explanation="Wells list",
        rows=[
            {"well_id": "GW_01", "depth_to_water_mbgl": 2.0, "data_quality_flag": "good"},
            {"well_id": "GW_02", "depth_to_water_mbgl": 25.0, "data_quality_flag": "good"}
        ],
        columns=["well_id", "depth_to_water_mbgl", "data_quality_flag"],
        row_count=2
    )
    ctx = AssembledContext(
        structured_summary="rows",
        semantic_chunks=[],
        coverage=coverage,
        sql_result=sql_res,
        well_coordinates=[],
        stats={}
    )
    state = _determine_state(ctx)
    assert state == "HUMAN_REVIEW"


def test_generate_response_dummy_mode():
    client = GeminiClient(api_key=None) # dummy mode
    coverage = CoverageResult(status="FULL", message="Complete data")
    sql_res = SQLResult(
        sql="SELECT * FROM wells",
        explanation="Wells list",
        rows=[
            {"well_id": "GW_01", "depth_to_water_mbgl": 12.0, "data_quality_flag": "good"}
        ],
        columns=["well_id", "depth_to_water_mbgl", "data_quality_flag"],
        row_count=1
    )
    ctx = AssembledContext(
        structured_summary="summary",
        semantic_chunks=[],
        coverage=coverage,
        sql_result=sql_res,
        well_coordinates=[],
        stats={}
    )
    resp = generate_response("What is the water level in Jaipur?", ctx, client)
    assert resp.state in ["GROUNDED", "PARTIAL"]
    assert len(resp.sources) > 0


def test_generate_response_handles_empty_provider_completion():
    class EmptyClient:
        def generate(self, prompt, temperature=0.2, **kwargs):
            return None

    coverage = CoverageResult(status="FULL", message="Complete data")
    sql_res = SQLResult(
        sql="SELECT * FROM wells",
        explanation="Wells list",
        rows=[{"well_id": "GW_01", "depth_to_water_mbgl": 12.0}],
        columns=["well_id", "depth_to_water_mbgl"],
        row_count=1,
    )
    ctx = AssembledContext(
        structured_summary="Retrieved row: GW_01, depth 12.0 mbgl.",
        semantic_chunks=[],
        coverage=coverage,
        sql_result=sql_res,
        well_coordinates=[],
        stats={},
    )

    response = generate_response("Show the latest water level", ctx, EmptyClient())

    assert "Retrieved row" in response.answer_text
    assert isinstance(response.raw_llm_output, str)


def test_generate_response_replaces_unstructured_table_with_grounded_fallback():
    class TableClient:
        def generate(self, prompt, temperature=0.2, **kwargs):
            return "| state | sample_count |\n| Bihar | 500 |"

        def _dynamic_hydro_synthesizer(self, prompt):
            return "**Answer**: 500 samples were retrieved.\n\n**Evidence**:\n- Source rows\n\n**Coverage Note**: Complete.\n\n**Confidence**: MEDIUM.\n\n**Recommendation**: Review samples."

    coverage = CoverageResult(status="FULL", message="Complete data")
    sql_res = SQLResult(
        sql="SELECT state, sample_count FROM quality_summary",
        explanation="Quality summary",
        rows=[{"well_id": "GW_01", "sample_count": 500}],
        columns=["well_id", "sample_count"],
        row_count=1,
    )
    ctx = AssembledContext(
        structured_summary="Bihar: 500 samples",
        semantic_chunks=[],
        coverage=coverage,
        sql_result=sql_res,
        well_coordinates=[],
        stats={"row_count": 1},
    )

    response = generate_response("Summarize water quality in Bihar", ctx, TableClient())

    assert response.answer_text == "500 samples were retrieved."
    assert "| state |" not in response.answer_text


def test_generate_response_keeps_model_summary_and_answer():
    class SummaryClient:
        def generate(self, prompt, **kwargs):
            return (
                "**Summary**: Bihar samples show elevated TDS.\n\n"
                "**Answer**: Mean TDS is 462.6 mg/L; 77 samples exceed 500 mg/L.\n\n"
                "**Evidence**:\n- TDS mean 462.6 mg/L\n\n"
                "**Coverage Note**: Full sample coverage.\n\n"
                "**Confidence**: MEDIUM - aggregated samples.\n\n"
                "**Recommendation**: Target the 77 high-TDS stations."
            )

    coverage = CoverageResult(status="FULL", message="Complete data")
    sql_res = SQLResult(
        sql="SELECT * FROM gw_quality",
        explanation="Quality rows",
        rows=[{"well_id": "GW_01", "tds_mg_l": 600.0}],
        columns=["well_id", "tds_mg_l"],
        row_count=1,
    )
    ctx = AssembledContext(
        structured_summary="GW_01: TDS 600",
        semantic_chunks=[],
        coverage=coverage,
        sql_result=sql_res,
        well_coordinates=[],
        stats={"row_count": 1},
    )

    response = generate_response("Summarize water quality in Bihar", ctx, SummaryClient())

    assert response.summary == "Bihar samples show elevated TDS."
    assert response.answer_text == "Mean TDS is 462.6 mg/L; 77 samples exceed 500 mg/L."
    assert response.coverage_note == "Full sample coverage."


def test_out_of_scope_prompt_demands_a_reason_not_substitute_data():
    class CapturingClient:
        prompt = ""

        def generate(self, prompt, **kwargs):
            self.prompt = prompt
            return (
                "**Summary**: The capital of France is outside the dataset.\n\n"
                "**Answer**: Not answerable from INGRES data.\n\n"
                "**Evidence**: none\n\n"
                "**Coverage Note**: Out of scope.\n\n"
                "**Confidence**: NONE\n\n"
                "**Recommendation**: Ask about Indian groundwater."
            )

    coverage = CoverageResult(
        status="OUT_OF_SCOPE",
        message="This question is outside the INGRES groundwater dataset.",
        suggestion="Ask about an Indian district.",
    )
    sql_res = SQLResult(sql="", explanation="", rows=[], columns=[], row_count=0)
    ctx = AssembledContext(
        structured_summary="", semantic_chunks=[], coverage=coverage,
        sql_result=sql_res, well_coordinates=[], stats={},
    )
    client = CapturingClient()

    response = generate_response("What is the capital of France?", ctx, client)

    assert "VALIDITY: NOT ANSWERABLE" in client.prompt
    assert "Do not substitute unrelated measurements" in client.prompt
    assert response.state == "OUT_OF_SCOPE"
    assert "Not answerable" in response.answer_text


def test_evidence_formatter_keeps_every_trend_year():
    rows = [
        {"district": "Jaipur", "year": 2015 + i, "season": "kharif",
         "avg_depth_mbgl": 10.0 + i, "n_readings": 3}
        for i in range(9)
    ]
    sql_res = SQLResult(
        sql="SELECT year FROM trend",
        explanation="Trend",
        rows=rows,
        columns=list(rows[0]),
        row_count=len(rows),
    )
    ctx = AssembledContext(
        structured_summary="", semantic_chunks=[],
        coverage=CoverageResult(status="FULL", message="Complete"),
        sql_result=sql_res, well_coordinates=[], stats={"row_count": len(rows)},
    )

    text = _format_evidence(ctx)

    assert "year=2015" in text
    assert "year=2023" in text
    assert "further rows not shown" not in text

def test_comparison_facts_pin_the_higher_area():
    rows = [
        {"location": "Bihar", "mean_tds_mg_l": 489.05, "potable_pct": 92.0},
        {"location": "Gujarat", "mean_tds_mg_l": 516.56, "potable_pct": 43.3},
    ]
    sql_res = SQLResult(
        sql="SELECT ...", explanation="Comparison", rows=rows,
        columns=list(rows[0]), row_count=2,
    )
    ctx = AssembledContext(
        structured_summary="", semantic_chunks=[],
        coverage=CoverageResult(status="FULL", message="Complete"),
        sql_result=sql_res, well_coordinates=[],
        stats={"comparison_highlights": {
            "mean_tds_mg_l": {"highest": "Gujarat", "lowest": "Bihar"},
            "potable_pct": {"highest": "Bihar", "lowest": "Gujarat"},
        }},
    )

    facts = _format_comparison_facts(ctx)

    assert "mean_tds_mg_l: Gujarat 516.56 is higher than Bihar 489.05" in facts
    assert "potable_pct: Bihar 92 is higher than Gujarat 43.3" in facts
    assert "difference 27.51" in facts

def test_friendly_labels_replace_raw_keys_in_evidence_output():
    rows = [
        {"location": "Bihar", "samples": 1530, "potable_samples": 1407,
         "non_potable_samples": 123, "potable_pct": 92.0, "mean_tds_mg_l": 489.05},
    ]
    sql_res = SQLResult(
        sql="SELECT ...", explanation="Comparison",
        rows=rows, columns=list(rows[0]), row_count=1,
    )
    ctx = AssembledContext(
        structured_summary="", semantic_chunks=[],
        coverage=CoverageResult(status="FULL", message="Complete"),
        sql_result=sql_res, well_coordinates=[],
        stats={"row_count": 1},
    )

    text = _format_evidence(ctx)

    assert "non_potable_samples" not in text
    assert "mean_tds_mg_l" not in text
    assert "non-potable samples=123" in text
    assert "mean TDS (mg/L)=489.05" in text


def test_prompt_exposes_friendly_stat_keys():
    class CapturingClient:
        prompt = ""

        def generate(self, prompt, **kwargs):
            CapturingClient.prompt = prompt
            return (
                "**Summary**: Bihar water quality.\n\n"
                "**Answer**: Mean TDS is 462.6 mg/L.\n\n"
                "**Evidence**:\n- TDS mean 462.6 mg/L\n\n"
                "**Coverage Note**: Complete.\n\n"
                "**Confidence**: MEDIUM.\n\n"
                "**Recommendation**: Review high-TDS stations."
            )

    sql_res = SQLResult(
        sql="SELECT 1", explanation="Quick",
        rows=[{"well_id": "GW_01", "tds_mg_l": 600.0}],
        columns=["well_id", "tds_mg_l"], row_count=1,
    )
    ctx = AssembledContext(
        structured_summary="", semantic_chunks=[],
        coverage=CoverageResult(status="FULL", message="Complete"),
        sql_result=sql_res, well_coordinates=[],
        stats={"row_count": 1, "mean_tds_mg_l": 462.6,
               "non_potable_samples": 85, "potable_pct": 92.0},
    )

    generate_response("Summarize water quality in Bihar",
                      ctx, CapturingClient())

    prompt = CapturingClient.prompt
    assert "mean_tds_mg_l" not in prompt
    assert "non_potable_samples" not in prompt
    assert "mean TDS (mg/L)" in prompt
    assert "non-potable samples" in prompt
    assert "total wells" not in prompt  # raw stats were absent in this fixture


def test_sanitize_stats_echo():
    from ingres.generation.response_generator import sanitize_stats_echo

    text = ("Bihar: total_potable_wells=399, potable_pct=92.0; "
            "non_potable_samples=123; over_exploited_units=8")

    cleaned = sanitize_stats_echo(text)
    assert "potable_pct" not in cleaned
    assert "non_potable_samples" not in cleaned
    assert "total potable wells=399" in cleaned
    assert "over-exploited units" in cleaned
    assert "total potable wells" in cleaned
