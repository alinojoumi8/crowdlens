"""Recovery-first publication of immutable evidence report revisions."""
import copy
from functools import wraps
import json
import os
from pathlib import Path
import shutil
import tempfile

from .claim_ledger import canonical_digest, validate_ledger, validate_paragraphs, render_paragraphs, apply_summary_edits
from .proposal_store import ProposalStore, ProposalError, atomic_json, fsync_directory, now, proposal_digest
from .source_retrieval import freeze_sources


def guard_report_generation(function):
    @wraps(function)
    def guarded(self, progress_callback=None, report_id=None):
        from .report_agent import ReportManager
        import uuid
        report_id = report_id or 'report_' + uuid.uuid4().hex[:12]
        store = ProposalStore(ReportManager._get_reports_dir())
        with store.operation(report_id):
            ReportManager.assert_report_writable(report_id)
            return function(self, progress_callback=progress_callback, report_id=report_id)
    return guarded


def guard_report_mutation(function):
    @wraps(function)
    def guarded(self, report, *args, **kwargs):
        from .report_agent import ReportManager
        if report.revision.get('immutable'):
            raise ProposalError('immutable_revision')
        store = ProposalStore(ReportManager._get_reports_dir())
        with store.operation(report.report_id):
            current = ReportManager.get_report(report.report_id)
            if current and current.revision.get('immutable'):
                raise ProposalError('immutable_revision')
            if store.path('.evidence-tombstones', report.report_id + '.json').exists():
                raise ProposalError('report_deleted', 410)
            return function(self, current or report, *args, **kwargs)
    return guarded


def report_content_digest(report):
    value = report.to_dict() if hasattr(report, 'to_dict') else copy.deepcopy(report)
    value['revision'] = dict(value.get('revision') or {})
    value['revision'].pop('content_digest', None)
    return canonical_digest(value)


class ReportRevisionService:
    def __init__(self, store, *, storage, report_manager=None):
        from .report_agent import ReportManager
        self.store, self.storage, self.manager = store, storage, report_manager or ReportManager

    def _recover(self, record):
        target = record['revision_report_id']
        if self.store.path('.evidence-tombstones', target + '.json').exists():
            raise ProposalError('revision_deleted', 410)
        target_dir = self.store.path(target)
        if not target_dir.exists():
            if record['state'] == 'accepted':
                raise ProposalError('revision_missing', 410)
            return None
        revision = self.manager.get_report(target)
        metadata = revision.revision if revision else {}
        if (not revision or metadata.get('proposal_id') != record['proposal_id']
                or metadata.get('proposal_digest') != record['proposal_digest']
                or metadata.get('content_digest') != report_content_digest(revision)):
            raise ProposalError('revision_conflict')
        # Every published artifact is sealed, not just the metadata view.
        try:
            manifest = json.loads(self.store.path(target, 'manifest.json').read_text())
            import hashlib
            for name, digest in manifest.items():
                if '/' in name or name.startswith('.'):
                    raise ProposalError('revision_conflict')
                data = self.store.path(target, name).read_bytes()
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ProposalError('revision_conflict')
        except (OSError, ValueError):
            raise ProposalError('revision_conflict')
        if record['state'] != 'accepted':
            self.store.update(record['proposal_id'], {'accepting'},
                {'state': 'accepted', 'accepted_report_id': target})
        return revision

    def accept(self, parent_report_id, proposal_id, expected_digest):
        record = self.store.get(parent_report_id, proposal_id)
        if not isinstance(expected_digest, str) or expected_digest != record.get('proposal_digest') or expected_digest != proposal_digest(record):
            raise ProposalError('proposal_digest_mismatch')
        with self.store.operation(parent_report_id), self.store.operation(record['revision_report_id']):
            record = self.store.get(parent_report_id, proposal_id)
            recovered = self._recover(record)
            if recovered:
                return recovered
            if record['state'] not in {'ready', 'accepting'} or any(f['blocking'] for f in record['findings']):
                raise ProposalError('not_acceptible')
            parent = self.manager.get_report(parent_report_id)
            if parent is None or canonical_digest(parent.to_dict()) != record['parent_digest']:
                self.store.update(proposal_id, {'ready', 'accepting'}, {'state': 'stale', 'error_code': 'stale_parent'})
                raise ProposalError('stale_parent')
            try:
                if record.get('policy') in ('evidence-draft-v15-source-completeness', 'evidence-draft-v16-staged-source-review'):
                    from .source_completeness import freeze_review_sources
                    corpus = freeze_review_sources(self.storage, record['scope'])
                else:
                    corpus = freeze_sources(self.storage.get_source_chunks(**record['scope']), record['scope'])
            except Exception:
                raise ProposalError('source_revalidation_unavailable', 503) from None
            if corpus['digest'] != record['source_digest']:
                self.store.update(proposal_id, {'ready', 'accepting'}, {'state': 'stale', 'error_code': 'stale_sources'})
                raise ProposalError('stale_sources')
            # Check the persisted frozen inputs as well as the current source corpus.
            frozen = self.store.load_snapshot(proposal_id, 'parent', record['parent_digest'])
            self.store.load_snapshot(proposal_id, 'sources', record['source_snapshot_digest'])
            ledger = self.store.load_snapshot(proposal_id, 'ledger', record['ledger_digest'])
            if record.get('policy') in ('evidence-draft-v15-source-completeness', 'evidence-draft-v16-staged-source-review'):
                from .source_completeness import source_completeness
                if record.get('policy') == 'evidence-draft-v16-staged-source-review':
                    from .staged_source_review import checked_progress
                    diagnostics = self.store.load_snapshot(proposal_id, 'diagnostics', record['diagnostics_digest'])
                    try:
                        _, coverage = checked_progress(record, corpus, require_complete=True, diagnostics=diagnostics)
                    except (ValueError, TypeError, KeyError, IndexError):
                        raise ProposalError('source_review_incomplete') from None
                else:
                    coverage = source_completeness(corpus, record['sources'])
                if not coverage['complete'] or coverage != record.get('source_completeness'):
                    raise ProposalError('source_completeness_unresolved')
            if record.get('policy') in {'focused-literal-correction-v1', 'focused-wording-correction-v2'}:
                from .focused_correction import validate_focused_record
                try:
                    validate_focused_record(record, frozen, corpus)
                except (ValueError, TypeError, KeyError):
                    raise ProposalError('invalid_proposal') from None
            else:
                if record.get('policy') in ('evidence-draft-v3-grounded-summary-scope', 'evidence-draft-v4-server-summary-target', 'evidence-draft-v5-claim-summary', 'evidence-draft-v6-conditional-extract', 'evidence-draft-v7-server-source-sentences', 'evidence-draft-v8-server-conditional-ledger', 'evidence-draft-v9-complete-pdf-pages', 'evidence-draft-v10-exact-quote-recovery', 'evidence-draft-v11-complete-claim-coverage', 'evidence-draft-v12-source-accounting', 'evidence-draft-v13-explicit-audit-targets', 'evidence-draft-v14-summary-assessment', 'evidence-draft-v15-source-completeness', 'evidence-draft-v16-staged-source-review'):
                    from .claim_ledger import summary_edit_scope, validate_summary_edit_scope
                    contract = summary_edit_scope(frozen['outline']['summary'], frozen['outline']['sections'][record['section_index'] - 1]['content'])
                    if record.get('policy') in ('evidence-draft-v14-summary-assessment', 'evidence-draft-v15-source-completeness', 'evidence-draft-v16-staged-source-review'):
                        if contract['unmapped_summary_requires_review']:
                            raise ProposalError('summary_scope_unmapped')
                        from .evidence_drafting import validate_summary_assessment
                        try:
                            validate_summary_assessment(record.get('summary_assessment'), True, record['sources'])
                        except ValueError:
                            raise ProposalError('summary_assessment_unverified') from None
                    try:
                        validate_summary_edit_scope(record['summary_edits'], contract)
                    except (ValueError, TypeError, KeyError):
                        raise ProposalError('summary_scope_mismatch') from None
                if record.get('policy') in ('evidence-draft-v7-server-source-sentences', 'evidence-draft-v8-server-conditional-ledger', 'evidence-draft-v9-complete-pdf-pages', 'evidence-draft-v10-exact-quote-recovery', 'evidence-draft-v11-complete-claim-coverage', 'evidence-draft-v12-source-accounting', 'evidence-draft-v13-explicit-audit-targets', 'evidence-draft-v14-summary-assessment', 'evidence-draft-v15-source-completeness', 'evidence-draft-v16-staged-source-review'):
                    from .conditional_extracts import build_extract_contract, resolve_extract_claims
                    try:
                        contract = build_extract_contract(record['sources'], record['scope'])
                        if record.get('extract_provenance', {}).get('contract') != contract:
                            raise ValueError('stale_source_sentence_contract')
                        resolved, _ = resolve_extract_claims(ledger, contract)
                        if resolved != ledger:
                            raise ValueError('source_sentence_text_changed')
                    except (ValueError, TypeError, KeyError, AttributeError):
                        raise ProposalError('invalid_proposal') from None
                findings = validate_ledger(ledger, record['sources'], record['scope']) + validate_paragraphs(record['paragraphs'], ledger, record['sources'])
                if record.get('policy') in ('evidence-draft-v11-complete-claim-coverage', 'evidence-draft-v12-source-accounting', 'evidence-draft-v13-explicit-audit-targets', 'evidence-draft-v14-summary-assessment', 'evidence-draft-v15-source-completeness', 'evidence-draft-v16-staged-source-review') and not findings:
                    covered = {identifier for paragraph in record['paragraphs'] for identifier in paragraph['claim_ids']}
                    if any(claim['claim_id'] not in covered for claim in ledger):
                        raise ProposalError('invalid_proposal')
                if record.get('policy') in ('evidence-draft-v12-source-accounting', 'evidence-draft-v13-explicit-audit-targets', 'evidence-draft-v14-summary-assessment', 'evidence-draft-v15-source-completeness', 'evidence-draft-v16-staged-source-review'):
                    from .source_coverage import source_coverage
                    if source_coverage(ledger, record.get('extract_provenance', {}).get('source_exclusions'), record['sources']):
                        raise ProposalError('invalid_proposal')
                if (ledger != record['ledger'] or any(f['blocking'] for f in findings)
                        or render_paragraphs(record['paragraphs'], ledger) != record['after']['section']
                        or apply_summary_edits(frozen['outline']['summary'], record['summary_edits'], ledger) != record['after']['summary']):
                    raise ProposalError('invalid_proposal')
            checked_at = now()
            revision = self._assemble(parent, record, checked_at)
            record = self.store.update(proposal_id, {'ready', 'accepting'}, {'state': 'accepting', 'source_checked_at': checked_at})
            self._publish(revision, record)
            self.store.update(proposal_id, {'accepting'}, {'state': 'accepted', 'accepted_report_id': revision.report_id})
            return revision

    def _assemble(self, parent, record, checked_at):
        from .report_agent import ReportStatus
        revision = copy.deepcopy(parent)
        revision.report_id = record['revision_report_id']
        revision.created_at = revision.completed_at = now()
        revision.status = ReportStatus.NEEDS_REVIEW
        revision.error = None
        revision.revision = {'immutable': True, 'parent_report_id': parent.report_id,
            'root_report_id': parent.revision.get('root_report_id', parent.report_id),
            'proposal_id': record['proposal_id'], 'proposal_digest': record['proposal_digest'],
            'accepted_at': now(), 'section_index': record['section_index'],
            'inherited_forecast': True, 'source_checked_at': checked_at,
            'inherited_section_indices': [i for i in range(1, len(parent.outline.sections)+1) if i != record['section_index']],
            'summary_edits': record['summary_edits'], 'source_digest': record['source_digest']}
        if record.get('policy') in {'focused-literal-correction-v1', 'focused-wording-correction-v2'}:
            revision.revision['focused_correction'] = record['focused_correction']
            revision.revision['review_scope'] = record['limitations'][0]
        section = revision.outline.sections[record['section_index'] - 1]
        section.content = record['after']['section']
        section.claim_ledger = record['ledger']
        section.evidence_cards = record['sources']
        section.claims = [{**c, **c['scope'], 'evidence_ids': c.get('citation_ids', [])} for c in record['ledger']]
        section.claim_checks = [check for c in record['ledger'] for check in c['checks']]
        section.claim_check_hash = canonical_digest(section.content)
        revision.outline.summary = record['after']['summary']
        if record['summary_edits']:
            # Retain only checks about unchanged summary text; their origin stays recorded.
            revision.outline.summary_claims = []
            revision.outline.summary_claim_checks = [check for check in parent.outline.summary_claim_checks
                if check.get('claim_text') and check['claim_text'] in revision.outline.summary
                and not any(check['claim_text'] in edit['old_text'] for edit in record['summary_edits'])]
            revision.outline.summary_claim_check_hash = ''
        revision.claim_checks = [dict(c, section_title=s.title) for s in revision.outline.sections for c in s.claim_checks]
        revision.markdown_content = revision.outline.to_markdown()
        if revision.forecast:
            from .forecasting import forecast_to_markdown
            revision.markdown_content = forecast_to_markdown(revision.forecast) + '\n\n' + revision.markdown_content
        from .report_semantics import proposal_review_findings
        revision.revision['review_findings'] = proposal_review_findings(record)
        revision.validation_issues = self.manager.validate_report_output(revision)
        if any(issue.get('blocking') for issue in revision.validation_issues):
            raise ProposalError('report_validation_failed')
        revision.quality_score = self.manager.evaluate_report_quality(revision)
        revision.revision['content_digest'] = report_content_digest(revision)
        return revision

    def _publish(self, revision, record):
        import hashlib
        staging_root = self.store.path('.evidence-staging')
        stage = Path(tempfile.mkdtemp(prefix=revision.report_id + '-', dir=staging_root))
        try:
            documents = {'meta.json': revision.to_dict(), 'outline.json': revision.outline.to_dict(),
                         'ledger.json': record['ledger'], 'provenance.json': record,
                         'progress.json': {'status': 'needs_review', 'progress': 100, 'message': 'Revision saved; review required.'}}
            for name, value in documents.items():
                atomic_json(stage / name, value)
            texts = {'full_report.md': revision.markdown_content}
            texts.update({f'section_{i:02}.md': section.to_markdown() for i, section in enumerate(revision.outline.sections, 1)})
            for name, value in texts.items():
                with (stage / name).open('w', encoding='utf-8') as stream:
                    stream.write(value); stream.flush(); os.fsync(stream.fileno())
            manifest = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in stage.iterdir()}
            atomic_json(stage / 'manifest.json', manifest)
            fsync_directory(stage)
            target = self.store.path(revision.report_id)
            if target.exists():
                raise ProposalError('revision_conflict')
            os.rename(stage, target)
            fsync_directory(self.store.root)
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    def reject(self, parent_report_id, proposal_id):
        record = self.store.get(parent_report_id, proposal_id)
        # Running workers hold the parent lease; rejection only fences their state.
        if self.store.path(record['revision_report_id']).exists() or record['state'] in {'accepted', 'accepting'}:
            with self.store.operation(parent_report_id), self.store.operation(record['revision_report_id']):
                current = self.store.get(parent_report_id, proposal_id)
                if not self._recover(current):
                    # Only abandon a pre-publication save while holding both leases.
                    return self.store.update(proposal_id, {'accepting'}, {'state': 'rejected'})
            raise ProposalError('already_accepted')
        return self.store.reject(parent_report_id, proposal_id)

    def revisions(self, report_id):
        self.store.identifier(report_id)
        report = self.manager.get_report(report_id)
        if not report:
            raise ProposalError('not_found', 404)
        root_id = report.revision.get('root_report_id', report_id)
        return [{'report_id': item.report_id, 'created_at': item.created_at, 'status': item.status.value, 'revision': item.revision}
                for item in self.manager.list_reports(simulation_id=report.simulation_id, limit=None)
                if item.report_id == root_id or item.revision.get('root_report_id') == root_id]

    def delete(self, report_id):
        self.store.identifier(report_id)
        with self.store.operation(report_id):
            report = self.manager.get_report(report_id)
            if report is None:
                return False
            atomic_json(self.store.path('.evidence-tombstones', report_id + '.json'),
                        {'report_id': report_id, 'deleted_at': now(), 'revision': report.revision})
            return self.manager._delete_report_unlocked(report_id)
