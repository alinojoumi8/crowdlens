"""Bounded retries retain batch identity and never pretend lost work succeeded."""
from types import SimpleNamespace

import pytest
from neo4j.exceptions import ServiceUnavailable

from app.services.graph_memory_updater import AgentActivity, GraphMemoryUpdater
from app.services.workflow_execution import WorkflowHalt


def activity():
    return AgentActivity('twitter', 1, 'Fictional speaker', 'CREATE_POST',
        {'content': 'Fictional action retained on disk'}, 1, '2026-10-11T00:00:00')


def test_later_stage_outage_reuses_memory_identity_for_every_retry(monkeypatch):
    records = []
    attempts = []
    def add_text(*args):
        attempts.append(args)
        if len(attempts) < 3:
            raise ServiceUnavailable('synthetic later-stage outage')
    storage = SimpleNamespace(add_agent_memories=lambda graph, batch: records.append(batch), add_text=add_text)
    updater = GraphMemoryUpdater('graph_fixture', storage)
    monkeypatch.setattr(updater, 'RETRY_DELAY', 0)
    updater._send_batch_activities([activity()], 'twitter')
    assert len(records) == 3
    ids = [batch[0].get('memory_id') for batch in records]
    assert all(ids) and len(set(ids)) == 1
    assert updater.get_stats()['items_sent'] == 1
    assert updater.get_stats()['failed_count'] == 0


def test_exhausted_outage_keeps_partial_files_and_reports_failure(tmp_path, monkeypatch):
    log = tmp_path / 'actions.jsonl'
    log.write_bytes(b'{"round":1,"content":"Retained partial action"}\n')
    report = tmp_path / 'section_1.md'; report.write_text('Retained partial report')
    before = {p: p.read_bytes() for p in (log, report)}
    calls = []
    def unavailable(*args):
        calls.append(args)
        raise ServiceUnavailable('synthetic unavailable graph')
    def forbidden(*args):
        pytest.fail('No later extraction or generation after failed memory write')
    updater = GraphMemoryUpdater('graph_fixture', SimpleNamespace(add_agent_memories=unavailable, add_text=forbidden))
    monkeypatch.setattr(updater, 'RETRY_DELAY', 0)
    updater._send_batch_activities([activity()], 'twitter')
    assert len(calls) == updater.MAX_RETRIES
    assert updater.get_stats()['failed_count'] == 1
    assert updater.get_stats()['items_sent'] == 0
    assert all(path.read_bytes() == content for path, content in before.items())


def test_stop_or_exhausted_allowance_never_retries_memory_generation():
    calls = []
    def halted(*args):
        calls.append(args)
        raise WorkflowHalt('request_limit')
    updater = GraphMemoryUpdater('graph_fixture', SimpleNamespace(add_agent_memories=halted))
    with pytest.raises(WorkflowHalt):
        updater._send_batch_activities([activity()], 'twitter')
    assert len(calls) == 1
