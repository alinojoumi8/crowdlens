"""Bounded retrieval from frozen original source chunks, with visible coverage."""
import math
import re
from collections import Counter
from .claim_ledger import SCOPE_KEYS, canonical_digest
from .evidence_verifier import text_hash
from .source_tracing import SourceIndex, tokens
from .pdf_source_pages import contextual_page_window, complete_pages


def lexical_anchor(text, query_terms):
    """Choose the densest matching span using original Unicode offsets."""
    hits = [(match.start(), match.group().casefold()) for match in re.finditer(r'\w+', text)
            if match.group().casefold() in query_terms]
    counts, left, best, anchor = Counter(), 0, (0, 0), 0
    for right, (offset, term) in enumerate(hits):
        counts[term] += 1
        while offset - hits[left][0] > 1600:
            expired = hits[left][1]
            counts[expired] -= 1
            if not counts[expired]:
                del counts[expired]
            left += 1
        score = (len(counts), right - left + 1)
        if score > best:
            best, anchor = score, hits[left][0]
    return anchor


def valid_vector(value, dimensions=None):
    return (isinstance(value, list) and bool(value) and (dimensions is None or len(value) == dimensions)
            and all(type(x) in (float, int) and math.isfinite(x) for x in value)
            and sum(x*x for x in value) > 0)


def freeze_sources(episodes, scope):
    if not isinstance(scope, dict) or any(not isinstance(scope.get(k), str) or not scope[k] for k in SCOPE_KEYS):
        raise ValueError('missing_source_scope')
    rows = [row for row in episodes if isinstance(row, dict) and isinstance(row.get('uuid'), str)
            and isinstance(row.get('document_id'), str) and row['document_id']
            and row.get('origin', 'source_document') == 'source_document'
            and all(row.get(k) == scope[k] for k in SCOPE_KEYS)]
    rows.sort(key=lambda row: row['uuid'])
    if len({row['uuid'] for row in rows}) != len(rows):
        raise ValueError('duplicate_source_id')
    index = SourceIndex(rows, scope)
    originals = {row['uuid']: row for row in rows}
    for source in index.sources:
        row = originals[source['episode_id']]
        if valid_vector(row.get('embedding')) and isinstance(row.get('embedding_provider_id'), str):
            source['embedding'] = row['embedding']
            source['embedding_provider_id'] = row['embedding_provider_id']
    limited = index.limited or len(episodes) > 2000
    result = {'scope': dict(scope), 'sources': index.sources, 'limited': limited,
              'limitations': ['source_corpus_truncated'] if limited else []}
    result['digest'] = canonical_digest(result)
    return result


def reciprocal_rank_fusion(rankings):
    scores = {}
    for ranking in rankings:
        for rank, identifier in enumerate(dict.fromkeys(ranking), 1):
            scores[identifier] = scores.get(identifier, 0) + 1 / (60 + rank)
    return sorted(scores, key=lambda key: (-scores[key], key))


def retrieve_sources(corpus, queries, *, budget, embedder=None):
    budget.check()
    queries = list(dict.fromkeys(q.strip() for q in queries if isinstance(q, str) and q.strip()))[:6]
    queries = [q[:2000] for q in queries]
    sources = {s['evidence_id']: s for s in corpus['sources']}
    limitations = list(corpus['limitations'])
    rows = [{**s, 'uuid': s['episode_id'], 'data': s['excerpt'], **s['locator']} for s in sources.values()]
    index = SourceIndex(rows, corpus['scope'])
    quotes = list(dict.fromkeys(phrase for q in queries for phrase in (re.findall(r'["“]([^"”]+)["”]', q) or [q])))
    exact = sorted(identifier for identifier, source in sources.items() if any(q in source['excerpt'] for q in quotes))
    rankings = [[s['evidence_id'] for s in index.search(q, limit=31)] for q in queries]
    if any(len(ranking) > 30 for ranking in rankings):
        limitations.append('retrieval_candidates_truncated')
    rankings = [ranking[:30] for ranking in rankings]
    lexical = reciprocal_rank_fusion(rankings)
    vectors, semantic_rankings = {}, []
    if embedder is None:
        limitations.append('semantic_retrieval_unavailable')
    elif getattr(embedder, 'provider', None) != 'ollama':
        limitations.append('remote_embeddings_skipped')
    else:
        provider_id = embedder.provider_id()
        dimensions = embedder.dimensions
        vectors = {key: s['embedding'] for key, s in sources.items()
                   if s.get('embedding_provider_id') == provider_id and valid_vector(s.get('embedding'), dimensions)}
        candidate_order = list(dict.fromkeys(exact + lexical + sorted(sources)))
        new_count = 0
        try:
            for key in candidate_order:
                if key in vectors:
                    continue
                if new_count == 200:
                    break
                budget.check()
                vector = embedder.embed(sources[key]['excerpt'], task_type='RETRIEVAL_DOCUMENT',
                    request_timeout=min(10, budget.remaining()), request_max_retries=0)
                budget.check()
                new_count += 1
                if valid_vector(vector, dimensions):
                    vectors[key] = vector
            for query in queries:
                budget.check()
                vector = embedder.embed(query, task_type='RETRIEVAL_QUERY',
                    request_timeout=min(10, budget.remaining()), request_max_retries=0)
                budget.check()
                if not valid_vector(vector, dimensions):
                    limitations.append('invalid_query_embedding')
                    continue
                norm = math.sqrt(sum(v*v for v in vector))
                scores = {key: sum(a*b for a,b in zip(vector, other)) / (norm * math.sqrt(sum(v*v for v in other)))
                          for key, other in vectors.items()}
                ranking = sorted((key for key, score in scores.items() if score > 0), key=lambda key: (-scores[key], key))
                if len(ranking) > 30:
                    limitations.append('retrieval_candidates_truncated')
                semantic_rankings.append(ranking[:30])
        except Exception as exc:
            from ..utils.draft_budget import DeadlineExceeded
            if isinstance(exc, DeadlineExceeded):
                raise
            limitations.append('local_embeddings_unavailable')
        if len(vectors) < len(sources):
            limitations.append('partial_semantic_coverage')
    fused = reciprocal_rank_fusion(rankings + semantic_rankings)
    selected = list(dict.fromkeys(exact + fused))
    if len(selected) > 30:
        limitations.append('retrieval_candidates_truncated')
    selected = selected[:30]
    if len(exact) > 30:
        limitations.append(f'exact_hits_truncated:{len(exact) - 30}')
    # Chunk indices, not lexicographic episode IDs, establish adjacent context.
    neighbors = []
    for key in selected:
        current = sources[key]
        chunk_index = current['locator'].get('chunk_index')
        if type(chunk_index) is not int:
            continue
        neighbors.extend(other for other in sorted(sources)
            if sources[other]['document_id'] == current['document_id']
            and type(sources[other]['locator'].get('chunk_index')) is int
            and abs(sources[other]['locator']['chunk_index'] - chunk_index) == 1)
    # A relevant hit anchors the packet. Also inspect one original window from
    # each admitted document: lexical silence is not evidence of irrelevance.
    # Preserve no-hit behavior and the existing scope/30-window/60k limits.
    ranked = list(dict.fromkeys(selected + neighbors))
    representatives = {}
    if selected:
        for key in ranked + sorted(sources):
            representatives.setdefault(sources[key]['document_id'], key)
    selected = list(dict.fromkeys(list(representatives.values()) + ranked))
    if len(selected) > 30:
        limitations.append('adjacent_context_truncated')
    selected = selected[:30]
    packet, used = [], 0
    query_terms = set(tokens(' '.join(queries)))
    for key in selected:
        budget.check()
        source = sources[key]
        text = source['excerpt']
        matches = [(text.index(q), len(q)) for q in quotes if q in text]
        at, length = min(matches) if matches else (lexical_anchor(text, query_terms), 0)
        window_size = max(2000, length + 400)
        start = max(0, at - 200)
        end = min(len(text), start + window_size)
        page = contextual_page_window(text, at)
        if not page and not matches:
            # Rank complete pages themselves when the chunk's best hit falls
            # in a fragment. Explicit literal quotes never take this fallback.
            candidates = [(len(query_terms & set(tokens(text[a:b]))), number, a, b)
                          for number, a, b in complete_pages(text) if b - a <= 4000]
            candidates = [c for c in candidates if c[0] >= min(3, len(query_terms)) and c[0] > 0]
            if candidates:
                _, number, a, b = max(candidates, key=lambda c: (c[0], -c[2]))
                page = (number, a, b)
                at = a
                limitations.append('pdf_complete_page_reranked: fragment matches may remain outside selected pages')
        if page and length <= page[2] - at:
            _, start, end = page
        # Expand both boundaries until every intersecting requested quote is whole.
        previous = None
        while previous != (start, end):
            previous = (start, end)
            for offset, size in matches:
                if offset < end and offset + size > start:
                    start, end = min(start, offset), max(end, offset + size)
        if end - start > 60000 - used:
            limitations.append('drafting_packet_truncated')
            continue
        if start or end < len(text):
            limitations.append('source_windows_clipped')
        if any(offset < start or offset + size > end for offset, size in matches):
            limitations.append('requested_quotes_outside_windows')
        window = text[start:end]
        locator = dict(source['locator'])
        if page and (start, end) == page[1:]:
            selected_pages = [n for n, a, b in complete_pages(text) if start <= a and b <= end]
            locator.update(page=selected_pages[0], page_end=selected_pages[-1], char_start=start, char_end=end)
            limitations.append('pdf_page_context_bounded: adjacent pages may contain continued attribution or conditions')
        used += len(window)
        packet.append({k: v for k, v in source.items() if k not in {'embedding', 'embedding_provider_id'}} |
                      {'window': window, 'window_start': start, 'window_end': end, 'window_hash': text_hash(window),
                       'locator': locator})
    admitted_documents = len({source['document_id'] for source in sources.values()})
    represented_documents = len({source['document_id'] for source in packet})
    if represented_documents < admitted_documents:
        limitations.append('document_coverage_truncated' if selected else 'no_relevant_source_anchor')
    return {'sources': packet, 'limitations': list(dict.fromkeys(limitations)),
            'rankings': {'exact': exact[:30], 'lexical': lexical[:30], 'fused': fused[:30],
                         'semantic_covered': len(vectors), 'admitted': len(sources), 'packet_characters': used,
                         'admitted_documents': admitted_documents, 'represented_documents': represented_documents}}


def verifier_sources(sources):
    return [{**s, 'excerpt': s['window'], 'source_hash': s['window_hash'],
             'original_source_hash': s['source_hash']} for s in sources]
