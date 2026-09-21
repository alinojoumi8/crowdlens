"""Bounded full-population relevance scoring with atomic fallback."""
import math
import time

from .decision_gateway import DecisionResult, request_within_limits

POLICY_VERSION = 'interview-v3'
MAX_POPULATION = 300
MAX_BATCHES = 16
BATCH_DEADLINE_SECONDS = 20
CRITERIA = [
    'No demonstrated connection to the topic.',
    'Indirectly affected, with only general background knowledge.',
    'Directly affected or has relevant subject expertise.',
    'Direct participant with specific knowledge central to the requested interview.',
]
# Provisional floor for shadow observations, not a calibrated domain threshold.
MIN_SCORE = .5


def build_interview_questions(profiles, *, keyed=False):
    questions = {}
    for i, profile in enumerate(profiles):
        path = f"candidates.agent_{profile['index']}" if keyed else f"candidates[{i}]"
        questions[f'fit_{i}'] = {
            'type': 'score',
            'instructions': f'How relevant is `{path}` to `interview_requirement` in `simulation_requirement`? '
                            'Judge only demonstrated topic knowledge, not agreement or stance. '
                            'Apply the absolute criteria independently; do not adjust scores based on who else appears in the batch.',
            'criteria': CRITERIA,
        }
    return questions


def select_interview_indices(profiles, answers, max_agents):
    if max_agents <= 0 or not profiles or len(profiles) > MAX_POPULATION or set(answers) != {f'fit_{i}' for i in range(len(profiles))}:
        return []
    scores = [answers[f'fit_{i}'].get('score') for i in range(len(profiles))]
    if any(type(s) not in (int, float) or not 0 <= s <= 3 or not math.isfinite(s) for s in scores):
        return []
    ranked = sorted((i for i, s in enumerate(scores) if s >= MIN_SCORE), key=lambda i: (-scores[i], i))
    # Profession diversity must not displace a more relevant identified party.
    return ranked[:max_agents]


def evaluate_population(profiles, interview_requirement, simulation_requirement, *, mode, runner):
    """Score every candidate in bounded requests, or reject the entire proposal."""
    from ..config import Config
    started = time.monotonic()
    model = getattr(getattr(runner, 'gateway', None), 'model', Config.TYPESAFE_MODEL)
    if mode == 'off':
        return DecisionResult('disabled', model=model)
    if len(profiles) > MAX_POPULATION:
        return DecisionResult('budget_exceeded', model=model, reason='population_limit')
    candidates = [{'index': i, 'name': p.get('realname') or p.get('name') or p.get('username') or f'Agent_{i}',
                   'profession': p.get('profession', 'Unknown'), 'bio': str(p.get('bio', ''))[:200],
                   'interested_topics': p.get('interested_topics', [])} for i, p in enumerate(profiles)]
    context = {'interview_requirement': interview_requirement, 'simulation_requirement': simulation_requirement}
    batches, current = [], []
    def fits(batch):
        try:
            return request_within_limits(state={**context, 'candidates': {f"agent_{c['index']}": c for c in batch}},
                                         questions=build_interview_questions(batch, keyed=True), model=model)
        except (ValueError, TypeError):
            return False
    # Admit the entire population before issuing any requests.
    for candidate in candidates:
        if current and not fits(current + [candidate]):
            batches.append(current); current = []
        if not fits([candidate]):
            return DecisionResult('budget_exceeded', model=model, reason='request_limit')
        current.append(candidate)
    if current:
        batches.append(current)
    if len(batches) > MAX_BATCHES:
        return DecisionResult('budget_exceeded', model=model, reason='batch_limit')
    answers, usage = {}, {}
    for batch in batches:
        if time.monotonic() - started >= BATCH_DEADLINE_SECONDS:
            return DecisionResult('unavailable', model=model, reason='population_deadline')
        result = runner.evaluate(feature='interview', policy_version=POLICY_VERSION, mode=mode,
                                 state={**context, 'candidates': {f"agent_{c['index']}": c for c in batch}}, questions=build_interview_questions(batch, keyed=True),
                                 candidate_ids=[c['index'] for c in batch])
        if result.status != 'ok':
            return DecisionResult(result.status, model=model, reason='batch_failed:' + (result.reason or result.status),
                                  elapsed_ms=(time.monotonic() - started) * 1000)
        if set(result.answers) != {f'fit_{i}' for i in range(len(batch))}:
            return DecisionResult('invalid', model=model, reason='incomplete_population')
        for i, candidate in enumerate(batch):
            answers[f"fit_{candidate['index']}"] = result.answers[f'fit_{i}']
        for key, value in result.usage.items():
            usage[key] = usage.get(key, 0) + value
    if time.monotonic() - started >= BATCH_DEADLINE_SECONDS:
        return DecisionResult('unavailable', model=model, reason='population_deadline')
    return DecisionResult('ok', model=model, answers=answers, usage=usage,
                          elapsed_ms=(time.monotonic() - started) * 1000)



def choose_interviews(*, profiles, interview_requirement, simulation_requirement, max_agents, mode, runner, baseline):
    if max_agents <= 0 or not profiles:
        return [], [], 'No interview candidates requested.'
    if mode == 'off':
        return baseline()
    result = evaluate_population(profiles, interview_requirement, simulation_requirement, mode=mode, runner=runner)
    selected = select_interview_indices(profiles, result.answers, max_agents) if result.status == 'ok' else []
    if mode == 'on' and selected:
        return [profiles[i] for i in selected], selected, f'Selected {len(selected)} candidates by topic relevance across the complete population ({result.model}).'
    original = baseline()
    try:
        runner.records.write({'feature': 'interview_comparison', 'mode': mode, 'scope': runner.scope,
                              'model': result.model, 'policy_version': POLICY_VERSION,
                              'status': result.status, 'reason': result.reason or ('no_eligible_candidates' if not selected else ''),
                              'baseline_ids': original[1], 'selected_ids': selected, 'candidate_ids': list(range(len(profiles)))})
    except OSError:
        pass
    return original
