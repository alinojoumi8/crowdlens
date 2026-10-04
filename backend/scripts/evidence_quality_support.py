"""Synthetic structural evaluation helpers; never call a provider or infer labels."""
import copy
import hashlib
import json
from pathlib import Path
import time

CORPUS_ROOT = Path(__file__).resolve().parents[1] / 'tests/fixtures/evidence_quality/v1'


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def load_corpus(split='holdout'):
    if split not in {'development', 'holdout'}:
        raise ValueError('unknown_split')
    manifest = json.loads((CORPUS_ROOT / 'manifest.json').read_text())
    for name, digest in manifest['files_sha256'].items():
        if sha256((CORPUS_ROOT / name).read_bytes()) != digest:
            raise ValueError('fixture_hash_mismatch:' + name)
    rows = json.loads((CORPUS_ROOT / split / 'cases.json').read_text())['cases']
    for row in rows:
        for source in row['sources']:
            if sha256(source['data'].encode()) != source['fixture_text_sha256']:
                raise ValueError('source_hash_mismatch:' + source['uuid'])
    return rows


def artifact_hashes(directory):
    return {str(path.relative_to(directory)): sha256(path.read_bytes())
            for path in sorted(directory.rglob('*')) if path.is_file()}


class FixtureStorage:
    """Returns all supplied rows so application admission, not this fake, isolates scope."""
    def __init__(self, rows):
        self.rows = copy.deepcopy(rows)

    def get_source_chunks(self, **scope):
        return copy.deepcopy(self.rows)


class ScriptedDraft:
    model = 'synthetic-scripted-draft-v1'

    def __init__(self, fixture):
        self.fixture, self.calls = fixture, []

    def chat_json(self, messages, **kwargs):
        from app.services.evidence_drafting import LEDGER_PROMPT, DRAFT_PROMPT, AUDIT_PROMPT
        prompt = messages[0]['content']
        payload = json.loads(messages[1]['content'])
        self.calls.append({'phase': prompt.splitlines()[0], 'prompt_sha256': sha256(prompt.encode()),
                           'request_max_retries': kwargs.get('request_max_retries'),
                           'request_timeout': kwargs.get('request_timeout')})
        assert kwargs['request_max_retries'] == 0
        assert 0 < kwargs['request_timeout'] <= 60
        assert kwargs['temperature'] == 0
        if prompt == LEDGER_PROMPT:
            result = {'claims': copy.deepcopy(self.fixture['stub_claims']), 'gaps': self.fixture['stub_gaps']}
        elif prompt == DRAFT_PROMPT:
            result = {'paragraphs': [{'text': claim['text'], 'kind': claim['kind'],
                                      'claim_ids': [claim['claim_id']]} for claim in payload['ledger']],
                      'summary_edits': []}
        elif prompt == AUDIT_PROMPT:
            result = {'findings': [], 'covered_paragraph_indices': list(range(len(payload['paragraphs']))),
                      'covered_summary_edit_indices': [], 'summary_unchanged_consistent': True,
                      'claim_reviews': [{'claim_id': c['claim_id'], 'outcome': 'supported',
                          'evidence_ids': c.get('citation_ids', []),
                          'detail': 'Synthetic positive model judgment for structural testing only; not a quality label.'}
                          for c in payload['ledger']]}
        else:
            raise AssertionError('unknown_model_phase')
        # The provider/model explicitly identifies a substitute. Token counts remain unknown.
        kwargs['usage_callback']('deterministic_substitute', self.model, {}, 0)
        return result


def prepare_proposal(fixture, root, monkeypatch):
    from app.models.task import TaskManager
    from app.services.evidence_drafting import EvidenceDraftingService
    from app.services.proposal_store import ProposalStore
    from app.services.report_agent import Report, ReportManager, ReportOutline, ReportSection, ReportStatus
    from app.utils.draft_budget import DraftBudget

    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(root))
    monkeypatch.setattr(TaskManager, '_repository', None)
    scope = fixture['scope']
    parent = Report('report_root', 'eq_sim_' + fixture['id'], scope['graph_id'], 'Synthetic parcel review',
                    ReportStatus.NEEDS_REVIEW, report_mode='legal_case', created_at='2026-10-02T00:00:00',
                    source_grounding=copy.deepcopy(scope), outline=ReportOutline('Synthetic parcel report',
                    fixture['summary'], [ReportSection(**fixture['section']),
                    ReportSection('Unselected section', content='This synthetic section stays unchanged.')]))
    ReportManager.save_report(parent)
    before_hashes = artifact_hashes(root / parent.report_id)
    store, storage, llm = ProposalStore(root), FixtureStorage(fixture['sources']), ScriptedDraft(fixture)
    record, lease = store.admit(parent.report_id, 'eq_' + fixture['id'], 'eq_body_v1')
    store.update(record['proposal_id'], {'queued'}, {'state': 'running', 'scope': scope, 'section_index': 1})
    started = time.monotonic()
    try:
        result = EvidenceDraftingService(storage, llm, store).generate(
            record['proposal_id'], parent.to_dict(), budget=DraftBudget())
    finally:
        lease.close()
    return {'parent': parent, 'store': store, 'storage': storage, 'llm': llm, 'result': result,
            'before_hashes': before_hashes, 'elapsed_seconds': time.monotonic() - started}
