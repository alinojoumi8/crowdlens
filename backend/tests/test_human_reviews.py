import copy
import hashlib
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pytest
from flask import Flask

from app.services.human_reviews import HumanReviewStore
from app.services.proposal_store import ProposalError, ProposalStore
from scripts.evidence_quality_reviews import import_reviews


@pytest.fixture
def material(tmp_path):
    proposals = ProposalStore(tmp_path)
    record, lease = proposals.admit('report_review_fixture', 'fixture', 'fixture')
    identifier = record['proposal_id']
    proposals.update(identifier, {'queued'}, {'state': 'running'})
    record = proposals.finish(identifier, dict(state='ready', section_index=1,
        before={'section': 'Original.', 'summary': 'Original summary.'},
        after={'section': 'Alex reported Friday.', 'summary': 'Friday was reported.'},
        ledger=[dict(claim_id='claim_1', kind='attributed_allegation', text='Alex reported Friday.',
                     attribution='Alex', citation_ids=['source_1'], premise_claim_ids=[])],
        sources=[dict(evidence_id='source_1', window='Alex: Friday.', source_hash='a'*64,
                      window_hash='b'*64, locator={'page': 1}, document_id='document_1')]))
    lease.close()
    parent = tmp_path/'parent.md'
    parent.write_text('Immutable original report')
    return proposals, record, parent


def form_for(store, record, reviewer='synthetic-reviewer-one', support=None):
    form = store.view(record)['blank_form']
    form.update(reviewer_id=reviewer, reviewer_kind='human', notes='Synthetic test only')
    if support:
        form['claims'][0].update(support=support, rationale='The retained quotation explicitly attributes this date.')
    return form


def test_persists_partial_reviews_without_mutating_proposal_or_parent(material):
    proposals, record, parent = material
    before = proposals._file(record['proposal_id']).read_bytes(), parent.read_bytes()
    store = HumanReviewStore(proposals)
    form = form_for(store, record, support='supported')
    store.save(record, form, 0)
    loaded = HumanReviewStore(ProposalStore(proposals.root)).view(record)
    assert loaded['reviews'][0]['form']['claims'][0]['support'] == 'supported'
    assert loaded['reviews'][0]['form']['claims'][0]['attribution_correct'] is None
    assert loaded['reviews'][0]['form']['review_seconds'] is None
    assert loaded['assessment']['status'] == 'PARTIAL'
    assert loaded['assessment']['reviewed_packets'] == 0
    assert before == (proposals._file(record['proposal_id']).read_bytes(), parent.read_bytes())
    assert (proposals.root/'.human-reviews.sqlite3').stat().st_mode & 0o777 == 0o600


def test_disagreement_history_version_conflict_and_export_roundtrip(material, tmp_path):
    proposals, record, _ = material
    store = HumanReviewStore(proposals)
    a = form_for(store, record, support='supported')
    a.update(reference_facts=[{'fact_id':'fact_1','text':'The statement is attributed to Alex.'}],
             omitted_reference_fact_ids=['fact_1'], review_seconds=24.5)
    store.save(record, a, 0)
    b = form_for(store, record, reviewer='synthetic-reviewer-two', support='unsupported')
    result = store.save(record, b, 0)
    assert len(result['assessment']['disagreements']) == 1
    with pytest.raises(ProposalError, match='review_version_conflict'):
        store.save(record, a, 0)
    a['claims'][0]['attribution_correct'] = True
    result = store.save(record, a, 1)
    assert len(result['history']) == 3
    assert len(result['reviews']) == 2
    with zipfile.ZipFile(store.export(record)) as archive:
        directory = tmp_path/'export'
        archive.extractall(directory)
    forms = [json.loads(line) for line in (directory/'reviews.jsonl').read_text().splitlines()]
    scored = import_reviews(directory/'reviewer', forms)
    assert scored == result['assessment']
    assert len(json.loads((directory/'history.json').read_text())) == 3
    assert scored['measured_review_seconds']['total'] == 24.5
    assert scored['omissions_per_reference_fact_review']['numerator'] == 1


@pytest.mark.parametrize('mutation,code', [
    (lambda f: f.update(packet_sha256='wrong'), 'review_content_changed'),
    (lambda f: f.update(reviewer_kind='ai'), 'human_provenance_required'),
    (lambda f: f['claims'][0].update(claim_id='unknown'), 'claim_coverage_mismatch'),
    (lambda f: f['claims'][0].update(support='supported', rationale=None), 'label_rationale_required'),
    (lambda f: f.update(review_seconds=-1), 'invalid_measured_review_time'),
    (lambda f: f.update(omitted_reference_fact_ids=['fact']), 'omissions_require_reference_assessment'),
])
def test_rejects_bad_or_stale_judgments(material, mutation, code):
    proposals, record, _ = material
    store = HumanReviewStore(proposals)
    form = form_for(store, record)
    mutation(form)
    with pytest.raises(ProposalError, match=code):
        store.save(record, form, 0)
    assert store.view(record)['reviews'] == []


def test_changed_content_never_inherits_ratings(material):
    proposals, record, _ = material
    store = HumanReviewStore(proposals)
    form = form_for(store, record, support='supported')
    store.save(record, form, 0)
    changed = copy.deepcopy(record)
    changed['sources'][0]['window'] = 'Different source.'
    with pytest.raises(ProposalError, match='review_content_changed'):
        store.view(changed)
    from app.services.proposal_store import proposal_digest
    changed['proposal_digest'] = proposal_digest(changed)
    assert store.view(changed)['reviews'] == []
    with pytest.raises(ProposalError, match='review_content_changed'):
        store.save(changed, form, 0)


def test_concurrent_edits_cannot_overwrite_another_saved_version(material):
    proposals, record, _ = material
    form = form_for(HumanReviewStore(proposals), record, support='supported')
    def save(_):
        try:
            HumanReviewStore(ProposalStore(proposals.root)).save(record, form, 0)
            return 'saved'
        except ProposalError as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, range(2))) == ['review_version_conflict', 'saved']
    assert len(HumanReviewStore(proposals).view(record)['history']) == 1


def test_api_persistence_export_and_report_binding(material):
    from app.api import report_bp
    proposals, record, _ = material
    app = Flask(__name__)
    app.extensions['evidence_proposal_store'] = proposals
    app.register_blueprint(report_bp, url_prefix='/api/report')
    client = app.test_client()
    base = f"/api/report/{record['parent_report_id']}/evidence-proposals/{record['proposal_id']}/human-reviews"
    form = client.get(base).json['data']['blank_form']
    form.update(reviewer_id='synthetic-ui-fixture', reviewer_kind='human')
    assert client.post(base,json={'form':form,'expected_version':0}).status_code == 200
    assert client.get(base).json['data']['assessment']['reviewed_packets'] == 0
    assert client.get(base+'/export').mimetype == 'application/zip'
    assert client.get(base.replace(record['parent_report_id'], 'report_other')).status_code == 404


def test_saved_proposals_are_discoverable_without_provider_calls(material):
    from app.api import report_bp
    proposals, record, _ = material
    app = Flask(__name__)
    app.extensions['evidence_proposal_store'] = proposals
    app.register_blueprint(report_bp, url_prefix='/api/report')
    client = app.test_client()
    rows = client.get('/api/report/report_review_fixture/evidence-proposals').json['data']
    assert rows == [{key:record.get(key) for key in ('proposal_id','section_index','state','created_at')}]
    assert client.get('/api/report/report_other/evidence-proposals').json['data'] == []
