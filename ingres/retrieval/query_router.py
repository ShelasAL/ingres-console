"""
Query Router: classifies user queries into retrieval intents.
Uses Gemini for classification with a fallback keyword-heuristic.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal, Optional

from loguru import logger

Intent = Literal[
    "STRUCTURED_LEVEL",       # water depth / level measurements
    "STRUCTURED_QUALITY",     # chemical quality / potability
    "STRUCTURED_ASSESSMENT",  # extraction stage, recharge, category
    "SEMANTIC_CONCEPTUAL",    # mechanism / explanation questions
    "AMBIGUOUS_LOCATION",     # location cannot be resolved uniquely
    "TEMPORAL_OUT_OF_RANGE",  # before 2000 or future
    "UNSUPPORTED",            # completely outside system scope
]

# India state + district name list for heuristic matching
KNOWN_LOCATIONS: set[str] = {
    "rajasthan", "jaipur", "bikaner", "jodhpur", "nagaur", "barmer",
    "maharashtra", "pune", "nashik", "aurangabad", "osmanabad", "latur",
    "gujarat", "ahmedabad", "mehsana", "banaskantha", "surat", "anand",
    "punjab", "ludhiana", "amritsar", "patiala", "sangrur", "bathinda",
    "uttar pradesh", "up", "lucknow", "agra", "varanasi", "allahabad", "meerut",
    "bihar", "patna", "gaya", "bhagalpur", "muzaffarpur", "nalanda",
    "andhra pradesh", "ap", "guntur", "nalgonda", "prakasam", "kurnool", "krishna",
    "tamil nadu", "tn", "chennai", "madurai", "coimbatore", "salem", "trichy",
    "karnataka", "bengaluru", "bangalore", "tumkur", "kolar", "mysuru", "dharwad",
    "telangana", "ts", "hyderabad", "warangal", "karimnagar", "khammam", "medak",
}

QUALITY_KEYWORDS = {"fluoride", "arsenic", "nitrate", "tds", "ph", "hardness",
                    "potable", "potability", "quality", "chemical", "iron", "salinity"}
LEVEL_KEYWORDS   = {"level", "depth", "water table", "mbgl", "water level", "trend",
                    "rising", "falling", "decline", "drop", "shallow", "deep"}
ASSESS_KEYWORDS  = {"recharge", "extraction", "stage", "over.exploit", "critical",
                    "safe", "semi.critical", "gec", "assessment", "mcm"}
CONCEPT_KEYWORDS = {"why", "how", "explain", "cause", "mechanism", "effect",
                    "reason", "process", "aquifer type", "confin"}


@dataclass
class RouteResult:
    intent: Intent
    entities: dict = field(default_factory=dict)
    confidence: float = 1.0
    reasoning: str = ""


def _keyword_route(query: str) -> RouteResult:
    """Fast heuristic fallback when LLM is unavailable."""
    q = query.lower()

    # Temporal check
    years = re.findall(r"\b(19\d{2}|200[0-9]|201[0-9])\b", q)
    if any(int(y) < 2000 for y in years):
        return RouteResult("TEMPORAL_OUT_OF_RANGE",
                           entities={"years": years},
                           reasoning="Year before 2000 detected")

    # Ambiguous spatial
    loc_found = [l for l in KNOWN_LOCATIONS if l in q]
    vague = any(p in q for p in ["north india", "south india", "east india",
                                  "west india", "near river", "somewhere"])
    if vague and not loc_found:
        return RouteResult("AMBIGUOUS_LOCATION",
                           reasoning="Vague geographic reference with no known location")

    # Intent by keyword
    if any(kw in q for kw in QUALITY_KEYWORDS):
        return RouteResult("STRUCTURED_QUALITY",
                           entities={"locations": loc_found},
                           reasoning="Quality keyword detected")
    if any(kw in q for kw in ASSESS_KEYWORDS):
        return RouteResult("STRUCTURED_ASSESSMENT",
                           entities={"locations": loc_found},
                           reasoning="Assessment keyword detected")
    if any(kw in q for kw in CONCEPT_KEYWORDS):
        return RouteResult("SEMANTIC_CONCEPTUAL",
                           reasoning="Conceptual keyword detected")
    if any(kw in q for kw in LEVEL_KEYWORDS):
        return RouteResult("STRUCTURED_LEVEL",
                           entities={"locations": loc_found},
                           reasoning="Level keyword detected")

    # Default: try structured level
    if loc_found:
        return RouteResult("STRUCTURED_LEVEL",
                           entities={"locations": loc_found},
                           confidence=0.6,
                           reasoning="Location found, defaulting to level query")

    return RouteResult("UNSUPPORTED",
                       confidence=0.5,
                       reasoning="No recognizable intent or location")


def route_query(query: str, llm_client=None) -> RouteResult:
    """
    Route a user query to an intent.
    Uses LLM if available and online, falls back to keyword heuristic.
    """
    if llm_client is None or not getattr(llm_client, "is_online", True):
        logger.debug("LLM client not online; using keyword heuristic router")
        return _keyword_route(query)

    ROUTER_PROMPT = f"""
You are a query classifier for an India groundwater database system.
Classify the user query into exactly ONE of these intents:

STRUCTURED_LEVEL      - Water depth/level measurements (mbgl, water table, trend)
STRUCTURED_QUALITY    - Chemical parameters (fluoride, arsenic, TDS, pH, potability)
STRUCTURED_ASSESSMENT - Extraction stage, recharge, GEC category (safe/critical/over-exploited)
SEMANTIC_CONCEPTUAL   - Mechanism/explanation questions (why, how, cause)
AMBIGUOUS_LOCATION    - Location cannot be resolved to a specific known district/state
TEMPORAL_OUT_OF_RANGE - Year before 2000 or beyond 2025
UNSUPPORTED           - Completely outside India groundwater scope

Known locations include Indian states and districts.

User query: "{query}"

Return ONLY valid JSON:
{{
  "intent": "<one of the intents above>",
  "entities": {{
    "locations": ["<district or state names found>"],
    "parameter": "<specific parameter if any>",
    "time_range": "<year or range if mentioned>"
  }},
  "confidence": <0.0 to 1.0>,
  "reasoning": "<one sentence>"
}}
"""
    try:
        response_text = llm_client.generate(ROUTER_PROMPT, temperature=0.0, max_tokens=300, timeout=25)
        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?|```", "", response_text).strip()
        data = json.loads(clean)
        return RouteResult(
            intent=data.get("intent", "UNSUPPORTED"),
            entities=data.get("entities", {}),
            confidence=float(data.get("confidence", 0.8)),
            reasoning=data.get("reasoning", ""),
        )
    except Exception as e:
        logger.warning(f"LLM router failed ({e}); falling back to keyword heuristic")
        return _keyword_route(query)

