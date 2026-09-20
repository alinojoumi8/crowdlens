from app.config import Config
from app.services.decision_gateway import DecisionResult
from app.services.evidence_reranker import rank_candidates, rerank_evidence
from app.services.graph_tools import GraphToolsService

CANDIDATES = [
    {'id': 'hearing', 'text': 'A hearing occurred on 2 September.', 'score': .9, 'graph_id': 'g'},
    {'id': 'deadline', 'text': 'File the response by 12 October.', 'score': .4, 'graph_id': 'g'},
    {'id': 'contradiction', 'text': 'The deadline was subsequently extended.', 'score': .3, 'graph_id': 'g'},
]
ANSWERS = {f'relevance_{i}': {'score': s} for i, s in enumerate([.2, 3, 3])}


def test_rank_preserves_verbatim_and_contradictions():
    result = rank_candidates(CANDIDATES, ANSWERS, 3)
    assert [c['id'] for c in result] == ['deadline', 'contradiction', 'hearing']
    assert result[0]['text'] == CANDIDATES[1]['text']
    assert result[0]['score'] == .4
    assert 'jev_relevance' not in CANDIDATES[1]


def test_partial_answers_preserve_entire_order():
    assert rank_candidates(CANDIDATES, {'relevance_0': {'score': 3}}, 3) == CANDIDATES
    assert rank_candidates([], {}, 3) == []
    assert rank_candidates(CANDIDATES, ANSWERS, 0) == []


class Runner:
    scope = {'graph_id': 'g', 'case_version_id': 'v1'}
    def __init__(self):
        self.calls = []
    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return DecisionResult('ok', model='jev-1.13.0', answers=ANSWERS)


def test_scope_mismatch_and_off_skip_network():
    runner = Runner()
    for mode, candidates in [('off', CANDIDATES), ('on', [{**CANDIDATES[0], 'graph_id': 'other'}]), ('on', [{**CANDIDATES[0], 'case_version_id': 'old'}])]:
        result = rerank_evidence(candidates, 'query', 3, mode=mode, runner=runner)
        assert result == candidates
    assert not runner.calls


def test_shadow_retains_original_order():
    runner = Runner()
    assert rerank_evidence(CANDIDATES, 'query', 3, mode='shadow', runner=runner) == CANDIDATES
    assert runner.calls[0]['state']['candidates'][2]['text'] == CANDIDATES[2]['text']


def test_graph_integration_ranks_after_storage_returns(monkeypatch):
    monkeypatch.setattr(Config, 'JEV_RERANK_MODE', 'on')
    class Storage:
        active = False
        def search(self, **kwargs):
            self.active = True
            result = {'edges': [{**c, 'uuid': c['id'], 'fact': c['text']} for c in CANDIDATES], 'nodes': []}
            self.active = False
            return result
    storage = Storage()
    service = GraphToolsService(storage)
    runner = Runner()
    original = runner.evaluate
    def evaluate(**kwargs):
        assert not storage.active
        return original(**kwargs)
    runner.evaluate = evaluate
    monkeypatch.setattr(service, '_decisions', lambda **kw: runner)
    result = service.search_graph('g', 'What is the deadline?', 2)
    assert [e['uuid'] for e in result.edges] == ['deadline', 'contradiction']
    assert result.edges[0]['score'] == .4
