"""Reorder retrieved records without replacing source text or hybrid scores."""
import math

POLICY_VERSION = 'rerank-v1'
CRITERIA = ['Unrelated to the query.', 'Shares the topic without answering the query.',
            'Partially answers the query.', 'Directly addresses the query with specific evidence.']


def build_relevance_questions(candidates):
    return {f'relevance_{i}': {
        'type': 'score', 'criteria': CRITERIA,
        'instructions': f'How relevant is `candidates[{i}].text` to `query`, considering `time_scope`? Contradictory evidence can be directly relevant. Rank relevance, not agreement or truth.'
    } for i in range(len(candidates))}


def rank_candidates(candidates, answers, limit):
    if limit <= 0:
        return []
    if set(answers) != {f'relevance_{i}' for i in range(len(candidates))}:
        return candidates[:limit]
    scores = [answers[f'relevance_{i}'].get('score') for i in range(len(candidates))]
    if any(type(s) not in (int, float) or not math.isfinite(s) or not 0 <= s <= 3 for s in scores):
        return candidates[:limit]
    order = sorted(range(len(candidates)), key=lambda i: (-scores[i], i))[:limit]
    return [{**candidates[i], 'jev_relevance': scores[i], 'jev_policy': POLICY_VERSION} for i in order]


def rerank_evidence(candidates, query, limit, *, mode, runner, time_scope='unspecified', baseline=None):
    original = (candidates if baseline is None else baseline)[:max(0, limit)]
    if mode == 'off' or not candidates or limit <= 0 or len(candidates) > 30:
        return original
    for candidate in candidates:
        for field in ('graph_id', 'case_version_id'):
            expected = runner.scope.get(field)
            if expected and candidate.get(field) and candidate[field] != expected:
                return original
    state = {'query': query, 'time_scope': time_scope, 'candidates': [
        {'id': str(c.get('id') or c.get('uuid') or i),
         'text': str(c.get('text') or c.get('fact') or c.get('summary') or ''),
         'graph_id': c.get('graph_id', runner.scope.get('graph_id')),
         'case_version_id': c.get('case_version_id'), 'source_hash': c.get('source_hash')}
        for i, c in enumerate(candidates)]}
    result = runner.evaluate(feature='rerank', policy_version=POLICY_VERSION, mode=mode,
                             state=state, questions=build_relevance_questions(candidates),
                             candidate_ids=[c['id'] for c in state['candidates']])
    if mode != 'on' or result.status != 'ok':
        return original
    return rank_candidates(candidates, result.answers, limit)
