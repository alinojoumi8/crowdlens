"""Frozen synthetic v1 checks measure structural contracts, never model quality."""
import copy
import json

import pytest

from scripts.evidence_quality_support import artifact_hashes, load_corpus, prepare_proposal

CASES = load_corpus('development') + load_corpus('holdout')


@pytest.mark.parametrize('fixture', CASES, ids=lambda row: row['split'] + '-' + row['id'])
def test_frozen_source_and_revision_contract(fixture, tmp_path, monkeypatch, record_property):
    from app.services.claim_ledger import validate_source
    from app.services.proposal_store import ProposalError
    from app.services.report_agent import ReportManager, ReportStatus
    from app.services.report_revisions import ReportRevisionService

    run = prepare_proposal(fixture, tmp_path, monkeypatch)
    result, parent, llm = run['result'], run['parent'], run['llm']
    observation = {'case_id': fixture['id'], 'split': fixture['split'], 'state': result['state'],
                   'finding_codes': sorted(f['code'] for f in result.get('findings', [])),
                   'selected_source_ids': sorted(s['evidence_id'] for s in result.get('sources', [])),
                   'substitute_calls': len(llm.calls), 'real_model_calls': 0,
                   'elapsed_seconds': run['elapsed_seconds'], 'claims': result.get('ledger', []),
                   'sources': result.get('sources', []), 'after': result.get('after'),
                   'parent_artifact_hashes_before': run['before_hashes'], 'calls': llm.calls,
                   'quality_labels': None, 'human_review_seconds': None}
    # Persist the observed result before assertions so failures retain useful evidence.
    record_property('corpus_observation', json.dumps(observation, sort_keys=True))
    expected = fixture['expected']
    assert result['state'] == expected['state']
    assert observation['finding_codes'] == sorted(expected['finding_codes'])
    assert observation['selected_source_ids'] == sorted(expected['selected_source_ids'])
    assert len(llm.calls) == expected['stub_calls']
    assert set(result) >= {'proposal_id', 'state', 'scope', 'findings', 'sources', 'usage', 'timing'}
    for source in result['sources']:
        assert validate_source(source, fixture['scope']) is None
        assert source['origin'] == 'source_document'
    for claim in result.get('ledger', []):
        if result['state'] == 'ready':
            assert set(claim['citation_ids']) <= set(observation['selected_source_ids'])
    service = ReportRevisionService(run['store'], storage=run['storage'])
    if result['state'] == 'blocked':
        with pytest.raises(ProposalError):
            service.accept(parent.report_id, result['proposal_id'], result['proposal_digest'])
        assert not (tmp_path / result['revision_report_id']).exists()
    else:
        child = service.accept(parent.report_id, result['proposal_id'], result['proposal_digest'])
        assert child.report_id != parent.report_id
        assert child.revision['immutable'] is True
        assert child.revision['parent_report_id'] == parent.report_id
        assert child.status == ReportStatus.NEEDS_REVIEW
        assert child.outline.sections[1] == parent.outline.sections[1]
        reopened = ReportManager.get_report(child.report_id)
        assert reopened.to_dict() == child.to_dict()
        assert service.accept(parent.report_id, result['proposal_id'], result['proposal_digest']).report_id == child.report_id
        assert len(service.revisions(parent.report_id)) == 2
        ReportManager.apply_quality_status(reopened)
        assert reopened.status == ReportStatus.NEEDS_REVIEW
        with pytest.raises(ProposalError, match='immutable_revision'):
            ReportManager.save_report(reopened)
    after_hashes = artifact_hashes(tmp_path / parent.report_id)
    record_property('parent_artifact_hashes_after', json.dumps(after_hashes, sort_keys=True))
    assert after_hashes == run['before_hashes']


def test_development_and_holdout_have_disjoint_identities():
    def identities(rows):
        return {value for row in rows for value in [*row['scope'].values(),
                *[source[key] for source in row['sources'] for key in ('document_id', 'uuid')]]}
    assert identities(load_corpus('development')).isdisjoint(identities(load_corpus('holdout')))


@pytest.mark.parametrize('field,value', [('graph_id', 'foreign'), ('case_id', 'foreign'),
    ('case_version_id', 'wrong-version'), ('origin', 'generated_report'),
    ('source_hash', 'tampered'), ('window_hash', 'tampered'), ('window_start', -1)])
def test_tampered_citation_provenance_is_invalid(field, value, tmp_path, monkeypatch):
    from app.services.claim_ledger import validate_source
    fixture = load_corpus('development')[0]
    run = prepare_proposal(fixture, tmp_path, monkeypatch)
    source = copy.deepcopy(run['result']['sources'][0])
    source[field] = value
    assert validate_source(source, fixture['scope']) is not None
