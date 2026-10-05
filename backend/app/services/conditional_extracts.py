"""Server-owned complete sentences for detected conditional source excerpts.

Selection and rendering replace model wording; they never certify source truth.
"""
import copy
import re
from .claim_ledger import canonical_digest, conditional_offer, complete_source_extract, validate_source, KINDS


def build_extract_contract(sources, scope):
    candidates = {}
    for source in sources:
        if validate_source(source, scope) or not conditional_offer(source['excerpt']):
            continue
        for match in re.finditer(r'\S.*?(?:[.!?](?=\s|$)|$)', source['excerpt'], re.S):
            start, end = match.span()
            text = match.group()
            if (len(text) > 4000 or not source['window_start'] <= start < end <= source['window_end']
                    or not complete_source_extract(text, source['excerpt'])):
                continue
            basis = {**scope, 'evidence_id': source['evidence_id'], 'source_hash': source['source_hash'],
                     'window_hash': source['window_hash'], 'start': start, 'end': end}
            identifier = 'sentence:' + canonical_digest(basis)
            candidates[identifier] = {'source_sentence_id': identifier, 'evidence_id': source['evidence_id'],
                                     'text': text, 'source_start': start, 'source_end': end}
    return list(candidates.values())


def resolve_extract_claims(claims, contract):
    """Resolve explicit sentence selection, never fuzzy-match a paraphrase."""
    candidates = {c['source_sentence_id']: c for c in contract}
    ledger, changes = copy.deepcopy(claims), []
    for claim in ledger:
        if 'source_sentence_id' not in claim:
            continue  # Exact legacy extracts still face the existing ledger guard.
        identifier = claim['source_sentence_id']
        if not isinstance(identifier, str) or identifier not in candidates:
            raise ValueError('unknown_source_sentence')
        candidate = candidates[identifier]
        if (claim.get('kind') not in KINDS - {'analysis'}
                or claim.get('citation_ids') != [candidate['evidence_id']]
                or claim.get('premise_claim_ids') != []):
            raise ValueError('invalid_source_sentence_linkage')
        changes.append({'claim_id': claim['claim_id'], 'source_sentence_id': identifier,
                        'model_text': claim.get('text'), 'source_text': candidate['text']})
        claim['text'] = candidate['text']
    return ledger, changes


def render_extract_paragraphs(paragraphs, ledger, sources):
    """Only render well-formed single-claim links; other contract errors remain."""
    rendered = copy.deepcopy(paragraphs)
    changes = []
    if not isinstance(rendered, list) or len(rendered) > 60:
        return rendered, changes
    claims = {c['claim_id']: c for c in ledger}
    guarded_sources = {s['evidence_id'] for s in sources if conditional_offer(s['excerpt'])}
    for index, paragraph in enumerate(rendered):
        if not isinstance(paragraph, dict):
            continue
        ids, text = paragraph.get('claim_ids'), paragraph.get('text')
        if (not isinstance(ids, list) or len(ids) != 1 or not isinstance(ids[0], str)
                or ids[0] not in claims or not isinstance(text, str) or not text.strip() or len(text) > 8000):
            continue
        claim = claims[ids[0]]
        if paragraph.get('kind') != claim['kind'] or not guarded_sources.intersection(claim.get('citation_ids', [])):
            continue
        if text != claim['text']:
            changes.append({'paragraph_index': index, 'claim_id': ids[0], 'model_text': text,
                            'source_text': claim['text']})
        paragraph['text'] = claim['text']
    return rendered, changes
