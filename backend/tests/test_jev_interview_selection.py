import json
from app.config import Config
from app.services.decision_gateway import DecisionResult
from app.services.decision_records import DecisionRecords
from app.services.graph_tools import GraphToolsService
from app.services.interview_selection import build_interview_questions, select_interview_indices


def test_unique_diverse_stable_and_zero_limit():
    profiles = [{'profession': p} for p in ['engineer', 'engineer', 'resident', '律师']]
    answers = {f'fit_{i}': {'score': s} for i, s in enumerate([3, 2.5, 2, 2])}
    assert select_interview_indices(profiles, answers, 3) == [0, 2, 3]
    assert select_interview_indices(profiles, answers, 0) == []
    assert select_interview_indices(profiles, answers, 8) == [0, 2, 3, 1]
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
