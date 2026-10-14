"""Bounded original-source and executed-trace context for report generation.

These mechanical quotation/probability checks are not factual certification.
"""
import re
from .claim_ledger import canonical_digest
from .source_retrieval import freeze_sources
from .source_scope import resolve_source_scope
from .simulation_activity import read_activity, unique_actions, summarize_activity

CONTRACT = 'report-grounding-v1'


def select_report_sources(rows, config, maximum=60000):
    """Keep document openings and explicit procedural anchors within the same cap."""
    def position(row):
        index = (row.get('locator') or {}).get('chunk_index')
        return index if type(index) is int and index >= 0 else float('inf')
    ordered = sorted(rows, key=lambda r: (r['document_id'], position(r), r['evidence_id']))
    first = {}
    for row in ordered:
        first.setdefault(row['document_id'], row['evidence_id'])
    legal = config.get('report_mode') == 'legal_case' or (config.get('prediction_settings') or {}).get('report_mode') == 'legal_case'
    def priority(row):
        text = row['excerpt']
        opening = first[row['document_id']] == row['evidence_id']
        anchor = legal and (bool(re.search(r'THE MOTION IS FOR', text, re.I))
            or bool(re.search(r'(?im)^APPROVED HEARING DATE[ \t]*:[ \t]*\S[^\n]+', text))
            or ('THIS COURT' in text and bool(re.search(r'extended to trial|Expanded Scope|amended to expand', text, re.I))))
        return (0 if opening else 1 if anchor else 2, row['document_id'], position(row), row['evidence_id'])
    selected, used = [], 0
    for row in sorted(ordered, key=priority):
        if used + len(row['excerpt']) > maximum:
            continue
        selected.append(row)
        used += len(row['excerpt'])
    return selected


def build_report_grounding(storage, config, graph_id, simulation_dir):
    packet = {'report_contract': CONTRACT, 'graph_id': graph_id, 'status': 'unavailable',
              'original_sources': [], 'limitations': []}
    try:
        scope = resolve_source_scope({'graph_id': graph_id}, config)
        packet.update(scope)
        corpus = freeze_sources(storage.get_source_chunks(**scope), scope)
        # Embeddings are retrieval machinery, not report evidence or prompt data.
        selected = select_report_sources(corpus['sources'], config)
        sources = []
        if len(selected) < len(corpus['sources']):
            packet['limitations'].append('report_source_context_truncated')
        for row in selected:
            sources.append({k: v for k, v in row.items() if k not in ('embedding', 'embedding_provider_id')})
        packet.update(original_sources=sources, source_corpus_digest=corpus['digest'],
                      available_source_count=len(corpus['sources']), selected_source_count=len(sources),
                      status='available' if sources else 'unavailable')
        packet['limitations'].extend(corpus['limitations'])
    except Exception:
        packet['limitations'].append('original_source_scope_or_retrieval_unavailable')
    # Do not manufacture provenance for legacy rows lacking phase labels.
    raw = read_activity(simulation_dir)
    actions, used = [], 0
    all_unique = unique_actions(raw)
    for index, row in enumerate(all_unique):
        reference = f"{row['platform']}:trace:{row['trace_id']}" if row.get('trace_id') is not None else f"{row['platform']}:legacy:{index}"
        item = {**row, 'reference': reference}
        size = len(str(item))
        if len(actions) >= 200 or used + size > 60000:
            packet['limitations'].append('report_action_context_truncated')
            break
        actions.append(item)
        used += size
    if any(row['origin'] == 'unknown' for row in all_unique):
        packet['limitations'].append('legacy_action_origins_unverified')
    activation_mode = (config.get('prediction_settings') or {}).get('activation_mode', 'stochastic')
    if activation_mode == 'smoke_round_robin':
        packet['limitations'].append('deterministic_smoke_activation_not_realistic_activity')
    packet['simulation_activity'] = {'summary': {**summarize_activity(raw), 'activation_mode': activation_mode}, 'actions': actions,
        'contract': 'initial_post and scheduled_event are scenario inputs; only successful runtime model_action records with nonempty authored text establish written responses; unknown is unverified legacy origin; smoke_round_robin deliberately schedules agents for an execution test, not a realistic activity sample'}
    packet['digest'] = canonical_digest(packet)
    return packet


def provenance_issues(content, grounding, forecast):
    if grounding.get('report_contract') != CONTRACT:
        return []
    issues = []
    sources = grounding.get('original_sources') or []
    known_documents = {row.get('document_id') for row in sources}
    for identifier in set(re.findall(r'\[(doc_[A-Za-z0-9_-]+)(?=[,\]])', content)):
        if identifier not in known_documents:
            issues.append({'code': 'unknown_document_citation', 'blocking': True,
                'message': 'Document citation is not an admitted original document ID.', 'document_id': identifier})
    actions = (grounding.get('simulation_activity') or {}).get('actions') or []
    normalize = lambda value: re.sub(r'\s+', ' ', value).strip()
    for paragraph in re.split(r'\n\s*\n', content):
        quotations = re.findall(r'["“]([^"”\n]+)["”]', paragraph)
        quotations += [re.sub(r'\[[^\]]+\]', '', line.lstrip('> ')).strip() for line in paragraph.splitlines()
                       if line.startswith('> ') and len(line) > 2 and not re.search(r'["“]', line)]
        for quote in quotations:
            text = normalize(quote)
            original = any(text in normalize(row.get('excerpt', ''))
                           and f"[{row.get('document_id', '')}]" in paragraph for row in sources)
            trace = any(row.get('origin') == 'model_action'
                        and text in normalize((row.get('action_args') or {}).get('content', ''))
                        and f"[{row.get('reference', '')}]" in paragraph for row in actions)
            if not original and not trace:
                issues.append({'code': 'unverified_quotation', 'blocking': True,
                    'message': 'Quotation is not an exact referenced original-source span or recorded model response.',
                    'quote': quote[:300]})
    if forecast.get('reason') == 'evidence_only':
        for table in re.findall(r'(?:^\|.*\n?)+', content, re.M):
            if (re.search(r'probabilit|likelihood|chance of|confidence', table.splitlines()[0], re.I)
                    and re.search(r'\|\s*(?:0?\.\d+|\d+(?:\.\d+)?\s*%)\s*\|', table)):
                issues.append({'code': 'evidence_only_probability_table', 'blocking': True,
                    'message': 'Evidence-only reports cannot publish numerical outcome probability tables.'})
    # Generated sections must not issue a second numerical forecast. Remove
    # only the exact deterministic authority block. Other percentages need an
    # original-document reference and a matching recorded source number.
    from .forecasting import forecast_to_markdown
    body = content.replace(forecast_to_markdown(forecast), '', 1)
    for paragraph in re.split(r'\n\s*\n', body):
        for number in re.findall(r'(\d+(?:\.\d+)?)\s*%', paragraph):
            sourced = any(f"[{row.get('document_id', '')}]" in paragraph
                and any(float(value) == float(number) for value in re.findall(r'(\d+(?:\.\d+)?)\s*%', row.get('excerpt', '')))
                for row in sources)
            if not sourced:
                issues.append({'code': 'forecast_probability_mismatch', 'blocking': True,
                    'message': 'Numerical percentages outside the frozen forecast table require an original-source reference and matching source number.',
                    'received_percent': number})
    if grounding.get('status') != 'available' or grounding.get('limitations'):
        issues.append({'code': 'report_provenance_limited', 'blocking': False, 'requires_review': True,
            'message': 'Original-source or executed-action context is unavailable or bounded; inspect saved provenance and limitations.'})
    return issues
