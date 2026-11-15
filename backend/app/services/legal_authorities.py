"""Explicit primary-text references, frozen separately from the matter's facts.

Schema and hashes establish input identity, not the truth or currency of law.
The caller supplies the research receipt; this module never fetches a URL.
"""
from copy import deepcopy
from datetime import date
from urllib.parse import urlsplit

from .claim_ledger import canonical_digest


def normalize_legal_authorities(value):
    if not isinstance(value, list) or len(value) > 12:
        raise ValueError('invalid_legal_authorities')
    sources, seen, total = [], set(), 0
    for item in value:
        if not isinstance(item, dict):
            raise ValueError('invalid_legal_authority')
        metadata = {}
        for key, maximum in [('citation', 300), ('source_url', 2048), ('retrieved_at', 10),
                             ('verification_note', 2000), ('treatment_note', 2000)]:
            text = item.get(key)
            if not isinstance(text, str) or not text.strip() or len(text) > maximum:
                raise ValueError('invalid_legal_authority_' + key)
            metadata[key] = text.strip()
        try:
            url = urlsplit(metadata['source_url'])
            if url.scheme != 'https' or not url.hostname or url.username or url.password:
                raise ValueError()
            date.fromisoformat(metadata['retrieved_at'])
        except ValueError as exc:
            raise ValueError('invalid_legal_authority_locator') from exc
        paragraphs = item.get('paragraphs')
        if not isinstance(paragraphs, dict) or not 1 <= len(paragraphs) <= 64:
            raise ValueError('invalid_legal_authority_paragraphs')
        if any(not isinstance(key, str) or not key.strip() or len(key) > 80
               or not isinstance(text, str) or not text.strip() or len(text) > 12000
               for key, text in paragraphs.items()):
            raise ValueError('invalid_legal_authority_paragraph')
        identity = canonical_digest({'citation': metadata['citation'], 'source_url': metadata['source_url'],
                                     'paragraphs': paragraphs})
        if identity in seen:
            raise ValueError('duplicate_legal_authority')
        seen.add(identity)
        ordered = sorted(paragraphs, key=lambda key: (0, int(key)) if key.isdigit() else (1, key))
        for locator in ordered:
            text = paragraphs[locator]
            total += len(text)
            if total > 60000:
                raise ValueError('legal_authority_context_limit')
        excerpt = (paragraphs[ordered[0]] if len(ordered) == 1 else
                   '\n\n'.join(f'[Paragraph {key}]\n{paragraphs[key]}' for key in ordered))
        sources.append({**metadata, 'document_id': 'doc_law_' + identity[:16],
            'evidence_id': 'authority:' + identity, 'source_kind': 'legal_authority',
            'origin': 'supplied_primary_text',
            'verification_status': 'supplied_research_receipt_not_automatic_verification',
            'locator': {'paragraphs': ordered}, 'excerpt': excerpt, 'source_hash': canonical_digest(excerpt)})
    return sorted(sources, key=lambda row: row['evidence_id'])


def authority_digest(sources):
    return canonical_digest(sources) if sources else None


def attach_legal_authorities(packet, sources):
    if not sources:
        return packet
    packet = deepcopy(packet)
    packet.pop('digest', None)
    packet.update(authority_sources=deepcopy(sources), authority_digest=authority_digest(sources))
    packet['digest'] = canonical_digest(packet)
    return packet


def admitted_sources(grounding):
    return list(grounding.get('original_sources') or []) + list(grounding.get('authority_sources') or [])
