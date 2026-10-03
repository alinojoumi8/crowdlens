"""Regression examples for graph quotations and conflicting probability prose."""
from copy import deepcopy

from app.services.report_agent import Report, ReportAgent, ReportManager, ReportStatus


SOURCE = 'Maya Chen supports a trial if loading access remains available.'


def report_with(text):
    return Report(report_id='report_contract', simulation_id='sim_contract', graph_id='graph_contract',
        simulation_requirement='fictional test', status=ReportStatus.COMPLETED,
        markdown_content=text, forecast={'status': 'available', 'probabilities': [
            {'outcome': 'Support', 'probability': 0.465}]},
        source_grounding={'report_contract': 'report-grounding-v1', 'status': 'available',
            'original_sources': [{'document_id': 'doc_1', 'excerpt': SOURCE}],
            'simulation_activity': {'actions': [{'reference': 'twitter:trace:3', 'origin': 'model_action',
                'action_args': {'content': 'A trial could help, provided loading access stays open.'}}]}})


def test_graph_paraphrase_cannot_pass_as_original_quote():
    report = report_with('Maya said "I support the trial if loading zones are protected." [doc_1]')
    assert any(i['code'] == 'unverified_quotation' and i['blocking'] for i in ReportManager.validate_report_output(report))


def test_section_prompt_example_obeys_the_same_quote_guard_as_output():
    from app.services.report_agent import SECTION_SYSTEM_PROMPT_TEMPLATE
    example = SECTION_SYSTEM_PROMPT_TEMPLATE.split('[Correct Example]', 1)[1].split('[Incorrect Example]', 1)[0]
    assert not any(i['code'] == 'unverified_quotation' for i in ReportManager.validate_report_output(report_with(example)))


def test_actual_blocked_cedarbrook_output_stays_blocked_after_prompt_repair():
    import json
    from pathlib import Path
    captured = json.loads((Path(__file__).parent / 'fixtures/report_grounding/cedarbrook-blocked.json').read_text())
    report = report_with(captured['markdown_content'])
    report.forecast = captured['forecast']
    report.source_grounding = captured['source_grounding']
    failures = [i for i in ReportManager.validate_report_output(report) if i['code'] == 'unverified_quotation']
    assert len(failures) == captured['expected_quote_failures']
    assert all(i['blocking'] for i in failures)


def test_exact_original_and_actual_trace_quotes_pass_with_references():
    report = report_with(f'Original packet: "{SOURCE}" [doc_1]\n\n'
        'Simulated model response: "A trial could help, provided loading access stays open." [twitter:trace:3]')
    assert not any(i.get('blocking') for i in ReportManager.validate_report_output(report))


def test_probability_prose_cannot_disagree_with_structured_forecast():
    report = report_with('The scenario has a 55% probability of support.')
    assert any(i['code'] == 'forecast_probability_mismatch' and i['blocking'] for i in ReportManager.validate_report_output(report))


def test_numerical_outcome_prose_cannot_bypass_authority_with_different_phrasing():
    report = report_with('Estimated support: 55%.')
    assert any(i['code'] == 'forecast_probability_mismatch' and i['blocking'] for i in ReportManager.validate_report_output(report))


def test_apply_forecast_uses_one_frozen_authority_not_generated_prose(monkeypatch):
    frozen = {'status': 'available', 'probabilities': [{'outcome': 'Support', 'probability': .465}]}
    agent = ReportAgent.__new__(ReportAgent)
    agent.simulation_id, agent.simulation_config, agent.report_mode = 'sim_contract', {}, 'prediction'
    agent._forecast_authority = deepcopy(frozen)
    agent._source_grounding = {'report_contract': 'report-grounding-v1', 'status': 'unavailable'}
    def forbidden(*args, **kwargs):
        raise AssertionError('Generated prose must not resynthesize the probability authority')
    monkeypatch.setattr('app.services.report_agent.ForecastSynthesizer.synthesize', forbidden)
    report = report_with('The source describes a proposed trial.')
    agent._apply_forecast_synthesis(report, None)
    assert report.forecast['probabilities'] == frozen['probabilities']
    assert '46.5%' in report.markdown_content


def test_legacy_reports_are_not_given_new_verified_provenance():
    report = report_with('The scenario has a 55% probability of support.')
    report.source_grounding = {}
    assert not any(i['code'] == 'forecast_probability_mismatch' for i in ReportManager.validate_report_output(report))


def test_general_report_packet_filters_original_scope_and_separates_trace_origins(tmp_path):
    import json
    from app.services.report_grounding import build_report_grounding
    scope = {'graph_id': 'graph_contract', 'case_id': 'case_contract', 'case_version_id': 'version_original'}
    class Storage:
        def get_source_chunks(self, **requested):
            assert requested == scope
            return [{**scope, 'uuid': 'e1', 'document_id': 'doc_1', 'data': SOURCE, 'page': 1},
                {**scope, 'uuid': 'e2', 'document_id': 'doc_2', 'data': 'Wrong version', 'case_version_id': 'newer'},
                {**scope, 'uuid': 'e3', 'document_id': 'doc_3', 'data': 'Graph paraphrase', 'origin': 'simulation'}]
    path = tmp_path / 'twitter'
    path.mkdir()
    rows = [{'agent_id': 0, 'action_type': 'CREATE_POST', 'round': 0, 'origin': 'initial_post', 'trace_id': 1, 'action_args': {'content': 'Seed input', 'post_id': 1}},
        {'agent_id': 0, 'action_type': 'CREATE_POST', 'round': 1, 'origin': 'model_action', 'trace_id': 2, 'action_args': {'content': 'Actual model response', 'post_id': 2}}]
    (path / 'actions.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))
    packet = build_report_grounding(Storage(), scope, scope['graph_id'], tmp_path)
    assert [source['excerpt'] for source in packet['original_sources']] == [SOURCE]
    assert packet['original_sources'][0]['source_hash']
    assert packet['simulation_activity']['summary']['model_actions'] == 1
    assert packet['simulation_activity']['actions'][1]['reference'] == 'twitter:trace:2'
    assert packet['digest']


def test_source_scope_failure_is_visible_not_replaced_with_latest_version(tmp_path):
    from app.services.report_grounding import build_report_grounding
    packet = build_report_grounding(None, {}, 'graph_contract', tmp_path)
    assert packet['status'] == 'unavailable' and not packet['original_sources']
    assert 'original_source_scope_or_retrieval_unavailable' in packet['limitations']


def test_short_invented_dialogue_is_rejected():
    report = report_with('Maya said "I oppose this." [doc_1]')
    assert any(i['code'] == 'unverified_quotation' for i in ReportManager.validate_report_output(report))


def test_reference_identity_is_exact_not_a_substring():
    report = report_with(f'Original packet: "{SOURCE}" [doc_10]\n\n'
        'Simulated response: "A trial could help, provided loading access stays open." [twitter:trace:30]')
    assert len([i for i in ReportManager.validate_report_output(report) if i['code'] == 'unverified_quotation']) == 2


def test_existing_forecast_authority_is_bound_before_resume_prompts(monkeypatch):
    agent = ReportAgent.__new__(ReportAgent)
    agent.simulation_id, agent.simulation_config, agent.report_mode = 'sim_contract', {}, 'prediction'
    report = report_with('Existing report')
    def forbidden(*args, **kwargs):
        raise AssertionError('Resume may not derive a replacement probability from current actions')
    monkeypatch.setattr('app.services.report_agent.ForecastSynthesizer.synthesize', forbidden)
    agent._bind_report_contract(report)
    assert agent._frozen_forecast()['probabilities'] == report.forecast['probabilities']
    assert agent._load_source_grounding() == report.source_grounding


def test_interrupted_initial_planning_retains_forecast_authority(tmp_path, monkeypatch):
    from app.config import Config
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    monkeypatch.setattr(Config, 'UPLOAD_FOLDER', str(tmp_path))
    agent = ReportAgent.__new__(ReportAgent)
    agent.simulation_id, agent.graph_id, agent.simulation_requirement = 'sim_contract', 'graph_contract', 'fictional test'
    agent.report_mode, agent.report_depth = 'prediction', 'fast'
    agent._forecast_authority = {'status': 'available', 'probabilities': [{'outcome': 'Support', 'probability': .465}]}
    agent._source_grounding = {'report_contract': 'report-grounding-v1', 'status': 'unavailable'}
    agent.report_logger = agent.console_logger = None
    def interrupt(**kwargs):
        saved = ReportManager.get_report('report_interrupted')
        assert saved.forecast['probabilities'][0]['probability'] == .465
        raise RuntimeError('controlled planning interruption')
    agent.plan_outline = interrupt
    result = agent.generate_report('report_interrupted')
    assert result.status == ReportStatus.FAILED
    assert ReportManager.get_report(result.report_id).forecast == agent._forecast_authority
