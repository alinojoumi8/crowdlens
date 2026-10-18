"""Explicit audit-only retries keep failed proposals and frozen inputs intact."""
import json

from .claim_ledger import (canonical_digest, summary_edit_scope, validate_summary_edit_scope,
                           validate_ledger, validate_paragraphs, render_paragraphs, apply_summary_edits)
from .proposal_store import ProposalError
from .source_completeness import source_completeness
from .source_coverage import source_coverage
from .summary_sources import validate_concise_summary
from .conditional_extracts import build_extract_contract, resolve_extract_claims

POLICIES = {'evidence-draft-v15-source-completeness', 'evidence-draft-v16-staged-source-review'}
ERRORS = {'audit_timeout', 'audit_unavailable', 'drafting_unavailable', 'deadline_exceeded', 'worker_interrupted'}
COPY_FIELDS = ('scope', 'section_index', 'before', 'after', 'ledger', 'sources', 'paragraphs',
               'summary_format', 'summary_edits', 'source_digest', 'policy', 'model', 'limitations', 'findings',
               'extract_provenance', 'source_completeness', 'summary_selection', 'usage', 'timing')


def saved_inputs(store, record):
    """Reject incomplete or changed checkpoints before any repeat model call."""
    parent = store.load_snapshot(record['proposal_id'], 'parent', record['parent_digest'])
    corpus = store.load_snapshot(record['proposal_id'], 'sources', record['source_snapshot_digest'])
    ledger = store.load_snapshot(record['proposal_id'], 'ledger', record['ledger_digest'])
    section = parent['outline']['sections'][record['section_index'] - 1]
    summary = parent['outline']['summary']
    scope = summary_edit_scope(summary, section['content'], record.get('summary_selection'))
    if (record['scope'] != corpus['scope'] or record['source_digest'] != corpus['digest']
            or record['before'] != {'section': section['content'], 'summary': summary, 'summary_scope_contract': scope}
            or ledger != record['ledger'] or not ledger
            or any(f['blocking'] for f in record['findings'])):
        raise ValueError('invalid_audit_checkpoint')
    validate_summary_edit_scope(record['summary_edits'], scope)
    validate_concise_summary(record)
    findings = validate_ledger(ledger, record['sources'], record['scope'])
    findings += validate_paragraphs(record['paragraphs'], ledger, record['sources'])
    findings += source_coverage(ledger, record['extract_provenance']['source_exclusions'], record['sources'])
    extracts = build_extract_contract(record['sources'], record['scope'])
    resolved, _ = resolve_extract_claims(ledger, extracts)
    coverage = source_completeness(corpus, record['sources'])
    covered_claims = {identifier for paragraph in record['paragraphs'] for identifier in paragraph['claim_ids']}
    if (any(f['blocking'] for f in findings)
            or any(claim['claim_id'] not in covered_claims for claim in ledger)
            or extracts != record['extract_provenance']['contract'] or resolved != ledger
            or (record['policy'] == 'evidence-draft-v15-source-completeness' and
                (not coverage['complete'] or coverage != record['source_completeness']))
            or render_paragraphs(record['paragraphs'], ledger) != record['after']['section']
            or apply_summary_edits(summary, record['summary_edits'], ledger) != record['after']['summary']):
        raise ValueError('invalid_audit_checkpoint')
    if record.get('diagnostics_digest'):
        diagnostics = store.load_snapshot(record['proposal_id'], 'diagnostics', record['diagnostics_digest'])
    else:
        # Older timeout records wrote the diagnostics file but omitted its digest.
        # Retain that file verbatim in the retry; it is never evidence of support.
        diagnostics = json.loads(store._file(record['proposal_id'], 'diagnostics').read_text())
    if not isinstance(diagnostics, dict):
        raise ValueError('invalid_audit_checkpoint')
    return {'parent': parent, 'sources': corpus, 'ledger': ledger, 'diagnostics': diagnostics}


def recovery_details(store, record):
    if (record['state'] != 'failed' or record.get('error_code') not in ERRORS
            or record.get('phase') not in {'auditing', 'deadline', 'interrupted'}
            or record.get('policy') not in POLICIES or record.get('source_review') is not None):
        return {'available': False}
    try:
        inputs = saved_inputs(store, record)
    except (ProposalError, ValueError, KeyError, TypeError, IndexError, OSError):
        return {'available': False}
    # Late telemetry may arrive after the failure is displayed. It does not
    # change the frozen draft, and the retry copies the latest usage under lease.
    checkpoint = {key: value for key, value in record.items() if key not in {'usage', 'timing', 'updated_at'}}
    return {'available': True, 'digest': canonical_digest({'record': checkpoint, 'snapshots': inputs}),
            'usage_may_be_unknown': True}


def copy_for_retry(store, original, new_record, expected_digest):
    recovery = recovery_details(store, original)
    if not recovery['available']:
        raise ProposalError('audit_not_recoverable')
    if not isinstance(expected_digest, str) or recovery['digest'] != expected_digest:
        raise ProposalError('audit_checkpoint_changed')
    inputs = saved_inputs(store, original)
    changes = {key: original[key] for key in COPY_FIELDS if key in original}
    for name, key in [('parent', 'parent_digest'), ('sources', 'source_snapshot_digest'),
                      ('ledger', 'ledger_digest'), ('diagnostics', 'diagnostics_digest')]:
        changes[key] = store.save_snapshot(new_record['proposal_id'], name, inputs[name])
    changes['audit_retry'] = {'proposal_id': original['proposal_id'], 'recovery_digest': expected_digest}
    return changes
