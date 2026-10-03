"""Limited deterministic trace checks, not general entailment or truth scoring."""
import re

CONTRACT = 'trace-review-v1'
MAX_CONTENT = 500000
LIMITATIONS = [
    'Checks cover explicit round action counts and nearby trace author/round/origin assertions only. Quoted, hypothetical and negated statements are excluded.',
    'Arbitrary paraphrases, omissions, predictions and implied agreement require independent review.',
    'Proposal-audit findings are model judgments, not independently established facts. Up to 30 unresolved findings are displayed; full sealed provenance is retained.',
]
REF = r'\b[a-z][a-z0-9_-]*:(?:trace|legacy):\d+\b'
ACTION = r'model(?:[- ](?:driven|generated))?\s+actions?'


def proposal_review_findings(record):
    claims = {c['claim_id']: c.get('text', '') for c in record.get('ledger', [])}
    return [{'code': 'proposal_' + finding['code'], 'check_family': 'semantic_review',
             'origin': 'proposal_model_audit', 'blocking': False, 'requires_review': True,
             'message': 'The proposal audit left a finding unresolved; inspect the claim and its original sources.',
             'claim_id': finding.get('claim_id'), 'claim_text': claims.get(finding.get('claim_id'), '')[:2000],
             'proposal_id': record.get('proposal_id'), 'evidence': []}
            for finding in record.get('findings', [])[:30] if not finding.get('blocking')]


def assess_trace_claims(content, grounding):
    result = {'contract': CONTRACT, 'issues': [], 'requires_review': False,
              'coverage': {'matched_assertions': 0, 'action_context_complete': False},
              'limitations': list(LIMITATIONS)}
    if grounding.get('report_contract') != 'report-grounding-v1':
        result['limitations'].append('No frozen action-provenance contract; trace assertions were not checked.')
        return result
    activity = grounding.get('simulation_activity') or {}
    rows = [dict(r, round_num=r.get('round', r.get('round_num'))) for r in (activity.get('actions') or [])]
    models = [r for r in rows if r.get('origin') == 'model_action']
    grouped = {}
    for row in rows:
        grouped.setdefault(row.get('reference'), []).append(row)
    verified = {ref: candidates[0] for ref, candidates in grouped.items()
                if isinstance(ref, str) and re.fullmatch(REF, ref)
                and all(tuple(r.get(k) for k in ('origin', 'round_num', 'agent_name')) ==
                        tuple(candidates[0].get(k) for k in ('origin', 'round_num', 'agent_name')) for r in candidates)}
    counted_models = [r for r in verified.values() if r.get('origin') == 'model_action'
                      and type(r.get('round_num')) is int]
    summary = activity.get('summary') or {}
    complete = (summary.get('model_actions') == len(models)
                and summary.get('unknown_origin_actions') == 0
                and all(r.get('origin') in {'model_action', 'scheduled_event', 'initial_post'} for r in rows)
                and len(verified) == len(rows)
                and all(isinstance(r.get('agent_name'), str) and r['agent_name'].strip() for r in models)
                and not any(x in (grounding.get('limitations') or []) for x in
                            ('report_action_context_truncated', 'legacy_action_origins_unverified'))
                and all(isinstance(r.get('round_num'), int) and not isinstance(r['round_num'], bool) for r in models))
    result['coverage']['action_context_complete'] = complete
    if not complete:
        result['limitations'].append('Frozen actions are incomplete or lack verified origins; absence cannot disprove an action.')
    names = sorted({r.get('agent_name') for r in rows if isinstance(r.get('agent_name'), str) and r['agent_name'].strip()})
    aliases = {name: name for name in names}
    for name in names:
        first = name.split()[0]
        if sum(n.split()[0] == first for n in names) == 1:
            aliases[first] = name
    name_pattern = '|'.join(re.escape(n) for n in sorted(aliases, key=len, reverse=True)) or r'(?!)'
    references = verified

    def issue(code, sentence, paragraph, evidence=(), **detail):
        result['issues'].append({'code': code, 'check_family': 'semantic_review', 'origin': 'recorded_actions',
            'blocking': False, 'requires_review': True, 'paragraph_index': paragraph,
            'claim_text': sentence[:2000], 'message': {
                'round_action_count_conflict': 'The stated model-action count conflicts with recorded actions.',
                'trace_author_conflict': 'The named author differs from the recorded trace author.',
                'trace_round_conflict': 'The stated round differs from the recorded trace round.',
                'trace_origin_conflict': 'Scenario input and model-response origins are being confused.',
                'semantic_claim_unverified': 'The frozen context cannot verify this explicit action assertion.',
            }[code], 'evidence': [{k: r.get(k) for k in
                ('reference', 'agent_name', 'round_num', 'origin', 'action_type')} for r in evidence[:8]], **detail})

    body = re.sub(r'```[\s\S]*?```', '', content[:MAX_CONTENT])
    if len(content) > MAX_CONTENT:
        result['limitations'].append('Only the first 500,000 report characters were checked.')
    for paragraph, raw in enumerate(re.split(r'\n\s*\n', body)):
        raw = '\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith('>'))
        # Quoted speech is evidence to inspect, not the report's own assertion.
        raw = re.sub(r'["“][^"”]*["”]', '', raw)
        raw = raw.replace('`', '').replace('**', '')
        for sentence in re.split(r'(?<=[.!?])\s+|\n', raw):
            if re.search(r'\b(if|suppose|hypothetical|might|could|whether|false|incorrect|falsely|contradiction|not|never)\b', sentence, re.I):
                continue
            count = re.search(r'\bRound\s+(\d+)\s+(?:contains?|contained|has|had|includes?|included|produced)\s+(no|zero|\d+)\s+' + ACTION + r'\b([^.!?]*)', sentence, re.I)
            reverse = re.search(r'\bNo\s+' + ACTION + r'\s+(?:occurred|were recorded|were generated)\s+in\s+Round\s+(\d+)\b([^.!?]*)', sentence, re.I)
            if count or reverse:
                round_num = int((count or reverse).group(1))
                expected = 0 if reverse or count.group(2).lower() in ('no', 'zero') else int(count.group(2))
                tail = (count.group(3) if count else reverse.group(2)).strip()
                scoped = None
                if tail:
                    scope = re.fullmatch(r'from\s+(.+)', tail, re.I)
                    if scope:
                        supplied = re.split(r'\s*(?:,|\band\b|\bor\b)\s*', scope.group(1))
                        supplied = [s.strip() for s in supplied if s.strip()]
                        if supplied and all(s in aliases for s in supplied):
                            scoped = {aliases[s] for s in supplied}
                    if scoped is None:
                        continue  # Do not guess whether a qualifier narrows the claim.
                observed = [r for r in counted_models if r.get('round_num') == round_num
                            and (scoped is None or r.get('agent_name') in scoped)]
                result['coverage']['matched_assertions'] += 1
                if len(observed) > expected or (complete and len(observed) != expected):
                    issue('round_action_count_conflict', sentence, paragraph, observed,
                          round_num=round_num, claimed_count=expected, observed_count=len(observed))
                elif not complete:
                    issue('semantic_claim_unverified', sentence, paragraph, observed)
            refs = re.findall(REF, sentence, re.I)
            # Multiple references can express comparisons; never guess their binding.
            if len(refs) != 1:
                continue
            ref = refs[0]
            author = re.search(r'\b(' + name_pattern + r")(?:'s\s+(?:model\s+)?(?:post|action|response))?\s+at\s+" + re.escape(ref), sentence)
            round_claim = re.search(r'\bRound\s+(\d+)\s+(?:model\s+)?(?:action|post|response)(?:\s+(?:belongs to|by|from)\s+(?:' + name_pattern + r'))?\s+at\s+' + re.escape(ref), sentence, re.I)
            origin = re.search(r'\b(model action|scheduled (?:event|input)|initial (?:post|input))\s+at\s+' + re.escape(ref), sentence, re.I)
            if not any((author, round_claim, origin)):
                continue
            result['coverage']['matched_assertions'] += 1
            row = references.get(ref)
            if not row:
                issue('semantic_claim_unverified', sentence, paragraph, reference=ref)
                continue
            if ((author and (not isinstance(row.get('agent_name'), str) or not row['agent_name'].strip()))
                    or (round_claim and type(row.get('round_num')) is not int)
                    or (origin and row.get('origin') not in {'model_action', 'scheduled_event', 'initial_post'})):
                issue('semantic_claim_unverified', sentence, paragraph, [row])
                continue
            if author and aliases[author.group(1)] != row.get('agent_name'):
                issue('trace_author_conflict', sentence, paragraph, [row], claimed_author=aliases[author.group(1)])
            if round_claim and int(round_claim.group(1)) != row.get('round_num'):
                issue('trace_round_conflict', sentence, paragraph, [row], claimed_round=int(round_claim.group(1)))
            if origin:
                wanted = {'model': 'model_action', 'scheduled': 'scheduled_event', 'initial': 'initial_post'}[origin.group(1).split()[0].lower()]
                if wanted != row.get('origin'):
                    issue('trace_origin_conflict', sentence, paragraph, [row], claimed_origin=wanted)
    result['requires_review'] = bool(result['issues'])
    return result


def current_review(report, reports_dir):
    """Assess a saved report without changing its persisted status or sealed files."""
    import hashlib
    import json
    from pathlib import Path
    from .proposal_store import ID, proposal_digest
    result = assess_trace_claims(report.markdown_content or '', report.source_grounding)
    if report.revision.get('immutable'):
        try:
            if not ID.fullmatch(report.report_id):
                raise ValueError('Invalid report identifier')
            root = Path(reports_dir).resolve()
            directory = (root / report.report_id).resolve()
            if directory.parent != root:
                raise ValueError('Invalid report path')
            provenance = directory / 'provenance.json'
            manifest_path = directory / 'manifest.json'
            if provenance.is_symlink() or manifest_path.is_symlink():
                raise ValueError('Invalid provenance path')
            if provenance.stat().st_size > 2000000 or manifest_path.stat().st_size > 100000:
                raise ValueError('Oversized provenance')
            raw = provenance.read_bytes()
            manifest = json.loads(manifest_path.read_bytes())
            if hashlib.sha256(raw).hexdigest() != manifest.get('provenance.json'):
                raise ValueError('Unsealed provenance')
            record = json.loads(raw)
            if any(record.get(key) != report.revision.get(key) for key in ('proposal_id', 'proposal_digest')):
                raise ValueError('Provenance identity mismatch')
            if proposal_digest(record) != record.get('proposal_digest'):
                raise ValueError('Proposal digest mismatch')
            result['issues'].extend(proposal_review_findings(record))
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            result['issues'].append({'code': 'proposal_review_unverified', 'check_family': 'semantic_review',
                'origin': 'proposal_provenance', 'blocking': False, 'requires_review': True,
                'message': 'Sealed proposal provenance is unavailable or invalid; unresolved audit findings cannot be checked.',
                'claim_text': '', 'evidence': []})
    result['requires_review'] = any(i.get('requires_review') for i in result['issues'])
    result['saved_status'] = report.status.value
    return result
