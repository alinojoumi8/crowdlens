import json

from app.config import Config
from app.services.forecasting import ForecastSynthesizer


def records():
    def row(post, origin, agent=0, round_num=1):
        return {'round': round_num, 'agent_id': agent, 'agent_name': 'Maya',
                'action_type': 'CREATE_POST', 'action_args': {'post_id': post, 'content': 'I support a protected pilot.'},
                'origin': origin, 'success': True, 'timestamp': '2026-10-03T10:00:00'}
    return [row(1, 'initial_post', round_num=0), row(1, 'initial_post'),
            row(2, 'scheduled_event'), row(2, 'scheduled_event'),
            {'agent_id': -1, 'action_type': 'SCHEDULED_EVENT', 'origin': 'scheduled_event'},
            row(3, 'model_action'),
            {'agent_id': 1, 'action_type': 'DO_NOTHING', 'origin': 'model_action', 'action_args': {}}]


def test_seeded_scheduled_duplicate_and_idle_actions_do_not_drive_forecast(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, 'OASIS_SIMULATION_DATA_DIR', str(tmp_path))
    path = tmp_path / 'sim_activity' / 'twitter' / 'actions.jsonl'
    path.parent.mkdir(parents=True)
    path.write_text('\n'.join(json.dumps(r) for r in records()) + '\n')
    synth = ForecastSynthesizer('sim_activity', {'agent_configs': [{'agent_id': 0, 'stance': 'supportive'}]})
    signal = synth.build_simulation_signal()
    assert signal['total_actions'] == 1
    assert signal['active_agents'] == 1


def test_activity_counts_describe_different_kinds_of_records():
    from app.services.simulation_activity import summarize_activity
    summary = summarize_activity(records())
    assert summary['logged_entries'] == 7
    assert summary['unique_posts'] == 3
    assert summary['model_actions'] == 2
    assert summary['initial_posts'] == 1
    assert summary['scheduled_posts'] == 1
    assert summary['scheduled_events'] == 1
    assert summary['unknown_origin_actions'] == 0


def test_legacy_unknown_origins_are_not_labelled_as_model_actions():
    from app.services.simulation_activity import summarize_activity
    legacy = {k: v for k, v in records()[5].items() if k != 'origin'}
    summary = summarize_activity([legacy, dict(legacy)])
    assert summary['unique_posts'] == 1
    assert summary['model_actions'] == 0
    assert summary['unknown_origin_actions'] == 1


def test_basic_status_keeps_activity_accounting_at_terminal_boundary(tmp_path, monkeypatch):
    from flask import Flask
    from app.api import simulation_bp
    from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
    path = tmp_path / 'sim_activity' / 'twitter' / 'actions.jsonl'
    path.parent.mkdir(parents=True)
    path.write_text('\n'.join(json.dumps(r) for r in records()) + '\n')
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    state = SimulationRunState(simulation_id='sim_activity', runner_status=RunnerStatus.COMPLETED)
    monkeypatch.setattr(SimulationRunner, 'get_run_state', lambda identifier: state)
    app = Flask(__name__)
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    data = app.test_client().get('/api/simulation/sim_activity/run-status').get_json()['data']
    assert data['runner_status'] == 'completed'
    assert data['activity_summary']['model_actions'] == 2
    assert data['platform_activity']['twitter']['unique_posts'] == 3


def test_effective_activation_alias_follows_explicit_round_control():
    from app.models.case import normalize_prediction_settings
    settings = normalize_prediction_settings({'active_agents_per_round': 1, 'active_agents_per_hour': 16})
    assert settings['active_agents_per_round'] == settings['active_agents_per_hour'] == 1


def test_written_reactions_noops_and_failures_are_not_interchangeable():
    from app.services.simulation_activity import summarize_activity
    def model(kind, trace, success=True):
        return {'agent_id': 0, 'action_type': kind, 'origin': 'model_action', 'trace_id': trace, 'success': success}
    rows = [model('CREATE_POST', 1), model('CREATE_COMMENT', 2), model('LIKE_POST', 3),
            model('DO_NOTHING', 4), model('CREATE_COMMENT', 5, False)]
    summary = summarize_activity(rows + [dict(rows[0])])
    assert summary['logged_entries'] == 6
    assert summary['model_actions'] == 5
    assert summary['model_written_actions'] == 2
    assert summary['model_reactions'] == 1
    assert summary['model_noops'] == summary['model_failed_actions'] == 1
