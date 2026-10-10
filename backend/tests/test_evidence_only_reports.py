"""Evidence-only reporting remains distinct across persistence and replay."""
from copy import deepcopy
from unittest.mock import patch

from app.services.report_agent import Report, ReportAgent, ReportManager, ReportOutline, ReportStatus
from test_evidence_quality_faults import ROOT_REQUEST, root_admission


def make_report(**extra):
    return Report(report_id='report_evidence', simulation_id='sim_evidence', graph_id='graph_evidence',
                  simulation_requirement='Review source assertions.', status=ReportStatus.NEEDS_REVIEW, **extra)


def test_evidence_only_does_not_synthesize_even_with_existing_activity_and_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    agent = object.__new__(ReportAgent)
    agent.evidence_only = True
    agent._source_grounding = {'report_contract': 'report-grounding-v1'}
    agent._load_source_grounding = lambda: deepcopy(agent._source_grounding)
    report = make_report(evidence_only=True, markdown_content='Attributed source review.')
    with patch('app.services.report_agent.ForecastSynthesizer', side_effect=AssertionError('forecast called')):
        agent._bind_report_contract(report)
        agent._apply_forecast_synthesis(report, None)
        assert report.forecast['reason'] == 'evidence_only'
        assert report.forecast['probabilities'] == []
        assert 'Forecast Probability Summary' not in report.markdown_content
        assert 'no recorded simulation actions' not in agent._report_mode_guidance()
        assert 'Do not plan a forecast table' in agent._report_mode_guidance()
        ReportManager.save_report(report)
        restored = ReportManager.get_report(report.report_id)
        assert restored.evidence_only is True
        # Resume binds the saved setting, rather than current defaults or action data.
        agent.evidence_only = False
        agent._bind_report_contract(restored)
        assert agent.evidence_only is True
        assert not agent._forecast_available()


def test_legacy_serialization_keeps_sealed_report_shape():
    assert 'evidence_only' not in make_report().to_dict()
    assert make_report(evidence_only=True).to_dict()['evidence_only'] is True


def test_report_lookup_separates_forecast_and_evidence_only(tmp_path, monkeypatch):
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    report = make_report(evidence_only=True)
    ReportManager.save_report(report)
    assert ReportManager.get_report_by_simulation(report.simulation_id, evidence_only=False) is None
    assert ReportManager.get_report_by_simulation(report.simulation_id, evidence_only=True).report_id == report.report_id


def test_evidence_choice_is_part_of_request_identity(root_admission):
    app, db, dispatched = root_admission
    client = app.test_client()
    assert client.post('/api/report/generate', json=ROOT_REQUEST).status_code == 200
    response = client.post('/api/report/generate', json={**ROOT_REQUEST, 'evidence_only': True})
    assert response.status_code == 409
    assert response.json['error'] == 'request_key_conflict'
    assert len(dispatched) == 1


def test_pending_report_retains_explicit_choice_and_rejects_invalid_flag(root_admission):
    app, db, dispatched = root_admission
    client = app.test_client()
    assert client.post('/api/report/generate', json={**ROOT_REQUEST, 'evidence_only': 'false'}).status_code == 400
    response = client.post('/api/report/generate', json={**ROOT_REQUEST, 'evidence_only': True})
    report = client.get('/api/report/' + response.json['data']['report_id'])
    assert report.json['data']['evidence_only'] is True
    assert len(dispatched) == 1


def test_evidence_only_decimal_probability_table_cannot_escape_percent_guard():
    from app.services.report_grounding import provenance_issues
    grounding = {'report_contract':'report-grounding-v1','status':'available','original_sources':[]}
    forecast = {'status':'unavailable','reason':'evidence_only','probabilities':[]}
    text = '| Outcome | Scenario probability |\n|---|---:|\n| Success | 0.416 |\n'
    issues = provenance_issues(text, grounding, forecast)
    assert any(i['code'] == 'evidence_only_probability_table' and i['blocking'] for i in issues)
    assert not provenance_issues('Attributed source date: July 25, 2024.', grounding, forecast)
