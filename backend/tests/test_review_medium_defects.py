"""Medium defects from the 2026-11-15 review of main."""
import os
import re

import pytest

from evidence_draft_samples import sample_report
from app.services.report_agent import ReportAgent, ReportManager


@pytest.fixture
def saved_report(tmp_path, monkeypatch):
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    report = sample_report()
    ReportManager.save_report(report)
    for index, section in enumerate(report.outline.sections, 1):
        ReportManager.save_section(report.report_id, index, section)
    ReportManager.save_outline(report.report_id, report.outline)
    report.markdown_content = ReportManager.assemble_full_report(report.report_id, report.outline)
    ReportManager.save_report(report)
    return report


def report_files(report_id):
    folder = os.path.dirname(ReportManager._get_outline_path(report_id))
    return {name: open(os.path.join(folder, name), 'rb').read() for name in sorted(os.listdir(folder))
            if name.endswith(('.md', '.json')) and name not in {'progress.json'} and not name.startswith('agent_log')}


def rewrite_agent(monkeypatch, text='An unchecked new claim.', blocking=True):
    agent = ReportAgent.__new__(ReportAgent)
    agent.disable_interviews = agent.strict_antirepetition = False
    agent.report_logger = agent.console_logger = None
    agent._bind_report_contract = lambda report: None
    agent._define_tools = lambda: {}
    def write(section, **kwargs):
        section.evidence_cards = [{'claim': 'replacement evidence'}]  # the real writer replaces these
        return text
    agent._generate_section_react = write
    agent._apply_forecast_synthesis = lambda report, outline: None
    agent._check_report_claims = lambda report: None
    monkeypatch.setattr(ReportManager, 'validate_report_output', staticmethod(
        lambda report: [{'blocking': True, 'message': 'Quotation is not an exact source span.'}] if blocking else []))
    return agent


def test_failed_section_rewrite_leaves_the_saved_report_unchanged(saved_report, monkeypatch):
    before = report_files(saved_report.report_id)
    report = ReportManager.get_report(saved_report.report_id)
    agent = rewrite_agent(monkeypatch)

    with pytest.raises(ValueError, match='validation failed'):
        agent.regenerate_section(report, 1)

    after = report_files(saved_report.report_id)
    assert {name: after.get(name) for name in before} == before
    assert b'An unchecked new claim.' not in b''.join(after.values())
    # The caller's object is restored too, so a retry cannot save the rejected text.
    assert report.outline.sections[0].content == 'The hearing is Thursday.'
    assert report.outline.sections[0].evidence_cards == []
    assert 'An unchecked new claim.' not in (report.markdown_content or '')


def test_stop_during_a_section_rewrite_also_restores_the_files(saved_report, monkeypatch):
    from app.services.workflow_execution import WorkflowHalt
    before = report_files(saved_report.report_id)
    agent = rewrite_agent(monkeypatch)
    def halt(report, outline):
        raise WorkflowHalt('stopped')
    agent._apply_forecast_synthesis = halt

    with pytest.raises(WorkflowHalt):
        agent.regenerate_section(ReportManager.get_report(saved_report.report_id), 1)

    after = report_files(saved_report.report_id)
    assert {name: after.get(name) for name in before} == before


def test_metadata_is_restored_when_a_write_fails_before_the_rewrite_is_saved(saved_report, monkeypatch):
    before = report_files(saved_report.report_id)
    agent = rewrite_agent(monkeypatch, text='A checked new statement.', blocking=False)
    monkeypatch.setattr(ReportManager, 'evaluate_report_quality', staticmethod(lambda report: {}))
    monkeypatch.setattr(ReportManager, 'apply_quality_status', staticmethod(lambda report: None))
    original = ReportManager.save_report
    calls = []
    def save_report(report):
        calls.append(1)
        original(report)  # meta.json is written ...
        if len(calls) == 2:
            raise OSError('disk full')  # ... then a later artifact write fails
    monkeypatch.setattr(ReportManager, 'save_report', staticmethod(save_report))

    with pytest.raises(OSError):
        agent.regenerate_section(ReportManager.get_report(saved_report.report_id), 1)

    assert report_files(saved_report.report_id)['meta.json'] == before['meta.json']


def test_restore_runs_as_a_trusted_repair_after_stop(saved_report, monkeypatch):
    from app.services import quota_io
    from app.services.workflow_execution import WorkflowHalt
    before = report_files(saved_report.report_id)
    agent = rewrite_agent(monkeypatch)
    stopped = []
    def halt(report, outline):
        stopped.append(1)
        raise WorkflowHalt('stopped')
    agent._apply_forecast_synthesis = halt
    original = quota_io.write_text
    def write_text(path, content):
        # After Stop, a normal write is refused; only a trusted repair may write.
        if stopped and not quota_io._REMEDIATION.get():
            raise WorkflowHalt('quota_storage_write_bytes_limit')
        return original(path, content)
    monkeypatch.setattr('app.services.report_agent.write_text', write_text)

    with pytest.raises(WorkflowHalt, match='stopped'):
        agent.regenerate_section(ReportManager.get_report(saved_report.report_id), 1)

    after = report_files(saved_report.report_id)
    assert {name: after.get(name) for name in before} == before


def test_a_file_that_cannot_be_restored_is_removed_not_left_rejected(saved_report, monkeypatch):
    from app.services import quota_io
    agent = rewrite_agent(monkeypatch)
    full_report = ReportManager._get_report_markdown_path(saved_report.report_id)
    rewriting = []
    def write(section, **kwargs):
        rewriting.append(1)
        return 'An unchecked new claim.'
    agent._generate_section_react = write
    original = quota_io.write_text
    def write_text(path, content):
        if rewriting and path == full_report and 'An unchecked' not in content:
            raise OSError('disk full')  # the restore of the old full report fails
        return original(path, content)
    monkeypatch.setattr('app.services.report_agent.write_text', write_text)

    with pytest.raises(ValueError, match='validation failed'):
        agent.regenerate_section(ReportManager.get_report(saved_report.report_id), 1)

    assert not os.path.exists(full_report)


def test_a_saved_rewrite_is_kept_if_only_the_last_progress_update_fails(saved_report, monkeypatch):
    agent = rewrite_agent(monkeypatch, text='A checked new statement.', blocking=False)
    monkeypatch.setattr(ReportManager, 'evaluate_report_quality', staticmethod(lambda report: {}))
    monkeypatch.setattr(ReportManager, 'apply_quality_status', staticmethod(lambda report: None))
    original = ReportManager.update_progress
    def update_progress(report_id, status, progress, message, **kwargs):
        if progress == 100:
            raise OSError('disk full')
        return original(report_id, status, progress, message, **kwargs)
    monkeypatch.setattr(ReportManager, 'update_progress', staticmethod(update_progress))

    with pytest.raises(OSError):
        agent.regenerate_section(ReportManager.get_report(saved_report.report_id), 1)

    files = report_files(saved_report.report_id)
    saved = ReportManager.get_report(saved_report.report_id)
    # meta.json and the files agree on the new, validated text.
    assert b'A checked new statement.' in files['section_01.md']
    assert 'A checked new statement.' in saved.markdown_content


def test_request_slots_left_by_a_crashed_process_are_freed_at_startup(tmp_path):
    import subprocess
    import sys
    from flask import Flask
    from app.api.execution import install_workflow_controls
    from app.services import administrator_quotas as quotas
    from app.services.workflow_execution import WorkflowLedger
    from app.storage.control_db import ControlDatabase
    ended = subprocess.Popen([sys.executable, '-c', 'pass'])
    ended_owner = quotas._owner(ended.pid)
    ended.wait()
    live_owner = quotas._owner()
    assert ended_owner and live_owner
    repository = ControlDatabase(tmp_path / 'control.sqlite')
    with WorkflowLedger(repository.path).transaction() as db:
        for identifier, active in [(f'op_{ended_owner}_a', 1),   # killed mid-request: teardown never ran
                                   (f'op_{live_owner}_b', 1),    # still running in a live worker
                                   ('op_legacyformat', 1),       # written by older code
                                   (f'op_{ended_owner}_c', 0)]:  # finished normally
            db.execute('INSERT INTO quota_operations VALUES(?, ?, 1.0, ?)', (identifier, 'workspace_a', active))

    app = Flask(__name__)
    app.extensions['control_db'] = repository
    install_workflow_controls(app)

    with WorkflowLedger(repository.path).transaction() as db:
        rows = dict(db.execute('SELECT id, active FROM quota_operations').fetchall())
    # Only the live request keeps its slot; every operation stays counted.
    assert rows == {f'op_{ended_owner}_a': 0, f'op_{live_owner}_b': 1, 'op_legacyformat': 0,
                    f'op_{ended_owner}_c': 0}


def test_new_slots_name_their_owning_process(tmp_path, monkeypatch):
    import uuid
    from app.services import administrator_quotas as quotas
    from app.services.workflow_execution import WorkflowLedger
    from app.storage.control_db import ControlDatabase
    monkeypatch.setattr(quotas, 'check', lambda *args, **kwargs: True)
    monkeypatch.setattr(quotas.uuid, 'uuid4', lambda: uuid.UUID(int=7))
    with WorkflowLedger(ControlDatabase(tmp_path / 'control.sqlite').path).transaction() as db:
        identifier = quotas.begin_operation(db, 'workspace_a', 1.0)
        assert identifier == f'op_{quotas._owner()}_{uuid.UUID(int=7).hex}'
        assert quotas.reclaim_abandoned_operations(db) == 0
