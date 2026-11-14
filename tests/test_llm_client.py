"""Regression tests for grounded provider fallback and quick failure handling."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingres.generation.llm_client import LLMClient


def generation_prompt(query, stats):
    return (
        "BIS limits: Fluoride 1.5 mg/L | TDS 500 mg/L.\n"
        f"Supporting statistics:\n{json.dumps(stats)}\n\n"
        "═══ USER QUERY ═══\n"
        f"{query}\n"
    )


def test_fallback_uses_query_not_quality_words_in_system_prompt():
    client = LLMClient(provider="custom", api_key="unit-test-key", base_url="https://example.invalid/v1")
    prompt = generation_prompt("How does groundwater recharge an aquifer?", {"row_count": 0})

    answer = client._dynamic_hydro_synthesizer(prompt)

    assert "Water quality analysis" not in answer
    assert "recharge" in answer.lower()
    assert "aquifer" in answer.lower()


def test_fallback_parses_nested_quality_stats_and_correct_row_count():
    client = LLMClient(provider="custom", api_key="unit-test-key", base_url="https://example.invalid/v1")
    prompt = generation_prompt(
        "Summarize groundwater quality in Bihar.",
        {
            "row_count": 500,
            "fluoride_mg_l_mean": 1.75,
            "tds_mg_l_mean": 612.4,
            "bis_violations": {"fluoride_>1.5": 12, "tds_>500": 31},
        },
    )

    answer = client._dynamic_hydro_synthesizer(prompt)

    assert "500 sampled station records" in answer
    assert "1.75 mg/L" in answer
    assert "612.4 mg/L" in answer
    assert "fluoride_>1.5: 12 records" in answer


def test_fallback_extracts_query_from_compact_generation_prompt():
    client = LLMClient(provider="custom", api_key="unit-test-key", base_url="https://example.invalid/v1")
    prompt = (
        "Summary statistics (JSON): {\"row_count\": 500, \"bis_violations\": {\"tds\": 3}}\n"
        "User question: Summarize groundwater quality in Bihar.\n"
    )

    answer = client._dynamic_hydro_synthesizer(prompt)

    assert "500 sampled station records" in answer
    assert "3 records" in answer


def test_offline_router_classifies_aquifer_questions_as_conceptual():
    client = LLMClient(provider="custom", api_key="unit-test-key", base_url="https://example.invalid/v1")

    routed = json.loads(client._synthesize_route('classify query: "What is an aquifer?"'))

    assert routed["intent"] == "SEMANTIC_CONCEPTUAL"


def test_offline_router_ignores_other_intent_names_in_router_prompt():
    client = LLMClient(provider="custom", api_key="unit-test-key", base_url="https://example.invalid/v1")
    prompt = '''Classify the query into one intent: STRUCTURED_QUALITY (fluoride, arsenic, TDS),
    SEMANTIC_CONCEPTUAL (why, how), STRUCTURED_LEVEL. User query: "Summarize groundwater quality in Bihar."'''

    routed = json.loads(client._synthesize_route(prompt.lower()))

    assert routed["intent"] == "STRUCTURED_QUALITY"


def test_provider_failure_falls_back_after_one_bounded_attempt():
    client = LLMClient(provider="custom", api_key="unit-test-key", base_url="https://example.invalid/v1")
    with patch("ingres.generation.llm_client.requests.post", side_effect=requests.Timeout("test timeout")) as post:
        answer = client.generate("A short test prompt")

    assert post.call_count == 1
    assert client.provider_requests == {"attempted": 1, "succeeded": 0, "failed": 1}
    assert "processed your inquiry" in answer


def test_custom_url_accepts_full_chat_completions_endpoint():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "TEST_OK"}}]}

    client = LLMClient(
        provider="custom",
        api_key="unit-test-key",
        base_url="https://integrate.api.nvidia.com/v1/chat/completions",
        model="mistralai/mistral-large-4-1t-a52b",
    )
    with patch("ingres.generation.llm_client.requests.post", return_value=Response()) as post:
        answer = client.generate("A short test prompt")

    assert answer == "TEST_OK"
    assert post.call_args.args[0] == "https://integrate.api.nvidia.com/v1/chat/completions"


def _response(content, usage=None):
    class Response:
        status_code = 200
        text = ""

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": content}}], "usage": usage or {}}

    return Response()


def test_openrouter_switches_off_hidden_reasoning():
    client = LLMClient(provider="openrouter", api_key="unit-test-key",
                       base_url="https://openrouter.ai/api/v1", model="openrouter/free")
    with patch("ingres.generation.llm_client.requests.post",
               return_value=_response("**Summary**: ok\n**Answer**: ok")) as post:
        client.generate("A short test prompt")

    payload = post.call_args.kwargs["json"]
    assert payload["reasoning"] == {"enabled": False}


def test_custom_endpoint_switches_off_thinking_template():
    client = LLMClient(provider="custom", api_key="unit-test-key",
                       base_url="https://example.invalid/v1")
    with patch("ingres.generation.llm_client.requests.post",
               return_value=_response("**Answer**: ok")) as post:
        client.generate("A short test prompt")

    payload = post.call_args.kwargs["json"]
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}


def test_empty_reasoning_only_completion_is_retried_with_larger_budget():
    client = LLMClient(provider="openrouter", api_key="unit-test-key",
                       base_url="https://openrouter.ai/api/v1", model="openrouter/free")
    empty = _response("", {"completion_tokens_details": {"reasoning_tokens": 900}})
    filled = _response("**Summary**: ok\n**Answer**: grounded", {"completion_tokens_details": {"reasoning_tokens": 100}})

    with patch("ingres.generation.llm_client.requests.post", side_effect=[empty, filled]) as post:
        answer = client.generate("A short test prompt", max_tokens=900)

    assert answer == "**Summary**: ok\n**Answer**: grounded"
    assert post.call_count == 2
    assert post.call_args_list[1].kwargs["json"]["max_tokens"] == 2700

