"""Interview relevance judgments; selection and profession coverage stay in code."""
import math

POLICY_VERSION = 'interview-v1'
CRITERIA = [
    'No demonstrated connection to the topic.',
    'Indirectly affected, with only general background knowledge.',
    'Directly affected or has relevant subject expertise.',
    'Direct participant with specific knowledge central to the requested interview.',
]
# Provisional floor for shadow observations, not a calibrated domain threshold.
MIN_SCORE = .5


def build_interview_questions(profiles):
    return {f'fit_{i}': {'type': 'score',
                        'instructions': f'How relevant is `candidates[{i}]` to `interview_requirement` in `simulation_requirement`? Judge only demonstrated topic knowledge, not agreement or stance.',
                        'criteria': CRITERIA} for i in range(len(profiles))}


def select_interview_indices(profiles, answers, max_agents):
    if max_agents <= 0 or not profiles or len(profiles) > 30 or set(answers) != {f'fit_{i}' for i in range(len(profiles))}:
        return []
    scores = [answers[f'fit_{i}'].get('score') for i in range(len(profiles))]
    if any(type(s) not in (int, float) or not math.isfinite(s) or not 0 <= s <= 3 for s in scores):
        return []
    ranked = sorted((i for i, s in enumerate(scores) if s >= MIN_SCORE), key=lambda i: (-scores[i], i))
    selected, professions = [], set()
    for i in ranked:
        profession = str(profiles[i].get('profession') or 'unknown').strip().casefold()
        if profession not in professions:
            selected.append(i)
            professions.add(profession)
    selected += [i for i in ranked if i not in selected]
    return selected[:max_agents]


def choose_interviews(*, profiles, interview_requirement, simulation_requirement, max_agents, mode, runner, baseline):
    if max_agents <= 0 or not profiles:
        return [], [], 'No interview candidates requested.'
    if mode == 'off':
        return baseline()
    # Never silently truncate the population: that would bias the panel.
    candidates = [{'index': i, 'name': p.get('realname', p.get('username', f'Agent_{i}')),
                   'profession': p.get('profession', 'Unknown'), 'bio': str(p.get('bio', ''))[:200],
                   'interested_topics': p.get('interested_topics', [])} for i, p in enumerate(profiles)]
    result = runner.evaluate(feature='interview', policy_version=POLICY_VERSION, mode=mode,
                             state={'interview_requirement': interview_requirement,
                                    'simulation_requirement': simulation_requirement, 'candidates': candidates},
                             questions=build_interview_questions(candidates), candidate_ids=list(range(len(profiles))))
    selected = select_interview_indices(profiles, result.answers, max_agents) if result.status == 'ok' else []
    if mode == 'on' and selected:
        return [profiles[i] for i in selected], selected, f'Selected {len(selected)} candidates by topic relevance and profession coverage ({result.model}).'
    original = baseline()
    try:
        runner.records.write({'feature': 'interview_comparison', 'mode': mode, 'scope': runner.scope,
                              'model': result.model, 'policy_version': POLICY_VERSION,
                              'status': result.status, 'reason': result.reason or ('no_eligible_candidates' if not selected else ''),
                              'baseline_ids': original[1], 'selected_ids': selected})
    except OSError:
        pass
    return original
