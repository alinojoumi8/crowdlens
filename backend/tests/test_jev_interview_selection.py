import json
from app.config import Config
from app.services.decision_gateway import DecisionResult
from app.services.decision_records import DecisionRecords
from app.services.graph_tools import GraphToolsService
from app.services.interview_selection import build_interview_questions, select_interview_indices


def test_relevance_precedes_profession_coverage_and_zero_limit():
    profiles = [{'profession': p} for p in ['engineer', 'engineer', 'resident', '律师']]
    answers = {f'fit_{i}': {'score': s} for i, s in enumerate([3, 2.5, 2, 2])}
    assert select_interview_indices(profiles, answers, 3) == [0, 1, 2]
    assert select_interview_indices(profiles, answers, 0) == []
    assert select_interview_indices(profiles, answers, 8) == [0, 1, 2, 3]
    assert select_interview_indices([], {}, 2) == []


def test_invalid_and_irrelevant_return_no_proposal():
    profiles = [{'id': 'same'}, {'id': 'same'}]
    assert select_interview_indices(profiles, {'fit_0': {'score': 0}, 'fit_1': {'score': 0}}, 2) == []
    assert select_interview_indices(profiles, {'fit_0': {'score': 3}}, 2) == []
    assert select_interview_indices(profiles * 16, {}, 2) == []
    assert 'candidates[0]' in build_interview_questions(profiles)['fit_0']['instructions']


class Baseline:
    def chat_json(self, **kwargs):
        return {'selected_indices': [1], 'reasoning': 'baseline reason'}


class Runner:
    scope = {}
    def __init__(self, tmp_path, status='ok'):
        self.records = DecisionRecords(tmp_path)
        self.status = status
    def evaluate(self, **kwargs):
        return DecisionResult(self.status, model='jev-1.13.0', answers={'fit_0': {'score': 3}, 'fit_1': {'score': 1}})


def test_shadow_preserves_baseline_and_records_comparison(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, 'JEV_INTERVIEW_MODE', 'shadow')
    service = GraphToolsService(None, Baseline())
    runner = Runner(tmp_path)
    monkeypatch.setattr(service, '_decisions', lambda **kw: runner)
    profiles = [{'profession': 'engineer'}, {'profession': 'resident'}]
    assert service._select_agents_for_interview(profiles, 'topic', '', 1) == ([profiles[1]], [1], 'baseline reason')
    comparison = json.loads(next(tmp_path.glob('*.json')).read_text())
    assert comparison['selected_ids'] == [0]
    assert comparison['baseline_ids'] == [1]


def test_failure_uses_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, 'JEV_INTERVIEW_MODE', 'on')
    service = GraphToolsService(None, Baseline())
    monkeypatch.setattr(service, '_decisions', lambda **kw: Runner(tmp_path, 'unavailable'))
    profiles = [{'profession': 'engineer'}, {'profession': 'resident'}]
    assert service._select_agents_for_interview(profiles, 'topic', '', 1)[1] == [1]


def test_full_population_is_scored_and_original_indices_survive(tmp_path):
    from app.services.interview_selection import evaluate_population, select_interview_indices
    class BatchRunner(Runner):
        def __init__(self): super().__init__(tmp_path); self.seen=[]
        def evaluate(self, **kw):
            ids=kw['candidate_ids'];self.seen.extend(ids)
            assert len(ids)<=30
            return DecisionResult('ok', model='jev-test', answers={f'fit_{i}':{'score': 3 if original==196 else .7} for i,original in enumerate(ids)})
    runner=BatchRunner();profiles=[{'realname':f'Person {i}'} for i in range(197)]
    result=evaluate_population(profiles,'Find participant 196','case',mode='shadow',runner=runner)
    assert runner.seen==list(range(197))
    assert select_interview_indices(profiles,result.answers,1)==[196]


def test_partial_batch_failure_discards_entire_panel(tmp_path):
    from app.services.interview_selection import evaluate_population
    class PartialRunner(Runner):
        calls=0
        def evaluate(self, **kw):
            self.calls+=1
            if self.calls==2:return DecisionResult('unavailable',reason='timeout')
            return DecisionResult('ok',answers={k:{'score':3} for k in kw['questions']})
    result=evaluate_population([{}]*61,'topic','context',mode='on',runner=PartialRunner(tmp_path))
    assert result.status=='unavailable' and not result.answers


def test_population_budget_is_explicit_and_makes_no_partial_calls(tmp_path):
    from app.services.interview_selection import evaluate_population
    class Forbidden:
        def evaluate(self, **kw): raise AssertionError('must not call provider')
    result=evaluate_population([{}]*301,'topic','context',mode='shadow',runner=Forbidden())
    assert result.status=='budget_exceeded' and result.reason=='population_limit'


def test_full_population_shadow_preserves_baseline_and_logs_all_ids(tmp_path):
    from app.services.interview_selection import choose_interviews
    class FullRunner(Runner):
        def evaluate(self, **kw):
            return DecisionResult('ok', answers={k: {'score': 2} for k in kw['questions']})
    profiles=[{'realname': str(i)} for i in range(197)]
    baseline=([profiles[196]],[196],'original')
    result=choose_interviews(profiles=profiles,interview_requirement='topic',simulation_requirement='case',
                             max_agents=2,mode='shadow',runner=FullRunner(tmp_path),baseline=lambda:baseline)
    assert result==baseline
    record=json.loads(next(tmp_path.glob('*.json')).read_text())
    assert record['candidate_ids']==list(range(197)) and record['selected_ids']==[0,1]


def test_oversized_context_is_rejected_before_any_network_request(tmp_path):
    from app.services.interview_selection import evaluate_population
    class Forbidden:
        def evaluate(self, **kw): raise AssertionError('network')
    assert evaluate_population([{}]*197,'topic','x'*25000,mode='shadow',runner=Forbidden()).reason=='request_limit'


def test_batches_reference_stable_named_candidates_not_array_offsets(tmp_path):
    from app.services.interview_selection import evaluate_population
    class InspectRunner(Runner):
        def evaluate(self, **kw):
            for i, identity in enumerate(kw['candidate_ids']):
                key=f'agent_{identity}'
                assert kw['state']['candidates'][key]['index']==identity
                assert f'candidates.{key}' in kw['questions'][f'fit_{i}']['instructions']
            return DecisionResult('ok',answers={k:{'score':1} for k in kw['questions']})
    assert evaluate_population([{}]*61,'topic','context',mode='shadow',runner=InspectRunner(tmp_path)).status=='ok'
