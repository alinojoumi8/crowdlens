import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from app.services.decision_gateway import DecisionGateway
from app.services.decision_records import DecisionRecords, decision_key

QUESTIONS = {
    'rank': {'type': 'score', 'instructions': 'Relevance', 'criteria': ['none', 'some', 'direct']},
    'verify': {'type': 'choice', 'instructions': 'Support', 'criteria': {'yes': 'supported', 'no': 'unsupported'}},
    'present': {'type': 'noul', 'instructions': 'Present?', 'criteria': {'true': 'present', 'false': 'absent'}},
}
BODY = {'model': 'jev-1.13.0', 'answers': {
    'rank': {'type': 'score', 'score': 1.5, 'confidence': .5, 'legend': {'0': 'none', '1': 'some', '2': 'direct'}, 'probabilities': {'0': 0, '1': .5, '2': .5}},
    'verify': {'type': 'choice', 'choice': 'yes', 'confidence': .9, 'probabilities': {'yes': .9, 'no': .1}},
    'present': {'type': 'noul', 'noul': .8},
}, 'usage': {'input_tokens': 100, 'output_tokens': 20}}

class Response:
    status_code = 200
    def __init__(self, body=None, status=200):
        self.body = copy.deepcopy(BODY if body is None else body)
        self.status_code = status
    def json(self):
        return self.body


def gateway(post):
    return DecisionGateway(api_key='secret-test-key', model='jev-1.13.0', post=post)


def test_disabled_and_missing_key_never_call_network():
    def forbidden(*a, **kw):
        pytest.fail('network called')
    assert gateway(forbidden).evaluate(state={}, questions={}, mode='off').status == 'disabled'
    assert DecisionGateway('', 'jev-1.13.0', post=forbidden).evaluate(state={}, questions=QUESTIONS, mode='on').status == 'unavailable'


def test_valid_contract():
    calls = []
    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()
    result = gateway(post).evaluate(state={'text': 'abc'}, questions=QUESTIONS, mode='shadow')
    assert result.status == 'ok'
    assert result.answers == BODY['answers']
    assert result.usage == BODY['usage']
    assert len(calls) == 1
    assert calls[0][0] == 'https://api.typesafe.ai/v1/systemone'
    assert calls[0][1]['timeout'] == 3


@pytest.mark.parametrize('status', [401, 422, 429, 529])
def test_http_errors_are_safe_single_attempt(status):
    calls = []
    def post(*a, **kw):
        calls.append(1)
        return Response({'error': 'secret-test-key'}, status)
    result = gateway(post).evaluate(state={}, questions=QUESTIONS, mode='on')
    assert result.status == 'unavailable'
    assert 'secret-test-key' not in repr(result)
    assert len(calls) == 1


@pytest.mark.parametrize('error', [requests.Timeout('secret-test-key'), ValueError('secret-test-key')])
def test_exceptions_are_redacted(error):
    def fail(*a, **kw):
        raise error
    result = gateway(fail).evaluate(state={}, questions=QUESTIONS, mode='on')
    assert result.status in {'unavailable', 'invalid'}
    assert 'secret-test-key' not in repr(result)


@pytest.mark.parametrize('mutation', [
    lambda b: b['answers'].pop('rank'),
    lambda b: b['answers'].update(extra=b['answers']['rank']),
    lambda b: b.update(model='different'),
    lambda b: b['answers']['verify'].update(choice='unknown'),
    lambda b: b['answers']['verify']['probabilities'].pop('no'),
    lambda b: b['answers']['verify']['probabilities'].update(yes=float('nan')),
    lambda b: b['answers']['verify']['probabilities'].update(yes=-.1, no=1.1),
    lambda b: b['answers']['verify']['probabilities'].update(yes=.1),
    lambda b: b['answers']['rank'].update(score=3),
    lambda b: b['answers']['rank'].update(score=float('inf')),
    lambda b: b['answers']['rank'].update(legend={'0': 'wrong'}),
    lambda b: b['answers']['rank'].update(type='choice'),
    lambda b: b['answers']['present'].update(confidence=.9),
    lambda b: b['answers']['present'].update(noul=True),
])
def test_invalid_answers_rejected_atomically(mutation):
    body = copy.deepcopy(BODY)
    mutation(body)
    result = gateway(lambda *a, **kw: Response(body)).evaluate(state={}, questions=QUESTIONS, mode='on')
    assert result.status == 'invalid'
    assert result.answers == {}


@pytest.mark.parametrize('state,questions', [({'text': 'x' * 24001}, QUESTIONS), ({'candidates': [{}] * 31}, QUESTIONS), ({}, {str(i): QUESTIONS['rank'] for i in range(65)}), ({}, {'q': {**QUESTIONS['rank'], 'instructions': 'x' * 48001}})])
def test_request_budget_prevents_network(state, questions):
    def forbidden(*a, **kw):
        pytest.fail('network called')
    assert gateway(forbidden).evaluate(state=state, questions=questions, mode='on').status == 'budget_exceeded'


def test_cache_key_covers_scope_model_policy_and_input():
    args = dict(state={'text': 'A'}, questions=QUESTIONS, model='jev-1.13.0', policy_version='v1', scope={'case_version': '1'})
    original = decision_key(**args)
    for k, v in [('scope', {'case_version': '2'}), ('model', 'new'), ('policy_version', 'v2'), ('state', {'text': 'B'}), ('questions', {})]:
        assert decision_key(**{**args, k: v}) != original
    assert decision_key(**args) == original


def test_atomic_records_discard_raw_source_and_secrets(tmp_path):
    records = DecisionRecords(tmp_path)
    def write(i):
        records.write({'decision_id': str(i), 'status': 'ok', 'api_key': 'secret-test-key', 'state': {'private': 'source'}, 'answers': BODY['answers']})
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(write, range(12)))
    files = list(tmp_path.glob('*.json'))
    assert len(files) == 12
    for path in files:
        data = json.loads(path.read_text())
        assert data['status'] == 'ok'
        assert 'secret-test-key' not in path.read_text()
        assert 'private' not in path.read_text()
    assert not list(tmp_path.glob('*.tmp'))


def test_runner_caches_only_success_and_rejects_non_json_state(tmp_path):
    from app.services.decision_records import DecisionRunner
    calls = []
    def post(*args, **kwargs):
        calls.append(1)
        return Response(status=429 if len(calls) == 1 else 200)
    runner = DecisionRunner({'graph_id': 'g', 'case_version_id': 'v1'}, gateway(post), DecisionRecords(tmp_path))
    args = dict(feature='test', policy_version='v1', state={}, questions=QUESTIONS, mode='shadow')
    assert runner.evaluate(**args).status == 'unavailable'
    assert runner.evaluate(**args).status == 'ok'
    assert runner.evaluate(**args).status == 'ok'
    assert len(calls) == 2
    assert runner.evaluate(**{**args, 'state': {'bad': float('nan')}}).status == 'invalid'
    assert len(calls) == 2
