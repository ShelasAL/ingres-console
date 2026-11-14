"""
INGRES Evaluation Runner.
Executes all 30 test cases across Normal, Edge, Incomplete, and Ambiguous categories,
comparing the Hybrid RAG pipeline against the TF-IDF Baseline.
Produces evaluation report and saves docs/evaluation_report.md.

Run: py -3 run_evaluation.py
"""
import sys
import time
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingres.schema.db_setup import get_connection
from ingres.retrieval.query_router import route_query
from ingres.retrieval.text_to_sql import execute_query
from ingres.retrieval.coverage_detector import check_coverage
from ingres.retrieval.vector_search import semantic_search
from ingres.retrieval.geo_filter import get_well_coordinates
from ingres.generation.context_assembler import assemble_context
from ingres.generation.response_generator import generate_response
from ingres.generation.llm_client import get_llm_client
from ingres.evaluation.baseline import TFIDFBaseline
from ingres.evaluation.metrics import load_test_cases, compute_metrics, EvalResult


def main():
    print("=========================================================")
    print("🌊 INGRES Ground Water Data Query Assistant - Evaluation")
    print("=========================================================\n")

    con = get_connection()
    llm = get_llm_client()
    baseline = TFIDFBaseline(con)
    cases = load_test_cases()

    print(f"Loaded {len(cases)} test cases across categories: normal, edge, incomplete, ambiguous.\n")

    results: list[EvalResult] = []

    for idx, case in enumerate(cases, 1):
        t0 = time.time()

        # 1. Query understanding & routing
        route_res = route_query(case.query, llm_client=llm)

        # 2. Coverage Detection
        coverage_res = check_coverage(case.query, route_res.entities, con)

        # 3. Retrieval
        sql_res = execute_query(
            query=case.query,
            entities=route_res.entities,
            intent=route_res.intent,
            con=con,
            llm_client=llm
        )

        semantic_chunks = []
        if route_res.intent in ["SEMANTIC_CONCEPTUAL", "UNSUPPORTED"] or not sql_res.success or sql_res.row_count == 0:
            semantic_chunks = semantic_search(case.query, n_results=2)

        # 4. Geospatial
        locs = route_res.entities.get("locations", [])
        coords = get_well_coordinates(locs, con) if locs else []

        # 5. Context & Generation
        ctx = assemble_context(
            sql_result=sql_res,
            semantic_chunks=semantic_chunks,
            coverage=coverage_res,
            intent=route_res.intent,
            well_coordinates=coords
        )

        resp = generate_response(case.query, ctx, llm)
        latency = (time.time() - t0) * 1000

        # Baseline execution
        base_res = baseline.query(case.query, top_k=2)

        # Evaluate criteria
        # Intent evaluation
        intent_ok = (route_res.intent == case.expected_intent) or (
            case.expected_intent in ["STRUCTURED_LEVEL", "STRUCTURED_QUALITY", "STRUCTURED_ASSESSMENT"]
            and route_res.intent.startswith("STRUCTURED")
        )

        # Coverage evaluation
        coverage_ok = True
        if case.expected_coverage_status:
            coverage_ok = (coverage_res.status == case.expected_coverage_status)

        # Provenance check
        has_prov = len(resp.sources) > 0 or len(resp.evidence_list) > 0
        prov_ok = has_prov if case.should_have_provenance else True

        # Overall pass check
        if case.category == "edge" and case.expected_type == "out_of_range_temporal":
            passed = (coverage_res.status == "OUT_OF_SCOPE")
        elif case.expected_coverage_status == "FULL":
            passed = (sql_res.row_count > 0 and prov_ok)
        elif case.category == "ambiguous":
            passed = (coverage_res.status in ["INSUFFICIENT", "PARTIAL"])
        elif case.category == "incomplete":
            passed = (coverage_res.status in ["PARTIAL", "FULL"] and (sql_res.row_count > 0 or len(semantic_chunks) > 0))
        else: # normal
            passed = (sql_res.row_count > 0 and prov_ok)

        eval_res = EvalResult(
            case_id=case.id,
            query=case.query,
            category=case.category,
            predicted_intent=route_res.intent,
            intent_correct=intent_ok,
            sql_executed=sql_res.success,
            sql_returned_rows=sql_res.row_count > 0,
            coverage_status=coverage_res.status,
            coverage_flag_correct=coverage_ok,
            has_provenance=has_prov,
            response_state=resp.state,
            confidence=resp.confidence,
            answer_preview=resp.answer_text[:80].replace("\n", " "),
            latency_ms=latency,
            baseline_answer_preview=base_res.answer[:80].replace("\n", " "),
            passed=passed
        )
        results.append(eval_res)

        status_sym = "✅" if passed else "❌"
        print(f"[{idx:02d}/{len(cases):02d}] {status_sym} {case.id:<8} ({case.category:<10}) Intent:{route_res.intent:<20} Coverage:{coverage_res.status:<12} Passed:{passed}")

    # Compute overall metrics
    report = compute_metrics(results)
    print("\n" + report.to_markdown())

    # Write report file
    docs_dir = Path(__file__).resolve().parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_file = docs_dir / "evaluation_report.md"
    report_file.write_text(report.to_markdown(), encoding="utf-8")
    print(f"\n📊 Report saved to {report_file}")


if __name__ == "__main__":
    main()
