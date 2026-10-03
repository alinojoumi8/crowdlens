"""Trace-derived regressions; no model or human quality labels are fabricated."""
import hashlib
import json
from pathlib import Path

import pytest

from app.services.report_agent import Report, ReportManager, ReportStatus


def packet():
    return {'report_contract': 'report-grounding-v1', 'status': 'available', 'limitations': [],
            'original_sources': [], 'simulation_activity': {'summary': {'model_actions': 2, 'unknown_origin_actions': 0},
            'actions': [
                {'reference': 'twitter:trace:11', 'origin': 'model_action', 'round_num': 1, 'agent_name': 'Maya Chen'},
                {'reference': 'twitter:trace:14', 'origin': 'model_action', 'round_num': 2, 'agent_name': 'Maya Chen'},
                {'reference': 'twitter:trace:9', 'origin': 'scheduled_event', 'round_num': 1, 'agent_name': 'Daniel Brooks'},
                {'reference': 'twitter:trace:3', 'origin': 'initial_post', 'round_num': 0, 'agent_name': 'Leo Martin'},
                {'reference': 'twitter:trace:4', 'origin': 'initial_post', 'round_num': 0, 'agent_name': 'Priya Shah'},
            ]}}


def report(text, grounding=None):
    return Report('semantic_report', 'simulation', 'graph', 'fictional test', ReportStatus.COMPLETED,
                  markdown_content=text, source_grounding=grounding or packet(), forecast={'status': 'unavailable'})


def semantic_issues(value):
    return [i for i in ReportManager.validate_report_output(value) if i.get('check_family') == 'semantic_review']


def test_actual_round_one_contradiction_requires_review_even_with_score_100():
    fixture = json.loads((Path(__file__).parent/'fixtures/report_grounding/cedarbrook-semantic.json').read_text())
    value = report(fixture['markdown_content'], fixture['source_grounding']);value.forecast=fixture['forecast']
    value.validation_issues = ReportManager.validate_report_output(value)
    assert set(fixture['expected_issue_codes']) <= {i['code'] for i in value.validation_issues}
    found = next(i for i in value.validation_issues if i['code']=='round_action_count_conflict')
    assert found['requires_review'] and not found['blocking']
    assert any(e['reference']=='twitter:trace:11' for e in found['evidence'])
    value.quality_score={'score':100}
    ReportManager.apply_quality_status(value)
    assert value.status == ReportStatus.NEEDS_REVIEW


@pytest.mark.parametrize('text,code', [
    ('Round 1 contains no model actions.', 'round_action_count_conflict'),
    ('No model actions occurred in Round 1.', 'round_action_count_conflict'),
    ('Round 1 produced 2 model actions.', 'round_action_count_conflict'),
    ('Leo Martin at `twitter:trace:11` generated the post.', 'trace_author_conflict'),
    ('The Round 2 model action belongs to Maya Chen at `twitter:trace:11`.', 'trace_round_conflict'),
    ('The model action at `twitter:trace:9` is a response.', 'trace_origin_conflict'),
])
def test_distinct_explicit_trace_contradictions(text, code):
    assert code in {i['code'] for i in semantic_issues(report(text))}


@pytest.mark.parametrize('text', [
    'Round 1 contains 1 model action.',
    'Round 3 contains no model actions.',
    'Round 2 contains no model actions from Daniel, Leo or Priya.',
    'Maya Chen at `twitter:trace:11` generated the post.',
    "Leo Martin asks about Maya Chen's post at `twitter:trace:11`.",
    'The Round 1 model action belongs to Maya Chen at `twitter:trace:11`.',
    'The scheduled input at `twitter:trace:9` is scenario content.',
    'If Round 1 contains no model actions, the report should say so.',
    'It is false that Round 1 contains no model actions.',
    '> Round 1 contains no model actions.',
])
def test_true_scoped_quoted_and_hypothetical_statements_are_not_contradictions(text):
    assert not semantic_issues(report(text))


def test_truncated_packet_cannot_disprove_missing_action_but_can_show_observed_one():
    grounding=packet();grounding['limitations']=['report_action_context_truncated']
    assert not any(i['code']=='round_action_count_conflict' for i in semantic_issues(report('Round 2 contains 3 model actions.', grounding)))
    assert any(i['code']=='semantic_claim_unverified' for i in semantic_issues(report('Round 2 contains 3 model actions.', grounding)))
    assert any(i['code']=='round_action_count_conflict' for i in semantic_issues(report('Round 1 contains no model actions.', grounding)))


@pytest.mark.parametrize('endpoint', ['/api/report/semantic_report', '/api/report/by-simulation/simulation'])
def test_read_assessment_adds_findings_without_changing_saved_report(tmp_path, monkeypatch, endpoint):
    from flask import Flask
    from app.api import report_bp
    monkeypatch.setattr(ReportManager,'REPORTS_DIR',str(tmp_path))
    value=report('Round 1 contains no model actions.');ReportManager.save_report(value)
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/value.report_id).iterdir() if p.is_file()}
    app=Flask(__name__);app.register_blueprint(report_bp,url_prefix='/api/report')
    response=app.test_client().get(endpoint)
    assert response.status_code==200
    assert response.json['data']['status']=='completed'  # Historical persisted state is retained.
    assert response.json['data']['current_review']['requires_review']
    assert response.json['data']['current_review']['issues'][0]['code']=='round_action_count_conflict'
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/value.report_id).iterdir() if p.is_file()}
    assert before==after


def test_new_revision_keeps_unresolved_premise_and_legacy_read_checks_sealed_provenance(tmp_path, monkeypatch):
    from evidence_draft_samples import sample_report
    from test_evidence_drafting import run, SourceStorage
    from app.services.proposal_store import ProposalStore, proposal_digest
    from app.services.report_revisions import ReportRevisionService
    from app.services.report_semantics import current_review
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    ReportManager.save_report(sample_report())
    record, _ = run(tmp_path)
    record['findings'] = [{'code':'premise_unverified','blocking':False,'claim_id':'claim_01'}]
    record['proposal_digest']=proposal_digest(record)
    service=ReportRevisionService(ProposalStore(tmp_path),storage=SourceStorage())
    # Test assembly with a retained nonblocking finding; acceptance/digest guards are tested separately.
    revision=service._assemble(sample_report(),record,'2026-10-03')
    assert revision.revision['review_findings'][0]['code']=='proposal_premise_unverified'
    assert revision.quality_score['status']=='needs_review'
    service._publish(revision,record)
    before={str(p.relative_to(tmp_path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*') if p.is_file()}
    # Legacy metadata had no review_findings; sealed provenance remains the evidence.
    revision.revision.pop('review_findings')
    assessed=current_review(revision,tmp_path)
    assert assessed['issues'][0]['code']=='proposal_premise_unverified'
    assert assessed['issues'][0]['origin']=='proposal_model_audit'
    assert before=={str(p.relative_to(tmp_path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*') if p.is_file()}
    (tmp_path/revision.report_id/'provenance.json').write_text('{}')
    assert current_review(revision,tmp_path)['issues'][0]['code']=='proposal_review_unverified'


def test_duplicate_and_unknown_origins_cannot_establish_absence():
    grounding=packet();grounding['simulation_activity']['actions'].append(dict(grounding['simulation_activity']['actions'][2]))
    issues=semantic_issues(report('Round 3 contains 1 model action.',grounding))
    assert [i['code'] for i in issues]==['semantic_claim_unverified']
    grounding=packet();grounding['simulation_activity']['actions'][2]['origin']='unknown'
    assert [i['code'] for i in semantic_issues(report('Round 3 contains 1 model action.',grounding))]==['semantic_claim_unverified']


def test_unbound_round_comparison_and_unknown_trace_origin_are_not_false_conflicts():
    assert not semantic_issues(report("The Round 2 model action refers to Maya Chen's post at twitter:trace:11."))
    grounding=packet();grounding['simulation_activity']['actions'][2]['origin']='unknown'
    assert [i['code'] for i in semantic_issues(report('The model action at twitter:trace:9 is a response.',grounding))]==['semantic_claim_unverified']


@pytest.mark.parametrize('text', [
    'This is not a model action at twitter:trace:9; it is scheduled input.',
    'Not Leo Martin at twitter:trace:11; the recorded author is Maya Chen.',
    'It is not true that Round 1 contains no model actions.',
])
def test_negated_assertions_do_not_become_conflicts(text):
    assert not semantic_issues(report(text))


def test_duplicate_trace_does_not_inflate_positive_proof():
    grounding=packet();grounding['simulation_activity']['actions'].append(dict(grounding['simulation_activity']['actions'][0]))
    assert [i['code'] for i in semantic_issues(report('Round 1 contains 1 model action.',grounding))]==['semantic_claim_unverified']


def test_missing_authors_and_boolean_rounds_cannot_prove_contradictions():
    grounding=packet();grounding['simulation_activity']['actions'][0]['agent_name']=None
    assert [i['code'] for i in semantic_issues(report('Round 1 contains 1 model action from Leo.',grounding))]==['semantic_claim_unverified']
    grounding=packet();grounding['simulation_activity']['actions'][0]['round_num']=True
    assert [i['code'] for i in semantic_issues(report('Round 1 contains no model actions.',grounding))]==['semantic_claim_unverified']


def test_blank_author_is_unverified_and_does_not_crash_read_assessment():
    grounding=packet();grounding['simulation_activity']['actions'][0]['agent_name']='   '
    assert [i['code'] for i in semantic_issues(report('Leo Martin at twitter:trace:11 generated the post.',grounding))]==['semantic_claim_unverified']
