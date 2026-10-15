"""Source admission and interval coverage; never a semantic correctness score."""
from .claim_ledger import canonical_digest, finding, validate_source
from .source_retrieval import freeze_sources

POLICY = 'evidence-draft-v15-source-completeness'


def freeze_review_sources(storage, scope):
    rows = storage.get_source_chunks(**scope)
    corpus = freeze_sources(rows, scope)
    # Absence of an independent inventory must never imply a complete upload.
    loader = getattr(storage, 'get_source_inventory', None)
    inventory = loader(**scope) if callable(loader) else None
    if not isinstance(inventory, list):
        inventory = None
    admitted = {s['episode_id'] for s in corpus['sources']}
    rejected = []
    for row in rows:
        if not isinstance(row, dict) or any(row.get(k) != v for k, v in scope.items()):
            continue
        if row.get('origin', 'source_document') != 'source_document':
            continue
        if row.get('uuid') not in admitted:
            rejected.append({'episode_id': row.get('uuid'), 'document_id': row.get('document_id'),
                             'reason': 'source_text_missing' if not isinstance(row.get('data'), str)
                             or not row['data'].strip() else 'source_not_admitted'})
    corpus['inventory'] = inventory
    corpus['rejected_sources'] = sorted(rejected, key=canonical_digest)
    corpus['digest'] = canonical_digest({k: v for k, v in corpus.items() if k != 'digest'})
    return corpus


def _merge(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return merged


def source_completeness(corpus, packet):
    """Recompute original chunk intervals, including exact reconstruction overlap."""
    from .pdf_chunk_context import exact_overlap
    originals = {s['episode_id']: s for s in corpus['sources']}
    intervals = {key: [] for key in originals}
    invalid = False
    for source in packet:
        if validate_source(source, corpus['scope']):
            invalid = True
            continue
        components = (source.get('reconstruction') or {}).get('components')
        if components:
            offset, previous = 0, None
            for component in components:
                if previous:
                    overlap = exact_overlap(previous['excerpt'], component['excerpt'])
                    offset += len(previous['excerpt']) - overlap
                original = originals.get(component['episode_id'])
                if (not original or original['source_hash'] != component['source_hash']
                        or original['locator'].get('chunk_index') != component['chunk_index']
                        or original['document_id'] != source['document_id']):
                    invalid = True
                else:
                    start = max(0, source['window_start'] - offset)
                    end = min(len(original['excerpt']), source['window_end'] - offset)
                    if start < end:
                        intervals[component['episode_id']].append([start, end])
                previous = component
        else:
            original = originals.get(source['episode_id'])
            if (not original or source['source_hash'] != original['source_hash']
                    or source['document_id'] != original['document_id']):
                invalid = True
            else:
                intervals[source['episode_id']].append([source['window_start'], source['window_end']])
    inventory = corpus.get('inventory')
    valid_inventory = isinstance(inventory, list) and bool(inventory)
    expected = {}
    if valid_inventory:
        for row in inventory:
            if (not isinstance(row, dict) or not isinstance(row.get('document_id'), str)
                    or not row['document_id'] or row['document_id'] in expected):
                valid_inventory = False
                break
            expected[row['document_id']] = row
    documents = []
    for identifier in sorted(set(expected) | {s['document_id'] for s in originals.values()}):
        original_chunks = [s for s in originals.values() if s['document_id'] == identifier]
        meta = expected.get(identifier, {})
        chunks = []
        for s in original_chunks:
            covered = _merge(intervals[s['episode_id']])
            length = len(s['excerpt'])
            chunks.append({'episode_id': s['episode_id'], 'characters': length,
                           'covered_intervals': covered,
                           'omitted_characters': length - sum(b-a for a,b in covered)})
        count = meta.get('chunk_count')
        extraction_ok = type(meta.get('text_length')) is int and meta['text_length'] > 0
        inventory_ok = (valid_inventory and type(count) is int and count > 0
                        and count == len(chunks) and extraction_ok)
        if 'chunk_indices' in meta:
            actual_indices = [s['locator'].get('chunk_index') for s in original_chunks]
            inventory_ok = inventory_ok and all(type(i) is int for i in actual_indices) and sorted(actual_indices) == meta['chunk_indices']
        rejected = [r for r in corpus.get('rejected_sources', []) if r['document_id'] == identifier]
        complete = inventory_ok and not rejected and all(c['omitted_characters'] == 0 for c in chunks)
        documents.append({'document_id': identifier, 'filename': meta.get('filename'),
                          'expected_chunks': count, 'admitted_chunks': len(chunks),
                          'inventory_verified': inventory_ok, 'chunks': chunks,
                          'rejected_sources': rejected, 'complete': complete})
    complete = (valid_inventory and bool(documents) and not corpus['limited'] and not invalid
                and not corpus.get('rejected_sources') and all(d['complete'] for d in documents))
    return {'schema_version': 1, 'complete': complete, 'inventory_available': valid_inventory,
            'corpus_limited': corpus['limited'], 'invalid_packet_sources': invalid,
            'rejected_sources': corpus.get('rejected_sources', []), 'documents': documents}


def completeness_findings(coverage):
    if coverage['complete']:
        return []
    incomplete = sum(not d['complete'] for d in coverage['documents'])
    return [{**finding('source_completeness_unresolved'),
             'detail': f'Source coverage is unresolved for {incomplete} document(s). Missing extraction, inventory or passages cannot be treated as reviewed.',
             'next_action': 'Inspect source coverage below. Restore missing document text or rebuild its source graph; for material exceeding review limits, use a focused correction with its stated scope.'}]


def retrieve_review_sources(corpus, queries, *, budget, embedder=None):
    """Prefer complete originals within the existing packet ceiling."""
    from .source_retrieval import retrieve_sources
    sources = corpus['sources']
    if len(sources) <= 30 and sum(len(s['excerpt']) for s in sources) <= 60000:
        budget.check()
        packet = [{k: v for k, v in s.items() if k not in {'embedding', 'embedding_provider_id'}} |
                  {'window': s['excerpt'], 'window_start': 0, 'window_end': len(s['excerpt']),
                   'window_hash': s['source_hash']} for s in sources]
        count = len({s['document_id'] for s in sources})
        return {'sources': packet, 'limitations': list(corpus['limitations']),
                'rankings': {'admitted': len(sources), 'admitted_documents': count,
                             'represented_documents': count, 'packet_characters': sum(len(s['window']) for s in packet),
                             'selection': 'complete_stored_sources'}}
    return retrieve_sources(corpus, queries, budget=budget, embedder=embedder)
