"""Preparation must use the same provider transport as reports and extraction."""

import json
from types import SimpleNamespace

import pytest

from app.services.oasis_profile_generator import OasisProfileGenerator
from app.services.simulation_config_generator import SimulationConfigGenerator


@pytest.mark.parametrize("generator_kind", ["profile", "simulation_config"])
@pytest.mark.parametrize("json_format", ["plain", "fenced", "truncated"])
def test_preparation_uses_minimax_messages(monkeypatch, generator_kind, json_format):
    calls = []
    result_data = {"bio": "Source-backed bio", "persona": "Source-backed persona"}
    content = json.dumps(result_data)
    if json_format == "fenced":
        content = "```json\n" + content + "\n```"
    elif json_format == "truncated":
        content = content[:-1]

    def fake_post(url, headers, json, timeout):
        calls.append((url, json))
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"content": [{"type": "text", "text": content}]},
        )

    def wrong_transport(**kwargs):
        raise AssertionError("Preparation sent MiniMax to OpenAI chat/completions")

    fake_openai = lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=wrong_transport))
    )
    for module in (
        "app.services.oasis_profile_generator",
        "app.services.simulation_config_generator",
        "app.utils.llm_client",
    ):
        monkeypatch.setattr(f"{module}.OpenAI", fake_openai, raising=False)
    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    kwargs = dict(api_key="test-key", base_url="https://api.minimax.io/anthropic", model_name="MiniMax-M3")
    if generator_kind == "profile":
        generator = OasisProfileGenerator(**kwargs)
        result = generator._generate_profile_with_llm("Alice", "Person", "Source", {}, "Context")
    else:
        generator = SimulationConfigGenerator(**kwargs)
        result = generator._call_llm_with_retry("Return a JSON object.", "Return JSON only.")

    assert result["bio"] == result_data["bio"]
    # Profile generation appends its forecast directives to the generated text.
    assert result["persona"].startswith(result_data["persona"])
    assert len(calls) == 1
    assert calls[0][0] == "https://api.minimax.io/anthropic/v1/messages"
    assert calls[0][1]["model"] == "MiniMax-M3"
