"""
Semantic vector search over hydrogeological knowledge base using ChromaDB.
Falls back to keyword search if ChromaDB is unavailable.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from loguru import logger

CHROMA_PATH = Path(__file__).resolve().parents[2] / "data" / "chroma_store"

# ── Built-in hydrogeological knowledge chunks ─────────────────────────────────
KNOWLEDGE_CHUNKS = [
    {
        "id": "gec2015_methodology",
        "text": (
            "The GEC-2015 (Ground Water Resource Estimation Committee) methodology "
            "is the standard framework used by CGWB for estimating India's groundwater "
            "resources. It calculates annual groundwater recharge and extraction at "
            "block/taluk level. The Stage of Groundwater Development (SGD) is the ratio "
            "of annual groundwater extraction to net annual groundwater availability, "
            "expressed as a percentage. Categories: Safe (<70%), Semi-Critical (70-90%), "
            "Critical (90-100%), Over-Exploited (>100%), Saline."
        ),
        "source": "CGWB GEC-2015 Report",
        "topic": "assessment methodology",
    },
    {
        "id": "fluoride_contamination",
        "text": (
            "Fluoride contamination in groundwater in India is a major concern in "
            "states like Rajasthan, Andhra Pradesh, Telangana, and Gujarat. The BIS "
            "permissible limit is 1.0 mg/L (acceptable) and 1.5 mg/L (maximum). "
            "Nalgonda district in Telangana historically has among the highest fluoride "
            "levels (up to 4-5 mg/L), causing dental and skeletal fluorosis. "
            "Fluoride originates from dissolution of fluorite minerals in granite aquifers."
        ),
        "source": "CGWB Groundwater Quality Report",
        "topic": "water quality fluoride",
    },
    {
        "id": "arsenic_contamination",
        "text": (
            "Arsenic contamination in groundwater is prevalent in the Gangetic plains, "
            "particularly in Bihar, Uttar Pradesh, and West Bengal. The BIS/WHO limit "
            "is 10 µg/L. Arsenic is released from iron-oxyhydroxide minerals under "
            "reducing conditions in shallow alluvial aquifers. Affected districts in "
            "Bihar include Patna, Bhagalpur, and Vaishali."
        ),
        "source": "CGWB Arsenic Status Report",
        "topic": "water quality arsenic",
    },
    {
        "id": "over_exploitation_rajasthan",
        "text": (
            "Rajasthan has the highest proportion of over-exploited groundwater "
            "assessment units in India. Arid districts like Bikaner, Jaisalmer, and "
            "Barmer face severe over-extraction due to agricultural irrigation using "
            "deep tubewells. The Thar Desert region has limited recharge from rainfall "
            "(100-300 mm/year) but high extraction for agriculture and domestic use."
        ),
        "source": "CGWB Dynamic Groundwater Resources of India 2022",
        "topic": "over exploitation rajasthan",
    },
    {
        "id": "aquifer_types_india",
        "text": (
            "India has diverse aquifer systems: (1) Alluvial aquifers in Indo-Gangetic "
            "plains and coastal areas - unconfined to confined, high productivity. "
            "(2) Hard rock aquifers in Deccan plateau (basalt, granite, schist) - "
            "limited groundwater storage in weathered and fractured zones. "
            "(3) Sandstone aquifers in Rajasthan and Madhya Pradesh. "
            "(4) Limestone/karst aquifers in parts of Rajasthan and Andhra Pradesh. "
            "Confined aquifers show artesian conditions (positive pressure) in select "
            "areas like Patna and parts of the Gangetic plains."
        ),
        "source": "CGWB Aquifer Mapping India",
        "topic": "aquifer types hydrogeology",
    },
    {
        "id": "monsoon_recharge",
        "text": (
            "Monsoon recharge is the primary mechanism replenishing groundwater in India. "
            "The southwest monsoon (June-September) provides 70-80% of annual rainfall. "
            "Post-monsoon water levels (measured in October-November) are typically "
            "shallower (less mbgl) than pre-monsoon levels (April-May). A declining trend "
            "in post-monsoon levels over years indicates net depletion exceeding recharge. "
            "CGWB monitoring occurs quarterly: January (rabi), April (pre-monsoon), "
            "August (kharif), and November (post-monsoon)."
        ),
        "source": "CGWB Annual Report",
        "topic": "monsoon recharge seasonal variation",
    },
    {
        "id": "bis_water_quality_standards",
        "text": (
            "BIS 10500:2012 specifies drinking water quality standards in India. "
            "Key limits: pH 6.5-8.5, TDS 500 mg/L (acceptable) / 2000 mg/L (max), "
            "Hardness 200/600 mg/L, Fluoride 1.0/1.5 mg/L, Nitrate 45 mg/L, "
            "Arsenic 0.01 mg/L (10 µg/L), Iron 0.3 mg/L. "
            "Exceedance of acceptable limits makes water 'marginal'; exceedance of "
            "maximum limits makes it 'non-potable'."
        ),
        "source": "BIS 10500:2012 Standard",
        "topic": "drinking water standards quality limits",
    },
    {
        "id": "water_table_trends_india",
        "text": (
            "Long-term water table trend analysis by CGWB (2009-2020) shows that "
            "61% of wells in India show declining trends, while 28% show rising trends. "
            "Over-exploited states like Punjab, Haryana, and parts of Rajasthan show "
            "the steepest declines (0.3-1.0 m/year). States with improved irrigation "
            "efficiency or reduced paddy area show recovery. Trend analysis requires "
            "at least 5-10 years of consistent seasonal data from 3+ wells per district."
        ),
        "source": "CGWB Water Level Trend Analysis 2022",
        "topic": "water table trend declining analysis",
    },
    {
        "id": "marathwada_drought",
        "text": (
            "Marathwada (comprising Aurangabad, Latur, Osmanabad, Nanded, Parbhani, "
            "Hingoli, Beed, and Jalna districts in Maharashtra) is a drought-prone "
            "region. Hard rock Deccan basalt aquifers have limited groundwater storage. "
            "Multiple consecutive droughts (2012, 2015, 2018) have severely depleted "
            "groundwater. Many villages in Osmanabad and Latur rely on tanker water supply."
        ),
        "source": "CGWB Maharashtra Report",
        "topic": "Marathwada drought hard rock aquifer",
    },
    {
        "id": "coastal_saline_intrusion",
        "text": (
            "Saltwater intrusion affects coastal aquifers in Tamil Nadu, Gujarat, "
            "Kerala, and Goa. Over-extraction near the coast reduces freshwater head, "
            "allowing denser saline water to migrate inland. TDS often exceeds 2000 mg/L "
            "in affected zones. CGWB designates such areas as 'Saline' in GEC assessments. "
            "Districts like Surat, South 24 Parganas, and coastal Tamil Nadu districts "
            "are affected."
        ),
        "source": "CGWB Coastal Aquifer Management",
        "topic": "saltwater intrusion coastal salinity",
    },
]


class VectorSearchEngine:
    """
    Semantic search over groundwater knowledge chunks.
    Uses ChromaDB with sentence-transformers embeddings.
    Falls back to keyword TF-IDF if ChromaDB is unavailable.
    """

    def __init__(self):
        self._chroma_available = False
        self._collection = None
        self._vectorizer = None
        self._tfidf_matrix = None
        self._tfidf_texts = [c["text"] for c in KNOWLEDGE_CHUNKS]
        self._tfidf_ids = [c["id"] for c in KNOWLEDGE_CHUNKS]
        self._load()

    def _load(self):
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            CHROMA_PATH.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self._collection = client.get_or_create_collection(
                name="ingres_knowledge",
                embedding_function=emb_fn,
                metadata={"hnsw:space": "cosine"},
            )
            # Seed if empty
            if self._collection.count() == 0:
                self._collection.add(
                    ids=[c["id"] for c in KNOWLEDGE_CHUNKS],
                    documents=[c["text"] for c in KNOWLEDGE_CHUNKS],
                    metadatas=[{"source": c["source"], "topic": c["topic"]}
                               for c in KNOWLEDGE_CHUNKS],
                )
                logger.info(f"Seeded {len(KNOWLEDGE_CHUNKS)} knowledge chunks into ChromaDB")
            self._chroma_available = True
            logger.info("ChromaDB vector store loaded successfully")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable ({e}); using TF-IDF fallback")
            self._load_tfidf()

    def _load_tfidf(self):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(stop_words="english")
            self._tfidf_matrix = self._vectorizer.fit_transform(self._tfidf_texts)
            logger.info("TF-IDF fallback vectorizer loaded")
        except Exception as e:
            logger.error(f"TF-IDF fallback also failed: {e}")

    def search(self, query: str, n_results: int = 3) -> list[dict]:
        """Return top-n relevant knowledge chunks for the query."""
        if self._chroma_available and self._collection is not None:
            return self._chroma_search(query, n_results)
        return self._tfidf_search(query, n_results)

    def _chroma_search(self, query: str, n: int) -> list[dict]:
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n, len(KNOWLEDGE_CHUNKS)),
            )
            out = []
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i]
                dist = results["distances"][0][i] if "distances" in results else 0.0
                out.append({
                    "text": doc,
                    "source": meta.get("source", "Unknown"),
                    "topic": meta.get("topic", ""),
                    "score": round(1.0 - dist, 3),
                })
            return out
        except Exception as e:
            logger.warning(f"ChromaDB search failed: {e}; using TF-IDF")
            return self._tfidf_search(query, n)

    def _tfidf_search(self, query: str, n: int) -> list[dict]:
        if self._vectorizer is None or self._tfidf_matrix is None:
            return []
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            q_vec = self._vectorizer.transform([query])
            scores = cosine_similarity(q_vec, self._tfidf_matrix).flatten()
            top_idx = np.argsort(scores)[::-1][:n]
            out = []
            for idx in top_idx:
                chunk = KNOWLEDGE_CHUNKS[idx]
                out.append({
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "topic": chunk["topic"],
                    "score": round(float(scores[idx]), 3),
                })
            return out
        except Exception as e:
            logger.error(f"TF-IDF search failed: {e}")
            return []


# Module-level singleton
_engine: Optional[VectorSearchEngine] = None


def get_search_engine() -> VectorSearchEngine:
    global _engine
    if _engine is None:
        _engine = VectorSearchEngine()
    return _engine


def semantic_search(query: str, n_results: int = 3) -> list[dict]:
    """Public API: search the knowledge base."""
    return get_search_engine().search(query, n_results)

