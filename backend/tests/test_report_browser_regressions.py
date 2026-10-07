"""Failures observed during the real Cedarbrook browser workflow."""
from types import SimpleNamespace

import pytest

from app.api.simulation import _get_report_id_for_simulation
from app.services.report_agent import (
    Report, ReportAgent, ReportManager, ReportOutline, ReportSection, ReportStatus,
)


@pytest.mark.parametrize("fallback", [False, True])
def test_history_finds_root_in_effective_store_even_after_new_revision(tmp_path, monkeypatch, fallback):
    configured = tmp_path / "configured"
    if fallback:
        configured.write_text("blocked directory", encoding="utf-8")
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(configured))
    monkeypatch.setattr(ReportManager, "FALLBACK_REPORTS_DIR", str(tmp_path / "fallback"))
    root = Report("report_browser_root", "sim_browser_regression", "graph", "test",
                  ReportStatus.COMPLETED, created_at="2026-10-03T12:00:00")
    child = Report("report_browser_child", root.simulation_id, "graph", "test",
                   ReportStatus.NEEDS_REVIEW, created_at="2026-10-03T12:05:00",
                   revision={"parent_report_id": root.report_id})
    ReportManager.save_report(root)
    ReportManager.save_report(child)

    assert _get_report_id_for_simulation(root.simulation_id) == root.report_id
    assert _get_report_id_for_simulation("missing_browser_simulation") is None


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("fallback", [False, True])
@pytest.mark.parametrize("bad_metadata", [
    '{', '{"report_id":"unrelated"}',
    '{"report_id":"unrelated","simulation_id":"other","graph_id":"g","simulation_requirement":"test","status":"unknown"}',
])
def test_history_skips_unrelated_unreadable_report(tmp_path, monkeypatch, bad_metadata, legacy, fallback):
    configured = tmp_path / "configured"
    if fallback:
        configured.write_text("blocked directory", encoding="utf-8")
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(configured))
    monkeypatch.setattr(ReportManager, "FALLBACK_REPORTS_DIR", str(tmp_path / "fallback"))
    root = Report("report_valid_history", "sim_valid_history", "graph", "test", ReportStatus.COMPLETED)
    ReportManager.save_report(root)
    store = ReportManager._get_reports_dir()
    from pathlib import Path
    store = Path(store)
    if legacy:
        (store / "report_bad.json").write_text(bad_metadata, encoding="utf-8")
    else:
        bad = store / "report_bad"
        bad.mkdir()
        (bad / "meta.json").write_text(bad_metadata, encoding="utf-8")

    assert _get_report_id_for_simulation(root.simulation_id) == root.report_id


def react_agent(monkeypatch, responses):
    agent = ReportAgent.__new__(ReportAgent)
    agent.report_logger = None
    agent.simulation_requirement = "Use the original fictional source."
    agent.report_depth = "fast"
    agent.MAX_TOOL_CALLS_PER_SECTION = 2
    agent.tools = {"quick_search": object()}
    agent._economy_evidence_cards = []
    agent._last_tool_evidence = []
    for name in ("_build_section_role", "_report_mode_guidance", "_get_tools_description",
                 "_build_used_evidence_ledger", "_source_grounding_prompt", "_prefetch_economy_evidence"):
        monkeypatch.setattr(agent, name, lambda *args: "")
    monkeypatch.setattr(agent, "_execute_tool", lambda *args, **kwargs: "Original source: eight-week pilot.")
    remaining = iter(responses)
    calls = []
    def chat(**kwargs):
        calls.append(kwargs)
        response = next(remaining)
        if isinstance(response, Exception):
            raise response
        return response
    agent.llm = SimpleNamespace(chat=chat)
    return agent, calls


TOOL = '<tool_call>{"name":"quick_search","parameters":{"query":"pilot"}}</tool_call>'


def test_thinking_only_answer_gets_one_bounded_continuation(monkeypatch):
    from app.utils.llm_client import EmptyLLMResponseError
    agent, calls = react_agent(monkeypatch, [TOOL, EmptyLLMResponseError("empty"), "Final Answer: Source-grounded prose."])
    section = ReportSection(title="Source facts")
    outline = ReportOutline(title="Pilot", summary="Fictional test", sections=[section])
    assert agent._generate_section_react_once(section, outline, []) == "Source-grounded prose."
    assert len(calls) == 3


def test_repeated_empty_answer_stops_without_publishing(monkeypatch):
    from app.utils.llm_client import EmptyLLMResponseError
    agent, calls = react_agent(monkeypatch, [TOOL, EmptyLLMResponseError("empty"), EmptyLLMResponseError("empty again")])
    section = ReportSection(title="Source facts")
    outline = ReportOutline(title="Pilot", summary="Fictional test", sections=[section])
    with pytest.raises(EmptyLLMResponseError):
        agent._generate_section_react_once(section, outline, [])
    assert len(calls) == 3


def test_process_note_is_not_adopted_as_completed_section(monkeypatch):
    note = "I have the source. Let me verify the simulated discussion before writing."
    agent, calls = react_agent(monkeypatch, [TOOL, note, "Final Answer: The source describes an eight-week pilot."])
    section = ReportSection(title="Source facts")
    outline = ReportOutline(title="Pilot", summary="Fictional test", sections=[section])

    result = agent._generate_section_react_once(section, outline, [])

    assert result == "The source describes an eight-week pilot."
    assert len(calls) == 3
    assert "Final Answer:" in calls[-1]["messages"][-1]["content"]


@pytest.mark.parametrize("empty", ["Final Answer:", "Final Answer: ## Source facts"])
def test_empty_final_marker_needs_completed_prose(monkeypatch, empty):
    agent, calls = react_agent(monkeypatch, [TOOL, empty, "Final Answer: Completed prose."])
    section = ReportSection(title="Source facts")
    outline = ReportOutline(title="Pilot", summary="Fictional test", sections=[section])
    assert agent._generate_section_react_once(section, outline, []) == "Completed prose."
    assert len(calls) == 3


@pytest.mark.parametrize("unfinished", [None, "", "Let me verify another source.", "Final Answer: ## Source facts"])
def test_exhausted_writer_does_not_publish_missing_final_answer(monkeypatch, unfinished):
    agent, calls = react_agent(monkeypatch, [TOOL] + ["Still checking the source."] * 4 + [unfinished])
    section = ReportSection(title="Source facts")
    outline = ReportOutline(title="Pilot", summary="Fictional test", sections=[section])

    with pytest.raises(ValueError, match="completed Final Answer"):
        agent._generate_section_react_once(section, outline, [])
    assert len(calls) == 6  # Existing bounded loop and one forced conclusion.
