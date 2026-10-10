from app.services.forecasting import ForecastSynthesizer, forecast_to_markdown
from app.services.report_agent import ReportAgent, Report, ReportStatus, ReportManager
from app.services.procedural_grounding import build_grounding, attribution_issues, marked_source_openings
from types import SimpleNamespace
import pytest


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


@pytest.mark.parametrize('covers,expected', [([cover()], 'anchored'),
    ([cover(), cover('PLAINTIFFS')], 'ambiguous'), ([], 'unavailable'),
    ([cover()] * 25, 'ambiguous')])
def test_report_contract_keeps_source_availability_separate_from_role_coverage(monkeypatch, covers, expected):
    from app.services import report_grounding
    monkeypatch.setattr(report_grounding, 'build_report_grounding', lambda *args: {
        'report_contract': 'report-grounding-v1', 'status': 'available',
        'case_id': 'c', 'case_version_id': 'v', 'original_sources': []})
    agent = ReportAgent.__new__(ReportAgent)
    agent.simulation_id, agent.graph_id = 's', 'g'
    agent.simulation_config, agent.report_mode = {}, 'legal_case'
    agent.graph_tools = SimpleNamespace(storage=SimpleNamespace(get_document_covers=lambda *args: covers))
    grounding = agent._load_source_grounding()
    assert grounding['status'] == 'available'
    assert grounding['procedural_status'] == expected
    issues = attribution_issues('The plaintiffs seek to set aside the injunction.', grounding)
    assert issues[0]['code'] == ('procedural_role_conflict' if expected == 'anchored' else 'procedural_source_unavailable')
    if expected == 'anchored':
        assert not attribution_issues('The defendants seek to set aside the injunction.', grounding)


def test_notice_caption_and_legacy_available_status_do_not_certify_roles():
    notice = cover()
    notice['data'] = 'Plaintiffs and Defendants\nNOTICE OF MOTION\nThe defendants will make a motion.'
    grounding = build_grounding([notice], 'g', 'c', 'v')
    assert grounding['status'] == 'notice_anchored'
    assert grounding['notice_anchors'][0]['moving_role'] == 'defendants'
    assert attribution_issues('Anything', {'status': 'available', 'anchors': [cover()]})


def notice(role='DEFENDANTS', document='doc_defendants', cross=False):
    row = cover()
    row.update(document_id=document, data=(
        'PLAINTIFFS\nA PERSON\nDEFENDANTS\nA COMPANY\nNOTICE OF '
        + ('CROSS-MOTION' if cross else 'MOTION')
        + f'\nThe {role} A PERSON and A COMPANY LTD. will make a motion to a Judge.'))
    return row


def test_paired_notices_keep_separate_document_movers_and_flag_swaps():
    grounding = build_grounding([notice(), notice('PLAINTIFFS', 'doc_plaintiffs', True)], 'g', 'c', 'v')
    assert grounding['status'] == 'notice_anchored'
    assert {n['document_id']: n['moving_role'] for n in grounding['notice_anchors']} == {
        'doc_defendants': 'defendants', 'doc_plaintiffs': 'plaintiffs'}
    assert grounding['notice_anchors'][1]['notice_kind'] == 'cross_motion'
    correct = "The defendants’ notice is dated April 29, 2025. [doc_defendants]\n\nThe plaintiffs’ notice is dated September 22, 2025. [doc_plaintiffs]"
    assert attribution_issues(correct, grounding) == []
    wrong = "The plaintiffs’ notice is dated April 29, 2025. [doc_defendants]"
    assert attribution_issues(wrong, grounding)[0]['document_id'] == 'doc_defendants'
    assert attribution_issues('The defendants signed this notice. [doc_plaintiffs]', grounding)


@pytest.mark.parametrize('text', [
    'PLAINTIFFS\nDEFENDANTS\nNOTICE OF MOTION\nThe caption lists the defendants.',
    'PLAINTIFFS\nDEFENDANTS\nThe plaintiffs will make a motion.',
    'NOTICE OF MOTION\nThe defendants oppose the plaintiffs who will make a motion.',
    'NOTICE OF MOTION\nTHE DEFENDANTS OPPOSE THE PLAINTIFFS WHO WILL MAKE A MOTION.',
    'NOTICE OF MOTION\nThe defendants do not consent. The plaintiffs will make a motion.',
])
def test_notice_role_requires_direct_declaration_after_heading(text):
    row = notice(); row['data'] = text
    grounding = build_grounding([row], 'g', 'c', 'v')
    assert grounding['status'] in {'unavailable', 'ambiguous'}
    assert not grounding['notice_anchors']


def test_notice_declarations_remain_scoped_and_conflicts_require_review():
    assert not build_grounding([notice()], 'g', 'c', 'other')['notice_anchors']
    row = notice(); row['origin'] = 'scheduled_event'
    assert not build_grounding([row], 'g', 'c', 'v')['notice_anchors']
    assert build_grounding([notice(), notice('PLAINTIFFS')], 'g', 'c', 'v')['status'] == 'ambiguous'
    oversized = notice('PLAINTIFFS'); oversized['data'] += 'x' * 13000
    assert build_grounding([notice(), oversized], 'g', 'c', 'v')['status'] == 'ambiguous'
    incomplete = notice('PLAINTIFFS', 'doc_plaintiffs'); incomplete['data'] = 'NOTICE OF CROSS-MOTION\nUnrecognized declaration'
    assert build_grounding([notice(), incomplete], 'g', 'c', 'v')['status'] == 'ambiguous'
    assert build_grounding([cover(), notice()], 'g', 'c', 'v')['status'] == 'ambiguous'


@pytest.mark.parametrize('text', [
    'The plaintiffs oppose the defendants’ notice. [doc_defendants]',
    'Whether the plaintiffs’ notice was served is unknown. [doc_defendants]',
    'The plaintiffs’ original notice differs. [doc_defendants]',
    '“The plaintiffs’ notice” is an allegation. [doc_defendants]',
    '> The plaintiffs’ notice was filed. [doc_defendants]',
    'The plaintiffs’ notice and defendants’ notice differ. [doc_defendants] [doc_plaintiffs]',
    'The plaintiffs request production, while the defendants’ notice contests the injunction. [doc_plaintiffs]',
    'The defendants’ notice contests the injunction. The plaintiffs request production. [doc_plaintiffs]',
])
def test_notice_check_does_not_guess_comparisons_quotes_or_prior_motions(text):
    grounding = build_grounding([notice(), notice('PLAINTIFFS', 'doc_plaintiffs', True)], 'g', 'c', 'v')
    assert not attribution_issues(text, grounding)


def test_notice_anchors_survive_persistence_without_global_relief_binding(tmp_path, monkeypatch):
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    grounding = build_grounding([notice()], 'g', 'c', 'v')
    report = Report('r', 's', 'g', 'audit', ReportStatus.COMPLETED, report_mode='legal_case',
        source_grounding=grounding, markdown_content="The plaintiffs’ notice is signed. [doc_defendants]")
    ReportManager.save_report(report)
    loaded = ReportManager.get_report('r')
    assert loaded.source_grounding == grounding
    assert any(i['code'] == 'procedural_role_conflict' for i in ReportManager.validate_report_output(loaded))
    assert not attribution_issues('The plaintiffs seek to set aside the injunction.', grounding)


def test_marker_openings_require_complete_page_one_and_retain_source_locator():
    source = {**notice(), 'episode_id': 'ep_notice', 'source_hash': 'chunk_hash',
        'excerpt': '[PDF page 1]\n' + notice()['data'] + '\n[PDF page 2]\nMore text'}
    openings = marked_source_openings([source])
    assert len(openings) == 1 and openings[0]['data'] == source['excerpt']
    grounding = build_grounding(openings, 'g', 'c', 'v')
    anchor = grounding['notice_anchors'][0]
    assert anchor['locator_basis'] == 'pdf_page_markers'
    assert anchor['chunk_source_hash'] == 'chunk_hash'
    assert anchor['page_start'] == 0 and anchor['page_end'] == source['excerpt'].index('[PDF page 2]')
    assert not marked_source_openings([{**source, 'excerpt': '[PDF page 1]\n' + notice()['data']}])
    assert not marked_source_openings([{**source, 'excerpt': notice()['data']}])
    assert not build_grounding(openings, 'g', 'wrong', 'v')['notice_anchors']

    late = notice()
    late['data'] = '[PDF page 1]\nOnly a caption.\n[PDF page 2]\n' + notice()['data'] + '\n[PDF page 3]\nMore'
    assert not build_grounding([late], 'g', 'c', 'v')['notice_anchors']


def test_report_agent_uses_frozen_page_markers_when_page_metadata_is_missing(monkeypatch):
    from app.services import report_grounding
    source = {**notice(), 'episode_id': 'ep_notice', 'excerpt': '[PDF page 1]\n' + notice()['data'] + '\n[PDF page 2]\nMore'}
    monkeypatch.setattr(report_grounding, 'build_report_grounding', lambda *args: {
        'status': 'available', 'case_id': 'c', 'case_version_id': 'v', 'original_sources': [source]})
    agent = ReportAgent.__new__(ReportAgent)
    agent.simulation_id, agent.graph_id, agent.simulation_config, agent.report_mode = 's', 'g', {}, 'legal_case'
    agent.graph_tools = SimpleNamespace(storage=SimpleNamespace(get_document_covers=lambda *args: []))
    assert agent._load_source_grounding()['procedural_status'] == 'notice_anchored'

    del agent._source_grounding
    def failed(*args):
        raise RuntimeError('source lookup unavailable')
    agent.graph_tools.storage.get_document_covers = failed
    assert agent._load_source_grounding()['procedural_status'] == 'ambiguous'
