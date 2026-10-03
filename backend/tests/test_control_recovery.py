"""Regressions from the preserved fictional browser run; no live inference."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.simulation_manager import SimulationManager
from app.services.simulation_config_generator import SimulationConfigGenerator, SimulationParameters
from app.services.report_agent import ReportManager
from app.services.graph_memory_updater import GraphMemoryUpdater
from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
from test_simulation_manager import FakeGraphStorage
from app.models.case import normalize_prediction_settings


def test_selected_settings_reach_config_worker(tmp_path, monkeypatch):
    monkeypatch.setattr(SimulationManager, 'SIMULATION_DATA_DIR', str(tmp_path))
    monkeypatch.setattr('app.services.simulation_config_generator.Config.LLM_API_KEY', 'synthetic')
    seen = {}
    def config(self, **kwargs):
        seen.update(kwargs)
        return SimulationParameters(**{k: kwargs[k] for k in
            ('simulation_id', 'project_id', 'graph_id', 'simulation_requirement')})
    monkeypatch.setattr(SimulationConfigGenerator, 'generate_config', config)
    selected = dict(agent_count=1, profile_parallelism=1, simulation_duration=2,
                    minutes_per_round=60, active_agents_per_round=1,
                    report_mode='evidence_gap', report_depth='fast')
    manager = SimulationManager()
    state = manager.create_simulation(project_id='synthetic', graph_id='synthetic', prediction_settings=selected)
    manager.prepare_simulation(state.simulation_id, 'Fictional bike lane', 'Frozen fictional input',
        use_llm_for_profiles=False, storage=FakeGraphStorage(), prediction_settings=selected)
    for key, value in selected.items():
        assert seen.get('prediction_settings', {}).get(key) == value


@pytest.mark.parametrize('status', ['generating', 'interrupted'])
@pytest.mark.parametrize('tz', [timezone.utc, timezone(timedelta(hours=-4))])
def test_report_progress_accepts_recovery_timestamp(status, tz):
    result = ReportManager.enrich_progress(dict(status=status,
        updated_at=(datetime.now(tz) - timedelta(seconds=120)).isoformat()), stale_after_seconds=60)
    assert result['seconds_since_update'] >= 120
    assert result['is_stale'] is (status == 'generating')


def test_stop_does_not_flush_more_generation():
    updater = GraphMemoryUpdater('synthetic', SimpleNamespace())
    calls = []
    updater._flush_remaining = lambda: calls.append('scheduled after stop')
    updater.stop()
    assert calls == []


def test_monitor_preserves_explicit_stop(tmp_path, monkeypatch):
    state = SimulationRunState(simulation_id='synthetic', runner_status=RunnerStatus.STOPPED)
    process = SimpleNamespace(poll=lambda: 0, returncode=0)
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    monkeypatch.setattr(SimulationRunner, '_processes', {'synthetic': process})
    monkeypatch.setattr(SimulationRunner, '_graph_memory_enabled', {})
    monkeypatch.setattr(SimulationRunner, '_action_queues', {})
    monkeypatch.setattr(SimulationRunner, '_stdout_files', {})
    monkeypatch.setattr(SimulationRunner, '_stderr_files', {})
    monkeypatch.setattr(SimulationRunner, 'get_run_state', lambda sid: state)
    monkeypatch.setattr(SimulationRunner, '_save_run_state', lambda s: None)
    SimulationRunner._monitor_simulation('synthetic')
    assert state.runner_status == RunnerStatus.STOPPED


@pytest.mark.parametrize('invalid', [dict(platform='unknown'), dict(report_mode='unknown'),
    dict(report_depth='unknown'), dict(memory_mode='unknown'), dict(profile_parallelism=0)])
def test_unsupported_settings_are_explicitly_rejected(invalid):
    with pytest.raises(ValueError):
        normalize_prediction_settings(invalid)
