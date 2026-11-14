"""
Evaluation metrics for INGRES components.
Computes SQL accuracy, coverage detection recall, provenance precision,
faithfulness, and latency.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from loguru import logger


@dataclass
class EvalCase:
    id: str
    query: str
    category: str                   # normal, edge, incomplete, ambiguous
    expected_intent: str
    expected_type: str              # structured_query, coverage_gap, partial_data, etc.
    acceptance_criterion: str
    gold_answer_keywords: list[str] = field(default_factory=list)
    expected_coverage_status: Optional[str] = None
    should_have_provenance: bool = True


@dataclass
class EvalResult:
    case_id: str
    query: str
    category: str
    # Retrieval
    predicted_intent: str
    intent_correct: bool
    sql_executed: bool
    sql_returned_rows: bool
    # Coverage
    coverage_status: str
    coverage_flag_correct: bool
    # Provenance
    has_provenance: bool
    # Response
    response_state: str
    confidence: str
    answer_preview: str
    # Timing
    latency_ms: float
    # Baseline
    baseline_answer_preview: str = ""
    # Overall
    passed: bool = False


@dataclass
class MetricsReport:
    total: int = 0
    intent_accuracy: float = 0.0
    sql_success_rate: float = 0.0
    coverage_detection_recall: float = 0.0
    provenance_precision: float = 0.0
    overall_pass_rate: float = 0.0
    mean_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    failure_patterns: dict = field(default_factory=dict)
    category_breakdown: dict = field(default_factory=dict)
    results: list[EvalResult] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# INGRES Evaluation Report\n",
            "## Overall Metrics\n",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total test cases | {self.total} |",
            f"| Intent accuracy | {self.intent_accuracy:.1%} |",
            f"| SQL success rate | {self.sql_success_rate:.1%} |",
            f"| Coverage detection recall | {self.coverage_detection_recall:.1%} |",
            f"| Provenance precision | {self.provenance_precision:.1%} |",
            f"| Overall pass rate | {self.overall_pass_rate:.1%} |",
            f"| Mean latency (ms) | {self.mean_latency_ms:.0f} |",
            f"| P95 latency (ms) | {self.p95_latency_ms:.0f} |",
            "",
            "## Category Breakdown\n",
        ]
        for cat, stats in self.category_breakdown.items():
            lines.append(f"### {cat.title()}")
            lines.append(f"- Total: {stats.get('total', 0)}")
            lines.append(f"- Passed: {stats.get('passed', 0)}")
            lines.append(f"- Pass rate: {stats.get('pass_rate', 0):.1%}")
            lines.append("")

        lines.append("## Failure Patterns\n")
        for pattern, count in self.failure_patterns.items():
            lines.append(f"- {pattern}: {count} cases")

        lines.append("\n## Detailed Results\n")
        lines.append("| Case ID | Category | Intent ✓ | SQL ✓ | Coverage ✓ | Provenance ✓ | Passed | Latency |")
        lines.append("|---------|----------|-----------|-------|-----------|--------------|--------|---------|")
        for r in self.results:
            lines.append(
                f"| {r.case_id} | {r.category} | "
                f"{'✅' if r.intent_correct else '❌'} | "
                f"{'✅' if r.sql_returned_rows else '❌'} | "
                f"{'✅' if r.coverage_flag_correct else '❌'} | "
                f"{'✅' if r.has_provenance else '❌'} | "
                f"{'✅' if r.passed else '❌'} | "
                f"{r.latency_ms:.0f}ms |"
            )
        return "\n".join(lines)


def load_test_cases(path: Optional[Path] = None) -> list[EvalCase]:
    """Load test cases from JSON fixture."""
    if path is None:
        path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "test_cases.json"
    with open(path) as f:
        data = json.load(f)
    cases = []
    for category, items in data.items():
        for item in items:
            cases.append(EvalCase(
                id=item["id"],
                query=item["query"],
                category=category.replace("_cases", ""),
                expected_intent=item.get("expected_intent", ""),
                expected_type=item.get("expected_type", ""),
                acceptance_criterion=item.get("acceptance_criterion", ""),
                gold_answer_keywords=item.get("gold_keywords", []),
                expected_coverage_status=item.get("expected_coverage_status"),
                should_have_provenance=item.get("should_have_provenance", True),
            ))
    return cases


def compute_metrics(results: list[EvalResult]) -> MetricsReport:
    """Aggregate evaluation results into a MetricsReport."""
    import numpy as np

    if not results:
        return MetricsReport()

    n = len(results)
    latencies = [r.latency_ms for r in results]

    # Per-category stats
    categories = {}
    for r in results:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0}
        categories[cat]["total"] += 1
        if r.passed:
            categories[cat]["passed"] += 1

    for cat in categories:
        t = categories[cat]["total"]
        p = categories[cat]["passed"]
        categories[cat]["pass_rate"] = p / t if t > 0 else 0.0

    # Failure patterns
    patterns: dict[str, int] = {}
    for r in results:
        if not r.passed:
            if not r.intent_correct:
                patterns["Wrong intent"] = patterns.get("Wrong intent", 0) + 1
            if not r.sql_returned_rows:
                patterns["SQL returned no rows"] = patterns.get("SQL returned no rows", 0) + 1
            if not r.coverage_flag_correct:
                patterns["Coverage not detected"] = patterns.get("Coverage not detected", 0) + 1
            if not r.has_provenance:
                patterns["Missing provenance"] = patterns.get("Missing provenance", 0) + 1

    coverage_cases = [r for r in results if r.coverage_status]
    return MetricsReport(
        total=n,
        intent_accuracy=sum(r.intent_correct for r in results) / n,
        sql_success_rate=sum(r.sql_returned_rows for r in results) / n,
        coverage_detection_recall=sum(r.coverage_flag_correct for r in results) / n,
        provenance_precision=sum(r.has_provenance for r in results) / n,
        overall_pass_rate=sum(r.passed for r in results) / n,
        mean_latency_ms=float(np.mean(latencies)),
        p95_latency_ms=float(np.percentile(latencies, 95)),
        failure_patterns=patterns,
        category_breakdown=categories,
        results=results,
    )

