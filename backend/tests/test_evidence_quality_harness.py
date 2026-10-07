"""Meaningful evaluator regression checks: nulls, blocked work and provenance."""
import copy
import json
import pytest

from scripts.evidence_quality_reviews import export_packets, import_reviews
from scripts.evaluate_evidence_quality import summarize_runs


def test_failed_and_skipped_runs_cannot_be_scored_as_success():
    runs = [{'exit_code': 1, 'cases': [{'id': 'a', 'status': 'failed', 'properties': {}},
            {'id': 'b', 'status': 'skipped', 'properties': {}}]},
            {'exit_code': 0, 'cases': [{'id': 'a', 'status': 'passed', 'properties': {}}]}]
    result = summarize_runs(runs)
    assert result['status'] == 'PARTIAL'
    assert result['first_attempt_success']['rate'] == 0
    assert result['pass_at_k']['rate'] == .5
    assert result['pass_power_k']['rate'] == 0
    assert result['missing_test_observations'] == 1
    assert result['model_quality']['unsupported_claim_rate'] is None
    empty = summarize_runs([{'exit_code': 0, 'cases': []}])
    assert empty['status'] == 'PARTIAL'
    assert empty['first_attempt_success']['rate'] is None


@pytest.fixture
def review_material(tmp_path):
    from scripts.evidence_quality_support import load_corpus
    fixture = load_corpus('holdout')[0]
    source = fixture['sources'][0]
    observation = {'case_id': fixture['id'], 'sources': [{'evidence_id': 'episode:' + source['uuid'],
        'excerpt': source['data'], 'source_hash': source['fixture_text_sha256'], 'origin': source['origin'], 'locator': {}}],
        'claims': fixture['stub_claims'], 'after': {'section': fixture['stub_claims'][0]['text'], 'summary': ''}}
    export_packets(tmp_path, [fixture], [observation])
    row = json.loads((tmp_path / 'reviewer/blank-review-forms.jsonl').read_text())
    return tmp_path / 'reviewer', row


def test_blank_review_forms_preserve_null_quality_and_time(review_material):
    path, row = review_material
    result = import_reviews(path, [row])
    assert result['status'] == 'PENDING'
    assert result['review_rows'] == 0 and result['pending_forms'] == 1
    assert result['unsupported_claims_per_review'] == {'numerator': 0, 'denominator': 0, 'rate': None}
    assert result['measured_review_seconds']['total'] is None
    assert result['omissions_per_reference_fact_review']['rate'] is None
    packet = json.loads(next(path.glob('packet_*.json')).read_text())
    assert 'direct_support' not in json.dumps(packet)
    assert not {'expected', 'model', 'category', 'candidate_origin'} & set(packet)


def filled(row, reviewer='synthetic-test-human'):
    row = copy.deepcopy(row)
    row.update(reviewer_id=reviewer, reviewer_kind='human', reviewed_at='2026-10-02T00:00:00Z')
    row['claims'][0].update(support='supported', rationale='Synthetic importer unit-test label; not a real review.')
    return row


@pytest.mark.parametrize('change,error', [({'reviewer_kind': 'ai'}, 'human_provenance'),
    ({'reviewer_id': None}, 'reviewer_identity'), ({'packet_sha256': 'changed'}, 'packet_hash'),
    ({'omitted_reference_fact_ids': ['fact-1']}, 'omissions_require'),
    ({'review_seconds': -1}, 'invalid_measured')])
def test_import_rejects_untrusted_or_incomplete_labels(review_material, change, error):
    path, row = review_material
    row = filled(row)
    row.update(change)
    with pytest.raises(ValueError, match=error):
        import_reviews(path, [row])


def test_disagreement_is_preserved_instead_of_voted_away(review_material):
    path, blank = review_material
    first, second = filled(blank, 'synthetic-test-A'), filled(blank, 'synthetic-test-B')
    second['claims'][0]['support'] = 'unsupported'
    result = import_reviews(path, [first, second])
    assert result['review_rows'] == 2
    assert result['unsupported_claims_per_review']['rate'] == .5
    assert len(result['disagreements']) == 1
    assert len(result['disagreements'][0]['judgments']) == 2
    assert result['real_model_quality'] is None
    with pytest.raises(ValueError, match='duplicate_reviewer'):
        import_reviews(path, [first, first])


def test_identity_without_any_labels_is_not_a_reviewed_packet(review_material):
    path, row = review_material
    row.update(reviewer_id='synthetic-test-A', reviewer_kind='human', reviewed_at='2026-10-02T00:00:00Z')
    result = import_reviews(path, [row])
    assert result['status'] == 'PENDING'
    assert result['reviewed_packets'] == 0
    assert result['review_rows'] == 0 and result['pending_forms'] == 1
    assert result['unsupported_claims_per_review']['rate'] is None


def test_import_rejects_missing_claim_schema_fields(review_material):
    path, row = review_material
    row = filled(row)
    del row['claims'][0]['citation_support_correct']
    with pytest.raises(ValueError, match='missing_claim_fields'):
        import_reviews(path, [row])


def test_partial_labels_remain_partial_until_all_claim_dimensions_are_assessed(review_material):
    path, row = review_material
    row = filled(row)
    partial = import_reviews(path, [row])
    assert partial['status'] == 'PARTIAL'
    assert partial['reviewed_packets'] == 0
    assert partial['review_rows'] == 1
    row['claims'][0].update(attribution_correct=True, citation_support_correct=True)
    assessed = import_reviews(path, [row])
    assert assessed['status'] == 'LABELS_IMPORTED'
    assert assessed['reviewed_packets'] == 1
