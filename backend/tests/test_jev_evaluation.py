import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('evaluate_jev', Path(__file__).parents[1] / 'scripts/evaluate_jev.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
evaluate_records = module.evaluate_records


def test_counts_false_supported_claims():
    result = evaluate_records([{'expected': 'contradicted', 'predicted': 'supported'},
                               {'expected': 'supported', 'predicted': 'supported'}])
    assert result['correct'] == 1
    assert result['false_supported'] == 1
    assert result['false_supported_rate'] == .5


def test_empty_and_skipped_are_not_incorrect():
    assert evaluate_records([])['accuracy'] is None
    result = evaluate_records([{'expected': 'supported', 'status': 'unavailable'},
                               {'nonsense': True}, {'expected': 'supported', 'predicted': 'contradicted'}])
    assert result['skipped'] == 1
    assert result['invalid'] == 1
    assert result['incorrect'] == 1
    assert result['fallback_rate'] == .5


def test_candidate_recall_is_separate_from_ranking_quality():
    result = evaluate_records([{'feature': 'reranking', 'case_id': 'a', 'expected': ['a', 'b'],
                               'predicted': ['a'], 'shortlist_ids': ['a'], 'relevance': {'a': 3, 'b': 3}}])
    assert result['recall_at_30'] == .5
    assert 0 < result['ndcg_at_10'] < 1


def test_interview_precision_diversity_and_latency():
    result = evaluate_records([{'feature': 'interviews', 'expected': ['a'], 'predicted': ['a', 'b'],
                               'professions': {'a': 'engineer', 'b': 'resident'}, 'elapsed_ms': 100,
                               'usage': {'input_tokens': 20, 'output_tokens': 3}, 'cache_hit': True}])
    assert result['interview_precision'] == .5
    assert result['profession_diversity'] == 1
    assert result['latency_ms']['p95'] == 100
    assert result['usage']['input_tokens'] == 20
    assert result['cache_hit_rate'] == 1


def test_status_snapshot_never_contains_credentials(monkeypatch):
    from app.config import Config
    from app.services.jev_policy import decision_configuration
    monkeypatch.setattr(Config, 'TYPESAFE_API_KEY', 'super-secret')
    monkeypatch.setattr(Config, 'JEV_EVIDENCE_MODE', 'shadow')
    data = decision_configuration()
    assert 'super-secret' not in str(data)
    assert data['features']['evidence']['mode'] == 'shadow'
    assert data['features']['evidence']['available'] is True


def test_recall_includes_unavailable_decisions():
    result = evaluate_records([
        {'feature': 'reranking', 'expected': ['a'], 'predicted': ['a'], 'shortlist_ids': ['a']},
        {'feature': 'reranking', 'expected': ['b'], 'predicted': None, 'shortlist_ids': [], 'status': 'unavailable'},
    ])
    assert result['recall_at_30'] == .5
    assert result['skipped'] == 1


def test_nested_malformed_records_are_counted_without_crashing():
    records = [
        {'expected': ['a'], 'predicted': ['a'], 'usage': None},
        {'feature': 'reranking', 'expected': [{}], 'predicted': []},
        {'expected': 'supported', 'predicted': 'supported', 'elapsed_ms': float('nan')},
        {'feature': 'reranking', 'expected': ['a'], 'predicted': ['a'], 'relevance': {'a': 'high'}},
        {'expected': 'supported', 'predicted': 'supported'},
    ]
    result = evaluate_records(records)
    assert result['invalid'] == 4
    assert result['correct'] == 1
