"""
Baseline retrieval: TF-IDF keyword match over flattened CSV export.
Used for comparison against the RAG system in evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger


@dataclass
class BaselineResult:
    answer: str
    matched_rows: list[dict]
    method: str = "TF-IDF Keyword Baseline"
    score: float = 0.0


class TFIDFBaseline:
    """
    Simple baseline: flatten all DB tables to text, TF-IDF match user query,
    return top-matched rows as a text answer.
    """

    def __init__(self, con):
        self._con = con
        self._corpus: list[str] = []
        self._rows: list[dict] = []
        self._vectorizer = None
        self._matrix = None
        self._build()

    def _build(self):
        try:
            # Flatten wells + levels + quality + assessments to text rows
            df = self._con.execute("""
                SELECT w.well_id, w.district, w.state, w.well_type,
                       l.season, l.depth_to_water_mbgl, l.data_quality_flag,
                       CAST(l.measurement_date AS VARCHAR) as date
                FROM wells w
                LEFT JOIN gw_levels l ON w.well_id = l.well_id
                WHERE l.depth_to_water_mbgl IS NOT NULL
                LIMIT 2000
            """).df()

            for _, row in df.iterrows():
                text = (f"district={row['district']} state={row['state']} "
                        f"season={row['season']} depth={row['depth_to_water_mbgl']}mbgl "
                        f"date={row['date']} well_type={row['well_type']}")
                self._corpus.append(text)
                self._rows.append(row.to_dict())

            # Add quality rows
            qdf = self._con.execute("""
                SELECT w.district, w.state, q.potability,
                       q.fluoride_mg_l, q.tds_mg_l, q.arsenic_ug_l, q.ph,
                       CAST(q.sample_date AS VARCHAR) as date
                FROM wells w JOIN gw_quality q ON w.well_id=q.well_id
                LIMIT 500
            """).df()
            for _, row in qdf.iterrows():
                text = (f"district={row['district']} state={row['state']} "
                        f"potability={row['potability']} fluoride={row['fluoride_mg_l']} "
                        f"tds={row['tds_mg_l']} arsenic={row['arsenic_ug_l']} ph={row['ph']}")
                self._corpus.append(text)
                self._rows.append(row.to_dict())

            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            self._matrix = self._vectorizer.fit_transform(self._corpus)
            logger.info(f"Baseline TF-IDF index built: {len(self._corpus)} documents")
        except Exception as e:
            logger.error(f"Baseline build failed: {e}")

    def query(self, user_query: str, top_k: int = 5) -> BaselineResult:
        if self._vectorizer is None or self._matrix is None:
            return BaselineResult(
                answer="Baseline unavailable (TF-IDF not built)",
                matched_rows=[],
            )
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            q_vec = self._vectorizer.transform([user_query])
            scores = cosine_similarity(q_vec, self._matrix).flatten()
            top_idx = np.argsort(scores)[::-1][:top_k]
            matched = [self._rows[i] for i in top_idx if scores[i] > 0.05]
            if not matched:
                return BaselineResult(
                    answer="No matching records found in baseline search.",
                    matched_rows=[],
                    score=0.0,
                )
            # Build a simple text answer
            lines = [f"Top {len(matched)} matching records (keyword match):"]
            for r in matched:
                parts = [f"{k}={v}" for k, v in r.items() if v is not None and str(v) != "nan"]
                lines.append("  • " + " | ".join(parts[:6]))
            return BaselineResult(
                answer="\n".join(lines),
                matched_rows=matched,
                score=float(scores[top_idx[0]]) if len(top_idx) > 0 else 0.0,
            )
        except Exception as e:
            logger.error(f"Baseline query failed: {e}")
            return BaselineResult(answer=f"Baseline error: {e}", matched_rows=[])

