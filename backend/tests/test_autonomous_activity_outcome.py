import json
from types import SimpleNamespace
import pytest
from app.services.simulation_activity import summarize_activity
from app.models.case import normalize_prediction_settings


def action(kind='CREATE_POST', **changes):
    return dict({'agent_id':0,'round_num':1,'action_type':kind,'origin':'model_action',
                 'trace_id':kind,'success':True,'action_args':{'content':'My response'}}, **changes)


def test_setup_idle_failure_and_unknown_never_establish_discussion():
    rows = [action(origin='initial_post', round_num=0), action(origin='scheduled_event'),
            action('DO_NOTHING'), action('IDLE'), action('CREATE_COMMENT',success=False)]
    result = summarize_activity(rows)
    assert result['activity_outcome'] == 'no_autonomous_activity'
    assert result['autonomous_actions'] == result['autonomous_written_responses'] == 0
    assert summarize_activity([action('LIKE_POST')])['activity_outcome'] == 'actions_only'
    for row in [action(success=None),action(origin='unknown')]:
        assert summarize_activity([row])['activity_outcome'] == 'unverified'


def test_written_response_requires_runtime_success_and_authored_text():
    rows = [action('CREATE_COMMENT',trace_id=1),
            action('QUOTE_POST',trace_id=2,action_args={'quote_content':'My view','original_content':'Old post'}),
            action(trace_id=3,action_args={'content':'  '}),
            action('QUOTE_POST',trace_id=4,action_args={'original_content':'Old post'}),
            action(trace_id=5,round_num=0),action(trace_id=6,agent_id=-1)]
    result = summarize_activity(rows + [dict(rows[0])])
    assert result['activity_outcome'] == 'responses_recorded'
    assert result['autonomous_written_responses'] == 2
    assert result['autonomous_actions'] == 4


def test_outcome_survives_reload_without_rewriting_runner_lifecycle(tmp_path, monkeypatch):
    from flask import Flask
    from app.api import simulation_bp
    from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
    path=tmp_path/'sim_empty'/'twitter'/'actions.jsonl';path.parent.mkdir(parents=True)
    path.write_text(json.dumps(action(origin='initial_post',round_num=0))+'\n');before=path.read_bytes()
    monkeypatch.setattr(SimulationRunner,'RUN_STATE_DIR',str(tmp_path))
    state=SimulationRunState(simulation_id='sim_empty',runner_status=RunnerStatus.COMPLETED)
    monkeypatch.setattr(SimulationRunner,'get_run_state',lambda _:state)
    app=Flask(__name__);app.register_blueprint(simulation_bp,url_prefix='/api/simulation')
    for status in (RunnerStatus.COMPLETED,RunnerStatus.STOPPED,RunnerStatus.RUNNING):
        state.runner_status=status
        data=app.test_client().get('/api/simulation/sim_empty/run-status').json['data']
        assert data['runner_status']==status.value
        assert data['activity_summary']['activity_outcome']=='no_autonomous_activity'
        assert data['platform_activity']['twitter']['autonomous_actions']==0
    assert path.read_bytes()==before


def test_smoke_activation_rotates_at_a_hard_cap_without_randomness(monkeypatch):
    from scripts import forecast_runtime
    def unexpected(*args):raise AssertionError('Smoke scheduling drew randomness')
    monkeypatch.setattr(forecast_runtime.random,'uniform',unexpected)
    monkeypatch.setattr(forecast_runtime.random,'random',unexpected)
    env=SimpleNamespace(agent_graph=SimpleNamespace(get_agent=lambda n:f'agent-{n}'))
    config={'prediction_settings':{'activation_mode':'smoke_round_robin'},'time_config':{'agents_per_hour_max':2},
            'agent_configs':[{'agent_id':i,'active_hours':[],'activity_level':0} for i in [3,1,2,0,0]]}
    for round_num,expected in [(0,[0,1]),(1,[2,3]),(2,[0,1])]:
        assert [i for i,_ in forecast_runtime.select_active_agents_for_round(env,config,0,round_num)]==expected
    config['time_config']['agents_per_hour_max']=20
    assert len(forecast_runtime.select_active_agents_for_round(env,config,0,1))==4
    config['agent_configs']=[]
    assert forecast_runtime.select_active_agents_for_round(env,config,0,1)==[]


def test_normal_activation_remains_stochastic_and_mode_validation_is_explicit():
    from scripts import forecast_runtime
    env=SimpleNamespace(agent_graph=SimpleNamespace(get_agent=lambda n:n))
    assert forecast_runtime.select_active_agents_for_round(env,{'agent_configs':[{'agent_id':0,'active_hours':[]}]},0,1)==[]
    assert normalize_prediction_settings({})['activation_mode']=='stochastic'
    assert normalize_prediction_settings({'activation_mode':'smoke_round_robin'})['activation_mode']=='smoke_round_robin'
    with pytest.raises(ValueError,match='unsupported_activation_mode'):
        normalize_prediction_settings({'activation_mode':'always_on'})


def test_actual_action_logger_and_frozen_smoke_report_preserve_evidence(tmp_path, monkeypatch):
    from scripts.action_logger import PlatformActionLogger
    from app.services.simulation_activity import read_activity
    from app.services.report_grounding import build_report_grounding, provenance_issues
    from app.services.report_agent import ReportAgent, Report, ReportManager, ReportStatus
    logger=PlatformActionLogger(platform='twitter',base_dir=str(tmp_path))
    logger.log_action(1,0,'Maya','CREATE_COMMENT',{'content':'Actual logged reply'},origin='model_action',trace_id=10)
    assert summarize_activity(read_activity(tmp_path))['autonomous_written_responses']==1
    packet=build_report_grounding(None,{'prediction_settings':{'activation_mode':'smoke_round_robin'}},'graph',str(tmp_path))
    assert packet['simulation_activity']['summary']['activation_mode']=='smoke_round_robin'
    assert 'deterministic_smoke_activation_not_realistic_activity' in packet['limitations']
    agent=object.__new__(ReportAgent);agent._load_source_grounding=lambda:packet;agent.evidence_only=True
    report=Report(report_id='report_smoke',simulation_id='sim_smoke',graph_id='graph',simulation_requirement='test',status=ReportStatus.NEEDS_REVIEW,markdown_content='Report content',evidence_only=True)
    agent._apply_forecast_synthesis(report,None);agent._apply_forecast_synthesis(report,None)
    assert report.markdown_content.count('**Deterministic smoke test:**')==1
    assert not any(issue.get('code') == 'unverified_quotation' for issue in provenance_issues(report.markdown_content, packet, report.forecast))
    monkeypatch.setattr(ReportManager,'REPORTS_DIR',str(tmp_path/'reports'))
    ReportManager.save_report(report)
    restored=ReportManager.get_report(report.report_id)
    assert restored.source_grounding['simulation_activity']['summary']['activation_mode']=='smoke_round_robin'
    assert 'not a realistic activity' in restored.markdown_content
    assert (tmp_path/'reports'/report.report_id/'full_report.md').read_text()==restored.markdown_content
