"""
Context Assembler: merges retrieved structured data and semantic chunks
into a unified context string for the LLM generator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from loguru import logger

from ingres.retrieval.text_to_sql import SQLResult
from ingres.retrieval.coverage_detector import CoverageResult


@dataclass
class AssembledContext:
    """Combined evidence context passed to the LLM generator."""
    structured_summary: str       # Formatted table/stats from SQL
    semantic_chunks: list[dict]   # Knowledge base chunks
    coverage: CoverageResult
    sql_result: SQLResult
    well_coordinates: list[dict]  # For map rendering
    stats: dict                   # Computed statistics


def _format_dataframe_for_llm(df: pd.DataFrame, max_rows: int = 20) -> str:
    """Convert a DataFrame to a compact table for the LLM."""
    if df.empty:
        return "No records found."
    subset = df.head(max_rows).copy()
    for col in subset.select_dtypes(include="float").columns:
        subset[col] = subset[col].round(2)
    try:
        return subset.to_markdown(index=False)
    except Exception:
        return subset.to_string(index=False)


def _compute_stats(df: pd.DataFrame, intent: str) -> dict:
    """Compute summary statistics from the SQL result DataFrame."""
    stats = {"row_count": len(df)}
    if df.empty:
        return stats

    if intent == "STRUCTURED_LEVEL" and "depth_to_water_mbgl" in df.columns:
        col = df["depth_to_water_mbgl"].dropna()
        if not col.empty:
            stats.update({
                "mean_depth_mbgl": round(col.mean(), 2),
                "min_depth_mbgl": round(col.min(), 2),
                "max_depth_mbgl": round(col.max(), 2),
                "std_depth_mbgl": round(col.std(), 2),
                "n_good_readings": int((df.get("data_quality_flag", pd.Series()) == "good").sum()),
            })

    elif intent == "STRUCTURED_QUALITY":
        for param in ["ph", "tds_mg_l", "fluoride_mg_l", "nitrate_mg_l", "arsenic_ug_l"]:
            if param in df.columns:
                col = df[param].dropna()
                if not col.empty:
                    stats[f"{param}_mean"] = round(col.mean(), 3)

        # BIS violation counts
        violations = {}
        if "fluoride_mg_l" in df.columns:
            violations["fluoride_>1.5"] = int((df["fluoride_mg_l"] > 1.5).sum())
        if "tds_mg_l" in df.columns:
            violations["tds_>500"] = int((df["tds_mg_l"] > 500).sum())
        if "nitrate_mg_l" in df.columns:
            violations["nitrate_>45"] = int((df["nitrate_mg_l"] > 45).sum())
        if violations:
            stats["bis_violations"] = violations

        # Well-level lists: name the exact wells over each limit. Without
        # this, models call any high-ish value an exceedance.
        limits = {
            "fluoride_mg_l": 1.5, "tds_mg_l": 500,
            "nitrate_mg_l": 45, "arsenic_ug_l": 10,
        }
        if "well_id" in df.columns:
            exceedances = {}
            for column, limit in limits.items():
                if column not in df.columns:
                    continue
                hit = df[df[column] > limit]
                if hit.empty:
                    continue
                examples = []
                for _, row in hit.head(8).iterrows():
                    item = {"well_id": row.get("well_id"), "value": round(float(row[column]), 2)}
                    if row.get("district"):
                        item["district"] = row["district"]
                    examples.append(item)
                exceedances[column] = {
                    "limit": limit,
                    "well_count": int(hit["well_id"].nunique()),
                    "examples": examples,
                }
            if exceedances:
                stats["bis_exceedances"] = exceedances

        # Pre-summed counts: models reliably mis-add district-level rows.
        if "non_potable_wells" in df.columns:
            stats["total_non_potable_wells"] = int(df["non_potable_wells"].fillna(0).sum())
        if "potable_wells" in df.columns:
            stats["total_potable_wells"] = int(df["potable_wells"].fillna(0).sum())
        if "wells" in df.columns:
            stats["total_wells"] = int(df["wells"].fillna(0).sum())

        # One unambiguous sentence for yes/no potability answers.
        if "potable_wells" in df.columns and len(df) == 1:
            row = df.iloc[0]
            total = int(row.get("wells") or 0)
            stats["potability_summary"] = (
                "%d well%s total: %d potable, %d non-potable, %d without a laboratory sample"
                % (total, "" if total == 1 else "s",
                   int(row.get("potable_wells") or 0),
                   int(row.get("non_potable_wells") or 0),
                   int(row.get("without_sample") or 0))
            )

        # Comparison answers flip directions when the model reads rows itself.
        # Name the highest and lowest area per metric explicitly.
        if "location" in df.columns and 2 <= len(df) <= 12:
            highlights = {}
            for col in df.columns:
                if col == "location":
                    continue
                series = pd.to_numeric(df[col], errors="coerce")
                if series.notna().sum() < 2 or series.nunique() < 2:
                    continue
                high = df.loc[series.idxmax(), "location"]
                low = df.loc[series.idxmin(), "location"]
                if high != low:
                    highlights[col] = {"highest": str(high), "lowest": str(low)}
            if highlights:
                stats["comparison_highlights"] = highlights

    elif intent == "STRUCTURED_ASSESSMENT" and "stage_of_extraction_pct" in df.columns:
        col = df["stage_of_extraction_pct"].dropna()
        if not col.empty:
            stats.update({
                "mean_stage_pct": round(col.mean(), 1),
                "max_stage_pct": round(col.max(), 1),
            })
        if "category" in df.columns:
            stats["category_counts"] = df["category"].value_counts().to_dict()

    return stats


def assemble_context(
    sql_result: SQLResult,
    semantic_chunks: list[dict],
    coverage: CoverageResult,
    intent: str,
    well_coordinates: list[dict] | None = None,
) -> AssembledContext:
    """Merge all retrieved evidence into a unified context."""
    df = sql_result.to_dataframe()
    structured_summary = _format_dataframe_for_llm(df)
    stats = _compute_stats(df, intent)

    logger.debug(
        f"Context assembled: {len(df)} SQL rows, "
        f"{len(semantic_chunks)} knowledge chunks, "
        f"coverage={coverage.status}"
    )

    return AssembledContext(
        structured_summary=structured_summary,
        semantic_chunks=semantic_chunks,
        coverage=coverage,
        sql_result=sql_result,
        well_coordinates=well_coordinates or [],
        stats=stats,
    )

