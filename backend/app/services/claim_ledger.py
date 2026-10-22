"""Deterministic provenance contracts for evidence-first drafts.

These checks establish structural linkage, never the truth of a source or inference.
"""
import hashlib
import json
import re

from .evidence_verifier import text_hash
from .pdf_source_pages import exact_extract_range

SCOPE_KEYS = ('graph_id', 'case_id', 'case_version_id')
KINDS = {'source_statement', 'attributed_allegation', 'analysis'}
MAX_CLAIMS = 30


def conditional_offer(text):
    """Bounded English trigger, not a general entailment classifier."""
    return isinstance(text, str) and bool(
        re.search(r'\b(could|may|might)\b', text, re.I)
        and re.search(r'\b(if|unless|provided|providing)\b', text, re.I))


def canonical_digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def finding(code, claim_id=None, blocking=True):
    result = {'code': code, 'blocking': blocking}
    if claim_id is not None:
        result['claim_id'] = claim_id
    return result


def _strings(value, maximum=30):
    return isinstance(value, list) and len(value) <= maximum and all(
        isinstance(item, str) and 0 < len(item) <= 200 for item in value)


def validate_source(source, scope):
    if not isinstance(source, dict) or source.get('origin') != 'source_document':
        return 'wrong_origin'
    if any(not scope.get(key) or source.get(key) != scope[key] for key in SCOPE_KEYS):
        return 'scope_mismatch'
    if any(not isinstance(source.get(key), str) or not source[key] for key in
           ('evidence_id', 'document_id', 'episode_id', 'excerpt', 'window')):
        return 'missing_provenance'
    if source.get('reconstruction') is not None:
        from .pdf_chunk_context import reconstruct
        provenance = source['reconstruction']
        if (not isinstance(provenance, dict)
                or provenance.get('kind') != 'exact_overlapping_original_chunks'
                or reconstruct(provenance.get('components')) != source['excerpt']):
            return 'invalid_chunk_reconstruction'
    if source.get('source_hash') != text_hash(source['excerpt']):
        return 'source_hash_mismatch'
    start, end = source.get('window_start'), source.get('window_end')
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source['excerpt']):
        return 'invalid_window'
    if source['excerpt'][start:end] != source['window'] or source.get('window_hash') != text_hash(source['window']):
        return 'window_hash_mismatch'
    return None


def validate_ledger(ledger, sources, scope):
    if not isinstance(ledger, list) or not ledger or len(ledger) > MAX_CLAIMS:
        return [finding('invalid_ledger')]
    if not isinstance(scope, dict) or any(not scope.get(k) for k in SCOPE_KEYS):
        return [finding('scope_mismatch')]
    if not isinstance(sources, list) or any(not isinstance(s, dict) for s in sources):
        return [finding('invalid_sources')]
    by_source, claims, findings = {}, {}, []
    for source in sources:
        identifier = source.get('evidence_id')
        if not isinstance(identifier, str) or identifier in by_source:
            findings.append(finding('duplicate_or_invalid_source_id'))
            continue
        by_source[identifier] = source
    for claim in ledger:
        if not isinstance(claim, dict) or not isinstance(claim.get('claim_id'), str) or not claim['claim_id']:
            findings.append(finding('invalid_claim'))
            continue
        identifier = claim['claim_id']
        if identifier in claims:
            findings.append(finding('duplicate_claim_id', identifier))
        claims[identifier] = claim
    for identifier, claim in claims.items():
        if not isinstance(claim.get('text'), str) or not claim['text'].strip() or len(claim['text']) > 4000:
            findings.append(finding('invalid_claim_text', identifier))
        if not isinstance(claim.get('scope'), dict) or any(claim['scope'].get(k) != scope[k] for k in SCOPE_KEYS):
            findings.append(finding('scope_mismatch', identifier))
        kind = claim.get('kind')
        if not isinstance(kind, str) or kind not in KINDS:
            findings.append(finding('new_simulation_observation' if kind == 'simulation_observation' else 'invalid_claim_kind', identifier))
            continue
        if kind == 'analysis':
            if claim.get('citation_ids', []) != []:
                findings.append(finding('analysis_citations_must_use_premises', identifier))
            if not _strings(claim.get('premise_claim_ids')) or not claim['premise_claim_ids']:
                findings.append(finding('missing_premises', identifier))
            continue
        if kind == 'attributed_allegation' and (not isinstance(claim.get('attribution'), str) or not claim['attribution'].strip()):
            findings.append(finding('missing_attribution', identifier))
        citations = claim.get('citation_ids')
        if not _strings(citations, maximum=3) or not citations:
            findings.append(finding('missing_citation', identifier))
            continue
        for citation in citations:
            source = by_source.get(citation)
            error = validate_source(source, scope) if source else 'unknown_citation'
            if error:
                findings.append(finding(error, identifier))
            elif conditional_offer(source['excerpt']) and not (
                    exact_extract_range(source) is not None
                    and claim.get('text') == source['excerpt'][slice(*exact_extract_range(source))]
                    and isinstance(claim.get('text'), str) and claim['text'] in source['window']):
                findings.append(finding('conditional_source_requires_extract', identifier))
        quote = claim.get('quote', '')
        if not isinstance(quote, str) or (quote and not any(
                quote in by_source[c]['window'] for c in citations
                if c in by_source and not validate_source(by_source[c], scope))):
            findings.append(finding('quote_absent', identifier))

    colors, outcomes, conditional_claims = {}, {}, set()
    for identifier, claim in claims.items():
        if any(conditional_offer(by_source.get(c, {}).get('excerpt'))
               for c in (claim.get('citation_ids') if _strings(claim.get('citation_ids')) else [])):
            conditional_claims.add(identifier)

    def visit(identifier):
        if identifier not in claims:
            return {'unverified'}
        if colors.get(identifier) == 1:
            findings.append(finding('premise_cycle', identifier))
            return {'unverified'}
        if colors.get(identifier) == 2:
            return outcomes[identifier]
        colors[identifier] = 1
        claim = claims[identifier]
        checks = claim.get('checks')
        allowed_outcomes = {'supported', 'contradicted', 'conflicting', 'unverified', 'insufficient'}
        if checks is None:
            checks = []
        if not isinstance(checks, list) or any(
                not isinstance(c, dict) or not isinstance(c.get('outcome'), str)
                or c['outcome'] not in allowed_outcomes for c in checks):
            findings.append(finding('invalid_checks', identifier))
            state = {'unverified'}
        else:
            state = {c['outcome'] for c in checks}
        if claim.get('kind') == 'analysis':
            premises = claim.get('premise_claim_ids', [])
            if _strings(premises):
                for parent in premises:
                    if parent not in claims:
                        findings.append(finding('unknown_premise', identifier))
                    state.update(visit(parent))
                    if parent in conditional_claims:
                        conditional_claims.add(identifier)
            if identifier in conditional_claims:
                findings.append(finding('conditional_analysis_requires_review', identifier))
            for outcome in sorted(state - {'supported'}):
                findings.append(finding('premise_' + str(outcome), identifier, blocking=False))
        elif not state:
            state = {'unverified'}
        if any(f.get('claim_id') == identifier and f['blocking'] for f in findings):
            state.add('unverified')
        colors[identifier] = 2
        outcomes[identifier] = state or {'unverified'}
        return outcomes[identifier]

    for identifier in claims:
        visit(identifier)
    return findings


def validate_paragraphs(paragraphs, ledger, sources=None):
    if not isinstance(paragraphs, list) or not paragraphs or len(paragraphs) > 60:
        return [finding('invalid_paragraphs')]
    claims = {c['claim_id']: c for c in ledger}
    conditional_sources = {s['evidence_id'] for s in sources or [] if conditional_offer(s.get('excerpt'))}
    findings = []
    for index, paragraph in enumerate(paragraphs):
        def issue(code, **details):
            findings.append({**finding(code), 'paragraph_index': index, **details})
        if not isinstance(paragraph, dict):
            issue('invalid_paragraph')
            continue
        text, identifiers = paragraph.get('text'), paragraph.get('claim_ids')
        if isinstance(identifiers, list) and any(
                isinstance(i, str) and i in claims and (conditional_offer(claims[i].get('text'))
                or (_strings(claims[i].get('citation_ids')) and bool(set(claims[i]['citation_ids']) & conditional_sources))) for i in identifiers):
            if len(identifiers) != 1 or text != claims[identifiers[0]]['text']:
                issue('conditional_paragraph_requires_extract')
        if not isinstance(text, str) or not text.strip() or len(text) > 8000:
            issue('invalid_paragraph_text')
        if not _strings(identifiers) or not identifiers or any(i not in claims for i in identifiers):
            issue('unlinked_paragraph')
        elif any(claims[i]['kind'] != paragraph.get('kind') for i in identifiers):
            issue('paragraph_kind_mismatch', expected_kinds=sorted({claims[i]['kind'] for i in identifiers}),
                  detail='Every linked claim must have the paragraph kind; separate different kinds.')
    return findings


def render_paragraphs(paragraphs, ledger):
    if validate_paragraphs(paragraphs, ledger):
        raise ValueError('invalid_paragraphs')
    claims = {c['claim_id']: c for c in ledger}
    citations = list(dict.fromkeys(citation for c in ledger for citation in c.get('citation_ids', [])))
    rendered = []
    for paragraph in paragraphs:
        numbers = sorted({citations.index(c) + 1 for identifier in paragraph['claim_ids']
                          for c in claims[identifier].get('citation_ids', [])})
        prefix = 'Analysis: ' if paragraph['kind'] == 'analysis' else ''
        suffix = ''.join(f' [{number}]' for number in numbers)
        rendered.append(prefix + paragraph['text'].strip() + suffix)
    return '\n\n'.join(rendered)


def apply_summary_edits(original, edits, ledger):
    if not isinstance(original, str) or not isinstance(edits, list) or len(edits) > 30:
        raise ValueError('invalid_summary_edits')
    claims = {c['claim_id'] for c in ledger}
    for edit in edits:
        if not isinstance(edit, dict) or not _strings(edit.get('claim_ids')) or not edit['claim_ids'] or any(
                identifier not in claims for identifier in edit['claim_ids']):
            raise ValueError('invalid_summary_claims')
        if type(edit.get('start')) is not int or type(edit.get('end')) is not int:
            raise ValueError('invalid_summary_offsets')
        if not isinstance(edit.get('new_text'), str) or len(edit['new_text']) > 8000:
            raise ValueError('invalid_summary_text')
    previous_start, result = len(original) + 1, original
    for edit in sorted(edits, key=lambda item: item['start'], reverse=True):
        start, end = edit['start'], edit['end']
        if not 0 <= start < end <= len(original) or end > previous_start:
            raise ValueError('overlapping_or_invalid_summary_edit')
        if original[start:end] != edit.get('old_text'):
            raise ValueError('stale_summary_span')
        result = result[:start] + edit['new_text'] + result[end:]
        previous_start = start
    return result


def resolve_summary_replacements(original, replacements, ledger):
    """Resolve exact unique original spans; never guess stale/repeated targets.

    Models supply text, not offsets. Existing deterministic edit validation stays
    authoritative, including claim links, overlap and replacement-size bounds.
    """
    if not isinstance(original, str) or not isinstance(replacements, list) or len(replacements) > 30:
        raise ValueError('invalid_summary_replacements')
    edits = []
    for replacement in replacements:
        if not isinstance(replacement, dict):
            raise ValueError('invalid_summary_replacement')
        old = replacement.get('old_text')
        if not isinstance(old, str) or not old or len(old) > 64000:
            raise ValueError('invalid_summary_target')
        start = original.find(old)
        if start < 0 or original.find(old, start + 1) >= 0:
            raise ValueError('missing_or_ambiguous_summary_target')
        edits.append({'start': start, 'end': start + len(old), 'old_text': old,
                      'new_text': replacement.get('new_text'), 'claim_ids': replacement.get('claim_ids')})
    apply_summary_edits(original, edits, ledger)
    return edits


def summary_edit_scope(original, section_text, selected_text=None):
    """Use an exact section match or an explicit operator-selected passage.

    Selection authorizes the edit boundary, never the truth of its contents.
    The replacement still needs ledger support and the normal source audit.
    """
    if not isinstance(original, str):
        raise ValueError('invalid_summary')
    if original == '' and selected_text is None:
        return {'basis': 'empty_original_summary', 'editable_spans': [],
                'unmapped_summary_requires_review': False}
    spans = []
    if selected_text is not None:
        if not isinstance(selected_text, str) or not 0 < len(selected_text) <= 2000 or not selected_text.strip():
            raise ValueError('invalid_summary_selection')
        start = original.find(selected_text)
        if start < 0 or original.find(selected_text, start + 1) >= 0:
            raise ValueError('missing_or_ambiguous_summary_target')
        return {'basis': 'operator_selected_summary',
                'editable_spans': [{'start': start, 'end': start + len(selected_text), 'text': selected_text}],
                'unmapped_summary_requires_review': False}
    if isinstance(section_text, str) and section_text.strip():
        start = original.find(section_text)
        if start >= 0 and original.find(section_text, start + 1) < 0:
            spans.append({'start': start, 'end': start + len(section_text), 'text': section_text})
    return {'basis': 'unique_exact_selected_section', 'editable_spans': spans,
            'unmapped_summary_requires_review': not bool(spans)}


def validate_summary_edit_scope(edits, scope):
    spans = scope['editable_spans']
    for edit in edits:
        if not any(span['start'] <= edit['start'] < edit['end'] <= span['end'] for span in spans):
            raise ValueError('summary_edit_outside_selected_section')
