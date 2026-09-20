from app.services.forecasting import ForecastSynthesizer, forecast_to_markdown
from app.services.report_agent import ReportAgent, Report, ReportStatus, ReportManager
from app.services.procedural_grounding import build_grounding, attribution_issues


def cover(role='DEFENDANTS', **extra):
    return dict(uuid='ep1', graph_id='g', case_id='c', case_version_id='v', document_id='d', page=1,
                data=f'MOTION RECORD OF THE {role}\nA PERSON AND A COMPANY\nMotion to set aside an injunction', **extra)


def test_no_actions_never_produce_probabilities_or_numeric_estimates(monkeypatch):
    synth = ForecastSynthesizer('absent', {'forecast_mode': 'general'})
    monkeypatch.setattr(synth, 'build_simulation_signal', lambda: None)
    monkeypatch.setattr(synth, '_load_ensemble_signal', lambda: None)
    forecast = synth.synthesize('Strong positive evidence. ' * 300, [{'fact': 'Evidence'}] * 10)
    assert forecast['status'] == 'unavailable'
    assert forecast['probabilities'] == [] and forecast['numeric'] is None
    assert forecast['confidence'] == 'unavailable'
    assert 'Probability Summary' not in forecast_to_markdown(forecast)


def test_scoped_source_role_and_conflict_detection():
    grounding = build_grounding([cover()], 'g', 'c', 'v')
    assert grounding['anchors'][0]['moving_role'] == 'defendants'
    assert attribution_issues('The plaintiffs seek to set aside the injunction.', grounding)
    assert attribution_issues("The plaintiffs’ motion to set aside the injunction raises issues.", grounding)
    assert not attribution_issues('The defendants seek to set aside the injunction. The plaintiffs oppose the motion.', grounding)
    assert not attribution_issues('The plaintiffs sought the original injunction.', grounding)
    assert not build_grounding([cover()], 'other', 'c', 'v')['anchors']
    assert not build_grounding([cover()], 'g', 'c', 'wrong')['anchors']


def test_ambiguous_source_roles_are_not_resolved_by_guessing():
    assert build_grounding([cover(), cover('PLAINTIFFS')], 'g', 'c', 'v')['status'] == 'ambiguous'


def test_review_required_overrides_high_quality_in_shadow():
    report = Report('r', 's', 'g', 'audit', ReportStatus.COMPLETED,
                    quality_score={'score': 100}, validation_issues=[{'requires_review': True}])
    report.decision_config = {'features': {'evidence': {'mode': 'shadow'}}}
    ReportManager.apply_quality_status(report)
    assert report.status == ReportStatus.NEEDS_REVIEW


def test_source_grounding_survives_save_and_flags_wrong_draft(tmp_path, monkeypatch):
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    grounding = build_grounding([cover()], 'g', 'c', 'v')
    report = Report('r', 's', 'g', 'audit', ReportStatus.COMPLETED, report_mode='legal_case',
                    markdown_content='The plaintiffs seek to set aside the injunction.', source_grounding=grounding)
    ReportManager.save_report(report)
    loaded = ReportManager.get_report('r')
    assert loaded.source_grounding == grounding
    assert any(i['code'] == 'procedural_role_conflict' for i in ReportManager.validate_report_output(loaded))


def test_no_action_guidance_does_not_demand_probability_tables(monkeypatch):
    agent = ReportAgent.__new__(ReportAgent)
    agent.simulation_id = 'none'
    agent.simulation_config = {}
    agent.report_mode = 'legal_case'
    monkeypatch.setattr(ForecastSynthesizer, 'build_simulation_signal', lambda self: None)
    monkeypatch.setattr(ForecastSynthesizer, '_load_ensemble_signal', lambda self: None)
    guidance = agent._report_mode_guidance()
    assert 'no recorded simulation actions' in guidance
    assert 'Include a probability' not in guidance


def test_empty_ensemble_does_not_bypass_no_action_guard(monkeypatch):
    synth = ForecastSynthesizer('none', {})
    monkeypatch.setattr(synth, 'build_simulation_signal', lambda: None)
    monkeypatch.setattr(synth, '_load_ensemble_signal', lambda: {'runs': 3, 'total_actions': 0, 'mean_probabilities': [.3, .4, .3]})
    assert synth.synthesize('Strong evidence')['status'] == 'unavailable'


def test_probability_claim_requires_review_but_source_percentages_do_not():
    report = Report('r', 's', 'g', 'audit', ReportStatus.COMPLETED,
                    forecast={'status': 'unavailable'}, markdown_content='There is a 70% probability of success.')
    assert any(i['code'] == 'unsupported_forecast' for i in ReportManager.validate_report_output(report))
    report.markdown_content = 'The affidavit reports a 70% ownership interest.'
    assert not any(i['code'] == 'unsupported_forecast' for i in ReportManager.validate_report_output(report))


def test_oversized_cover_does_not_hide_conflicting_procedural_sources():
    other = cover('PLAINTIFFS')
    other['data'] += 'x' * 13000
    assert build_grounding([cover(), other], 'g', 'c', 'v')['status'] == 'ambiguous'


def test_availability_notice_is_not_scored_as_an_evidence_section():
    sections = ReportManager._extract_report_sections('## Forecast Availability\n\nNo forecast.\n\n# Audit\n\n## Parties\n\nSource facts.')
    assert len(sections) == 1 and 'Source facts.' in sections[0]
