"""Full-section review and explicit audit recovery without live providers."""
import copy
import json
import threading

import pytest
import requests

from app.services.report_agent import ReportManager
from test_evidence_proposals_api import app, terminal
from test_evidence_drafting import FakeLLM
from evidence_draft_samples import TEXT


URL = '/api/report/report_root/evidence-proposals'


def join_workers():
    for worker in threading.enumerate():
        if worker.name == 'evidence-proposal':
            worker.join(10)
            assert not worker.is_alive()


def test_selected_paraphrased_summary_can_be_corrected_without_changing_forecast(app):
    parent = ReportManager.get_report('report_root')
    selected = 'The hearing is expected to go ahead on Thursday.'
    parent.outline.summary = selected + ' Other issues remain open.'
    parent.forecast = {'forecast_mode': 'general', 'confidence': 'low',
        'probabilities': [{'outcome': 'Proceeds', 'probability': .6, 'rationale': 'Inherited synthetic estimate.'}]}
    ReportManager.save_report(parent)
    before = copy.deepcopy(parent.to_dict())
    store = app.extensions['evidence_proposal_store']
    app.extensions['evidence_llm_factory'] = lambda identifier: FakeLLM(store, identifier, {
        'EVIDENCE_DRAFT_V1': {'paragraphs': [{'text': TEXT, 'kind': 'attributed_allegation',
            'claim_ids': ['claim_01']}], 'section_summary_claim_ids': ['claim_01']}})
    client = app.test_client()
    response = client.post(URL, json={'section_index': 1, 'request_key': 'selected', 'summary_selection': selected})
    assert response.status_code == 202
    record = terminal(client, response.json['data']['proposal_id'])
    assert record['state'] == 'ready'
    assert record['before']['summary_scope_contract']['basis'] == 'operator_selected_summary'
    assert record['after']['summary'] == TEXT + ' Other issues remain open.'
    join_workers()
    saved = client.post(URL + '/' + record['proposal_id'] + '/accept', json={'proposal_digest': record['proposal_digest']})
    assert saved.status_code == 200
    revision = saved.json['data']
    assert revision['forecast'] == before['forecast']
    assert revision['revision']['inherited_forecast'] is True
    assert revision['status'] == 'needs_review'
    assert ReportManager.get_report('report_root').to_dict() == before


@pytest.mark.parametrize('selected', ['', ' ', 12, [], 'Missing passage', 'x' * 2001])
def test_invalid_summary_selection_never_schedules_model(app, selected):
    app.extensions['evidence_llm_factory'] = lambda _: pytest.fail('invalid selection reached model')
    response = app.test_client().post(URL, json={'section_index': 1, 'request_key': 'invalid',
        'summary_selection': selected})
    assert response.status_code == 400


def failed_audit(app):
    store = app.extensions['evidence_proposal_store']
    calls = []

    class TimeoutLLM(FakeLLM):
        def chat_json(self, messages, **kwargs):
            phase = messages[0]['content'].splitlines()[0]
            calls.append(phase)
            if phase == 'EVIDENCE_AUDIT_V1':
                kwargs['usage_callback']('synthetic', self.model, {}, 100)
                raise requests.Timeout('synthetic timeout')
            return super().chat_json(messages, **kwargs)

    app.extensions['evidence_llm_factory'] = lambda identifier: TimeoutLLM(store, identifier)
    client = app.test_client()
    response = client.post(URL, json={'section_index': 1, 'request_key': 'timeout'})
    identifier = response.json['data']['proposal_id']
    record = terminal(client, identifier)
    join_workers()
    return client, identifier, record, calls


def test_timeout_reopens_and_retries_only_saved_audit_explicitly(app):
    client, identifier, failed, calls = failed_audit(app)
    assert failed['state'] == 'failed' and failed['error_code'] == 'audit_timeout'
    assert failed['audit_recovery']['available'] is True
    assert calls == ['EVIDENCE_LEDGER_V1', 'EVIDENCE_DRAFT_V1', 'EVIDENCE_AUDIT_V1']
    store = app.extensions['evidence_proposal_store']
    original = store.read(identifier)
    again = client.get(URL + '/' + identifier).json['data']
    assert again['audit_recovery'] == failed['audit_recovery']
    recovered_calls = []

    class AuditOnly(FakeLLM):
        def chat_json(self, messages, **kwargs):
            phase = messages[0]['content'].splitlines()[0]
            recovered_calls.append(phase)
            assert phase == 'EVIDENCE_AUDIT_V1'
            return super().chat_json(messages, **kwargs)

    app.extensions['evidence_llm_factory'] = lambda new_id: AuditOnly(store, new_id)
    body = {'request_key': 'retry-once', 'recovery_digest': failed['audit_recovery']['digest']}
    response = client.post(URL + '/' + identifier + '/retry-audit', json=body)
    assert response.status_code == 202
    new_id = response.json['data']['proposal_id']
    assert new_id != identifier
    recovered = terminal(client, new_id)
    assert recovered['state'] == 'ready' and recovered_calls == ['EVIDENCE_AUDIT_V1']
    assert recovered['summary_format'] == failed['summary_format'] == 'concise-linked-v1'
    assert recovered['after'] == failed['after']
    assert recovered['usage']['calls'] == failed['usage']['calls']
    assert store.read(identifier) == original
    assert client.post(URL + '/' + identifier + '/retry-audit', json=body).json['data']['proposal_id'] == new_id
    assert recovered_calls == ['EVIDENCE_AUDIT_V1']
    join_workers()
    assert client.post(URL + '/' + new_id + '/accept', json={'proposal_digest': recovered['proposal_digest']}).status_code == 200


def test_selection_is_digest_bound_and_revalidated_at_acceptance(app):
    from app.services.proposal_store import proposal_digest
    client = app.test_client()
    result = client.post(URL, json={'section_index': 1, 'request_key': 'selected',
        'summary_selection': 'The hearing is Thursday.'})
    record = terminal(client, result.json['data']['proposal_id'])
    join_workers()
    store = app.extensions['evidence_proposal_store']
    digest = record['proposal_digest']
    record.pop('audit_recovery')
    record['summary_selection'] = 'Other issues remain open.'
    assert proposal_digest(record) != digest
    record['proposal_digest'] = proposal_digest(record)
    store._file(record['proposal_id']).write_text(json.dumps(record))
    rejected = client.post(URL + '/' + record['proposal_id'] + '/accept', json={'proposal_digest': record['proposal_digest']})
    assert rejected.status_code == 409 and rejected.json['error'] == 'summary_scope_mismatch'


def test_ambiguous_selection_does_not_authorize_summary_changes(app):
    parent = ReportManager.get_report('report_root')
    parent.outline.summary = 'Repeated. Repeated.'
    ReportManager.save_report(parent)
    response = app.test_client().post(URL, json={'section_index': 1, 'request_key': 'ambiguous', 'summary_selection': 'Repeated.'})
    assert response.status_code == 400
    assert response.json['error'] == 'missing_or_ambiguous_summary_target'


def test_unmapped_summary_requires_selection_before_any_model_call(app):
    parent = ReportManager.get_report('report_root')
    parent.outline.summary = 'A paraphrased forecast that needs source review.'
    ReportManager.save_report(parent)
    app.extensions['evidence_llm_factory'] = lambda _: pytest.fail('unmapped summary reached model')
    response = app.test_client().post(URL, json={'section_index': 1, 'request_key': 'unmapped'})
    assert response.status_code == 400 and response.json['error'] == 'summary_selection_required'


@pytest.mark.parametrize('change,expected', [('parent', 'stale_parent'), ('sources', 'stale_sources'), ('digest', 'audit_checkpoint_changed')])
def test_retry_revalidates_before_scheduling_a_model(app, change, expected):
    client, identifier, failed, _ = failed_audit(app)
    store = app.extensions['evidence_proposal_store']
    original = store.read(identifier)
    if change == 'parent':
        parent = ReportManager.get_report('report_root')
        parent.outline.summary += ' Changed.'
        ReportManager.save_report(parent)
    if change == 'sources':
        app.extensions['neo4j_storage'].get_source_chunks = lambda **kwargs: []
    app.extensions['evidence_llm_factory'] = lambda _: pytest.fail('stale checkpoint reached model')
    response = client.post(URL + '/' + identifier + '/retry-audit', json={'request_key': 'retry',
        'recovery_digest': 'wrong' if change == 'digest' else failed['audit_recovery']['digest']})
    assert response.status_code == 409 and response.json['error'] == expected
    assert store.read(identifier) == original


def test_legacy_timeout_can_recover_but_corrupt_snapshot_cannot(app):
    client, identifier, failed, _ = failed_audit(app)
    store = app.extensions['evidence_proposal_store']
    original = store.read(identifier)
    original.update(error_code='drafting_unavailable')
    original.pop('diagnostics_digest')
    store._file(identifier).write_text(json.dumps(original))
    assert client.get(URL + '/' + identifier).json['data']['audit_recovery']['available']
    store._file(identifier, 'ledger').write_text('[]')
    assert not client.get(URL + '/' + identifier).json['data']['audit_recovery']['available']


def test_retry_preserves_refusal_when_failure_cleanup_is_busy(app, monkeypatch):
    from app.services.proposal_store import ProposalError
    client, identifier, _, _ = failed_audit(app)
    store = app.extensions['evidence_proposal_store']
    app.extensions['evidence_llm_factory'] = lambda _: pytest.fail('refused retry reached model')
    def busy_cleanup(*args, **kwargs):
        raise ProposalError('state_busy')
    monkeypatch.setattr(store, 'update', busy_cleanup)
    response = client.post(URL + '/' + identifier + '/retry-audit',
        json={'request_key': 'refused-retry', 'recovery_digest': 'wrong'})
    assert response.status_code == 409
    assert response.json['error'] == 'audit_checkpoint_changed'


def test_recovery_retains_adverse_judgments_from_a_timed_out_structural_correction(app):
    store = app.extensions['evidence_proposal_store']
    count = 0
    class StructuralTimeout(FakeLLM):
        def chat_json(self, messages, **kwargs):
            nonlocal count
            result = super().chat_json(messages, **kwargs)
            if messages[0]['content'].startswith('EVIDENCE_AUDIT_V1'):
                count += 1
                if count == 2:
                    raise requests.Timeout('synthetic correction timeout')
                result['summary_reviews'] = []
                result['summary_consistent'] = False
                result['summary_assessment'] = {'outcome': 'contradicted', 'detail': 'Synthetic adverse judgment.', 'evidence_ids': ['episode:one']}
            return result
    app.extensions['evidence_llm_factory'] = lambda identifier: StructuralTimeout(store, identifier)
    client = app.test_client()
    created = client.post(URL, json={'section_index': 1, 'request_key': 'structural'})
    identifier = created.json['data']['proposal_id']
    record = terminal(client, identifier)
    join_workers()
    assert record['audit_recovery']['available'] and count == 2
    app.extensions['evidence_llm_factory'] = lambda identifier: FakeLLM(store, identifier)
    result = client.post(URL + '/' + identifier + '/retry-audit', json={'request_key': 'structural-retry', 'recovery_digest': record['audit_recovery']['digest']})
    recovered = terminal(client, result.json['data']['proposal_id'])
    assert recovered['state'] == 'blocked'
    assert 'audit_adverse_judgment_changed' in {f['code'] for f in recovered['findings']}


def test_retry_rejects_a_changed_model_without_request(app):
    client, identifier, failed, _ = failed_audit(app)
    store = app.extensions['evidence_proposal_store']
    class ChangedModel(FakeLLM):
        model = 'different'
        def chat_json(self, *args, **kwargs):
            pytest.fail('changed model reached transport')
    app.extensions['evidence_llm_factory'] = lambda identifier: ChangedModel(store, identifier)
    result = client.post(URL + '/' + identifier + '/retry-audit', json={'request_key': 'changed', 'recovery_digest': failed['audit_recovery']['digest']})
    recovered = terminal(client, result.json['data']['proposal_id'])
    assert recovered['state'] == 'blocked' and recovered['findings'][0]['code'] == 'audit_model_changed'


def test_deadline_after_correction_replays_both_saved_audits_and_cannot_erase_adverse_result(app):
    store = app.extensions['evidence_proposal_store']
    audits = 0
    class DeadlineAfterCorrection(FakeLLM):
        def chat_json(self, messages, **kwargs):
            nonlocal audits
            result = super().chat_json(messages, **kwargs)
            if messages[0]['content'].startswith('EVIDENCE_AUDIT_V1'):
                audits += 1
                if audits == 1:
                    result['summary_reviews'] = []
                    result['summary_consistent'] = False
                    result['summary_assessment'] = {'outcome': 'contradicted', 'detail': 'Earlier adverse judgment.', 'evidence_ids': ['episode:one']}
                else:
                    kwargs['usage_callback'].__self__.deadline = 0
            return result
    app.extensions['evidence_llm_factory'] = lambda identifier: DeadlineAfterCorrection(store, identifier)
    client = app.test_client()
    created = client.post(URL, json={'section_index': 1, 'request_key': 'late-correction'})
    identifier = created.json['data']['proposal_id']
    failed = terminal(client, identifier)
    join_workers()
    assert failed['error_code'] == 'deadline_exceeded' and failed['audit_recovery']['available']
    class NoMoreCalls(FakeLLM):
        def chat_json(self, *args, **kwargs):
            pytest.fail('completed audit responses must be replayed without another request')
    app.extensions['evidence_llm_factory'] = lambda identifier: NoMoreCalls(store, identifier)
    result = client.post(URL + '/' + identifier + '/retry-audit', json={'request_key': 'late-retry', 'recovery_digest': failed['audit_recovery']['digest']})
    recovered = terminal(client, result.json['data']['proposal_id'])
    assert recovered['state'] == 'blocked' and audits == 2
    assert 'audit_adverse_judgment_changed' in {f['code'] for f in recovered['findings']}
