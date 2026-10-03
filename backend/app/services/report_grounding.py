"""Bounded original-source and executed-trace context for report generation.

These mechanical quotation/probability checks are not factual certification.
"""
import re
from .claim_ledger import canonical_digest
from .source_retrieval import freeze_sources
from .source_scope import resolve_source_scope
from .simulation_activity import read_activity, unique_actions, summarize_activity

CONTRACT = 'report-grounding-v1'


def build_report_grounding(storage, config, graph_id, simulation_dir):
    packet = {'report_contract': CONTRACT, 'graph_id': graph_id, 'status': 'unavailable',
              'original_sources': [], 'limitations': []}
    try:
        scope = resolve_source_scope({'graph_id': graph_id}, config)
        packet.update(scope)
        corpus = freeze_sources(storage.get_source_chunks(**scope), scope)
        # Embeddings are retrieval machinery, not report evidence or prompt data.
        sources, used = [], 0
        for row in corpus['sources']:
            if used + len(row['excerpt']) > 60000:
                packet['limitations'].append('report_source_context_truncated')
                break
            sources.append({k: v for k, v in row.items() if k not in ('embedding', 'embedding_provider_id')})
            used += len(row['excerpt'])
        packet.update(original_sources=sources, source_corpus_digest=corpus['digest'],
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
    packet['simulation_activity'] = {'summary': summarize_activity(raw), 'actions': actions,
        'contract': 'initial_post and scheduled_event are scenario inputs; only model_action is a model response; unknown is unverified legacy origin'}
    packet['digest'] = canonical_digest(packet)
    return packet


def provenance_issues(content, grounding, forecast):
    if grounding.get('report_contract') != CONTRACT:
        return []
    issues = []
    sources = grounding.get('original_sources') or []
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
