"""Recover PDF context only from consecutive, exactly overlapping originals."""
import hashlib
import json

MAX_JOINED_CHARS = 30000


def exact_overlap(left, right):
    # Short/repeated overlaps cannot establish an unambiguous boundary.
    matches = [n for n in range(64, min(1000, len(left), len(right)) + 1)
               if left[-n:] == right[:n]]
    return matches[0] if len(matches) == 1 else None


def reconstruct(components):
    if not isinstance(components, list) or not 2 <= len(components) <= 3:
        return None
    text, previous = '', None
    for component in components:
        if not isinstance(component, dict):
            return None
        excerpt, index = component.get('excerpt'), component.get('chunk_index')
        if (not isinstance(excerpt, str) or not excerpt or type(index) is not int
                or component.get('source_hash') != hashlib.sha256(excerpt.encode()).hexdigest()
                or not isinstance(component.get('episode_id'), str) or not component['episode_id']):
            return None
        if previous is not None:
            if index != previous['chunk_index'] + 1:
                return None
            overlap = exact_overlap(previous['excerpt'], excerpt)
            if overlap is None:
                return None
            text += excerpt[overlap:]
        else:
            text = excerpt
        if len(text) > MAX_JOINED_CHARS:
            return None
        previous = component
    return text


def joined_context(source, sources):
    index = source['locator'].get('chunk_index')
    if type(index) is not int or '[PDF page ' not in source['excerpt']:
        return None
    by_index = {}
    for candidate in sources:
        if (candidate['document_id'] != source['document_id']
                or any(candidate[k] != source[k] for k in ('graph_id', 'case_id', 'case_version_id'))):
            continue
        number = candidate['locator'].get('chunk_index')
        if type(number) is int and abs(number - index) <= 1:
            if number in by_index:  # Duplicate chunk positions are ambiguous.
                return None
            by_index[number] = candidate
    ordered = [by_index[n] for n in sorted(by_index)]
    components = [{'episode_id': s['episode_id'], 'chunk_index': s['locator']['chunk_index'],
                   'source_hash': s['source_hash'], 'excerpt': s['excerpt']} for s in ordered]
    text = reconstruct(components)
    if text is None:
        return None
    prefix = 0
    for left, right in zip(ordered, ordered[1:]):
        if right['locator']['chunk_index'] <= index:
            prefix += len(left['excerpt']) - exact_overlap(left['excerpt'], right['excerpt'])
    digest = hashlib.sha256(json.dumps(components, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    identifier = 'joined-pdf:' + digest
    return ({**source, 'episode_id': identifier, 'evidence_id': 'episode:' + identifier,
             'excerpt': text, 'source_hash': hashlib.sha256(text.encode()).hexdigest(),
             'reconstruction': {'kind': 'exact_overlapping_original_chunks', 'components': components},
             'locator': {**source['locator'], 'chunk_index': None,
                         'chunk_start': components[0]['chunk_index'], 'chunk_end': components[-1]['chunk_index'],
                         'offset_basis': 'joined_original_chunks', 'char_start': 0, 'char_end': len(text)}}, prefix)
