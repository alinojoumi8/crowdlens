"""Synthetic reference texts; no private matter documents or real legal rules."""
from copy import deepcopy

import pytest

from app.services.report_agent import Report, ReportAgent, ReportStatus
from test_evidence_quality_faults import root_admission


AUTHORITY = {'citation': 'Fictional Reference, 2000 EX 1',
    'source_url': 'https://example.test/decision/1', 'retrieved_at': '2026-11-08',
    'verification_note': 'Synthetic fixture, not a verified authority.',
    'treatment_note': 'No treatment checked in this fixture.',
    'paragraphs': {'4': 'The fictional proponent must establish the fictional threshold.'}}


def test_authority_text_is_separate_from_case_facts_and_has_content_bound_identity():
    from app.services.legal_authorities import normalize_legal_authorities, attach_legal_authorities
    source = deepcopy(AUTHORITY)
    rows = normalize_legal_authorities([source])
    original = {'report_contract': 'report-grounding-v1', 'original_sources': [
        {'document_id': 'doc_case', 'excerpt': 'The memo alleges a disputed contact.'}], 'digest': 'original'}
    packet = attach_legal_authorities(original, rows)
    assert packet['original_sources'] == original['original_sources']
    assert packet['authority_sources'][0]['excerpt'] == AUTHORITY['paragraphs']['4']
    assert packet['authority_sources'][0]['source_kind'] == 'legal_authority'
    assert packet['authority_sources'][0]['source_url'] == AUTHORITY['source_url']
    assert packet['authority_digest'] and packet['digest'] != original['digest']
    assert 'authority_sources' not in original
    source['paragraphs']['4'] = 'Changed after submission.'
    assert rows[0]['excerpt'] == AUTHORITY['paragraphs']['4']
    changed = normalize_legal_authorities([{**AUTHORITY, 'paragraphs': {'4': 'A different reference text.'}}])
    assert changed[0]['document_id'] != rows[0]['document_id']


@pytest.mark.parametrize('value', [None, {}, 'reference', [42], [{**AUTHORITY, 'paragraphs': {}}],
    [{**AUTHORITY, 'source_url': 'file:///private/file'}],
    [{**AUTHORITY, 'source_url': 'https://user:password@example.test/case'}],
    [{**AUTHORITY, 'retrieved_at': 'not-a-date'}],
    [{**AUTHORITY, 'paragraphs': {'4': 42}}],
    [AUTHORITY, AUTHORITY], [AUTHORITY] * 13])
def test_invalid_authority_packets_are_rejected(value):
    from app.services.legal_authorities import normalize_legal_authorities
    with pytest.raises(ValueError, match='legal_authorit'):
        normalize_legal_authorities(value)


def test_reference_citations_and_quotes_are_checked_against_exact_authority_text():
    from app.services.legal_authorities import normalize_legal_authorities, attach_legal_authorities
    from app.services.report_grounding import provenance_issues
    packet = attach_legal_authorities({'report_contract': 'report-grounding-v1',
        'status': 'available', 'original_sources': []}, normalize_legal_authorities([AUTHORITY]))
    identifier = packet['authority_sources'][0]['document_id']
    exact = f'Authority: "{AUTHORITY["paragraphs"]["4"]}" [{identifier}, para. 4]'
    assert not any(row.get('blocking') for row in provenance_issues(exact, packet, {}))
    invented = exact.replace('fictional threshold', 'invented rule')
    assert any(row['code'] == 'unverified_quotation' for row in provenance_issues(invented, packet, {}))


def test_saved_report_preserves_authorities_when_chat_or_resume_rebinds_the_contract():
    from app.services.legal_authorities import normalize_legal_authorities, attach_legal_authorities
    packet = attach_legal_authorities({'report_contract': 'report-grounding-v1',
        'status': 'available', 'original_sources': []}, normalize_legal_authorities([AUTHORITY]))
    report = Report('report_reference', 'sim_reference', 'graph_reference', 'Synthetic question',
        ReportStatus.NEEDS_REVIEW, source_grounding=packet,
        forecast={'status': 'unavailable', 'reason': 'evidence_only'})
    agent = ReportAgent.__new__(ReportAgent)
    agent._bind_report_contract(report)
    prompt = agent._source_grounding_prompt()
    assert AUTHORITY['paragraphs']['4'] in prompt and AUTHORITY['source_url'] in prompt
    assert agent._source_grounding['authority_digest'] == packet['authority_digest']
    agent._source_grounding['authority_sources'][0]['excerpt'] = 'Altered worker copy.'
    assert report.source_grounding == packet


def test_authority_packet_changes_cannot_replay_a_different_generation_request(root_admission):
    from test_evidence_quality_faults import ROOT_REQUEST
    app, db, dispatched = root_admission
    client = app.test_client()
    first = client.post('/api/report/generate', json={**ROOT_REQUEST, 'legal_authorities': [AUTHORITY]})
    changed = client.post('/api/report/generate', json={**ROOT_REQUEST, 'legal_authorities': [
        {**AUTHORITY, 'paragraphs': {'4': 'Different reference text.'}}]})
    assert first.status_code == 200
    assert changed.status_code == 409 and changed.json['error'] == 'request_key_conflict'
    assert len(dispatched) == len(db.list_tasks()) == 1


def test_invalid_authorities_fail_before_task_or_provider_admission(root_admission):
    from test_evidence_quality_faults import ROOT_REQUEST
    app, db, dispatched = root_admission
    result = app.test_client().post('/api/report/generate', json={**ROOT_REQUEST, 'legal_authorities': {}})
    assert result.status_code == 400 and not db.list_tasks() and not dispatched


def test_case_source_identity_cannot_be_supplied_in_a_reference_payload():
    from app.services.legal_authorities import normalize_legal_authorities
    rows = normalize_legal_authorities([{**AUTHORITY, 'document_id': 'doc_case', 'source_kind': 'case_fact',
                                        'verification_status': 'court_certified'}])
    assert rows[0]['document_id'].startswith('doc_law_')
    assert rows[0]['source_kind'] == 'legal_authority'
    assert rows[0]['verification_status'] != 'court_certified'


def test_agent_attaches_references_without_adding_them_to_the_case_graph(monkeypatch):
    from types import SimpleNamespace
    from app.services import report_agent, report_grounding
    base = {'report_contract': 'report-grounding-v1', 'status': 'available',
            'original_sources': [{'document_id': 'doc_case', 'excerpt': 'A disputed source allegation.'}]}
    monkeypatch.setattr(report_agent, 'load_simulation_config', lambda _: {})
    monkeypatch.setattr(report_grounding, 'build_report_grounding', lambda *a: deepcopy(base))
    agent = ReportAgent('graph_ref', 'sim_ref', 'Synthetic question', llm_client=object(),
        graph_tools=SimpleNamespace(storage=SimpleNamespace(get_document_covers=lambda *a: [])),
        report_mode='legal_case', legal_authorities=[AUTHORITY])
    packet = agent._load_source_grounding()
    assert packet['original_sources'] == base['original_sources']
    assert packet['authority_sources'][0]['excerpt'] == AUTHORITY['paragraphs']['4']
    assert packet['authority_digest']


def test_memo_only_cached_report_is_not_reused_for_an_authority_enriched_request(root_admission, monkeypatch):
    from app.api import report as api
    from test_evidence_quality_faults import ROOT_REQUEST
    app, db, dispatched = root_admission
    previous = Report('old', 'eq_sim', 'eq_graph', 'Synthetic', ReportStatus.NEEDS_REVIEW,
                      report_mode='legal_case')
    monkeypatch.setattr(api.ReportManager, 'get_report_by_simulation', lambda *a, **kw: previous)
    result = app.test_client().post('/api/report/generate', json={**ROOT_REQUEST, 'legal_authorities': [AUTHORITY]})
    assert result.status_code == 200
    assert result.json['data']['report_id'] != previous.report_id
    assert len(dispatched) == len(db.list_tasks()) == 1


def test_report_lookup_returns_the_newest_report_with_the_requested_authority_set(tmp_path, monkeypatch):
    from app.services.report_agent import Report, ReportManager, ReportStatus
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    for report_id, created, digest in [('report_a', '2026-11-01T00:00:00', 'digest-a'),
                                       ('report_b', '2026-11-02T00:00:00', 'digest-b'),
                                       ('report_c', '2026-11-03T00:00:00', None)]:
        ReportManager.save_report(Report(report_id=report_id, simulation_id='sim_x', graph_id='graph_x',
            simulation_requirement='Review.', status=ReportStatus.COMPLETED, created_at=created,
            source_grounding={'authority_digest': digest} if digest else {}))

    lookup = lambda **kw: ReportManager.get_report_by_simulation('sim_x', **kw).report_id
    assert lookup() == 'report_c'
    assert lookup(authority_digest='digest-a') == 'report_a'
    assert lookup(authority_digest='digest-b') == 'report_b'
    assert lookup(authority_digest=None) == 'report_c'
    assert ReportManager.get_report_by_simulation('sim_x', authority_digest='digest-z') is None
