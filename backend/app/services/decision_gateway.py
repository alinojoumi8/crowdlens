"""Small, bounded TypeSafe HTTP boundary. Never logs provider bodies or retries."""
from dataclasses import dataclass, field
import json
import math
import threading
import time
from typing import Any

import requests


@dataclass(frozen=True)
class DecisionResult:
    status: str
    model: str = ''
    answers: dict[str, dict[str, Any]] = field(default_factory=dict)
    usage: dict[str, int] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    reason: str = ''


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def request_within_limits(*, state, questions, model):
    """Shared admission check for the gateway and callers packing batches."""
    payload = {'model': model, 'state': state, 'questions': questions}
    return (len(questions) <= 64 and len(state.get('candidates', [])) <= 30
            and len(canonical_json(state).encode()) <= 24000
            and len(canonical_json(payload).encode()) <= 48000)


def _number(value, lower, upper):
    return type(value) in (int, float) and lower <= value <= upper and math.isfinite(value)


def _valid_answer(question, answer):
    if not isinstance(answer, dict) or answer.get('type') != question['type']:
        return False
    kind = question['type']
    if kind == 'noul':
        return _number(answer.get('noul'), 0, 1) and 'confidence' not in answer
    if not _number(answer.get('confidence'), 0, 1):
        return False
    criteria = question['criteria']
    keys = set(criteria) if kind == 'choice' else {str(i) for i in range(len(criteria))}
    probabilities = answer.get('probabilities')
    if not isinstance(probabilities, dict) or set(probabilities) != keys:
        return False
    if not all(_number(p, 0, 1) for p in probabilities.values()) or abs(sum(probabilities.values()) - 1) > .01:
        return False
    if kind == 'choice':
        return isinstance(answer.get('choice'), str) and answer['choice'] in keys
    return (answer.get('legend') == {str(i): label for i, label in enumerate(criteria)}
            and _number(answer.get('score'), 0, len(criteria) - 1))


class DecisionGateway:
    # A process-wide cap is stricter than a per-run cap and bounds all feature calls.
    _slots = threading.BoundedSemaphore(2)

    def __init__(self, api_key, model, timeout=3.0, post=requests.post):
        self.api_key = api_key
        self.model = model
        self.timeout = max(.1, min(float(timeout), 30))
        self.post = post

    def evaluate(self, *, state, questions, mode):
        started = time.monotonic()
        def result(status, reason='', **kwargs):
            return DecisionResult(status, model=self.model, elapsed_ms=(time.monotonic() - started) * 1000, reason=reason, **kwargs)
        if mode == 'off':
            return result('disabled')
        if mode not in {'on', 'shadow'}:
            return result('invalid', 'invalid_mode')
        if not self.api_key:
            return result('unavailable', 'missing_credentials')
        try:
            payload = {'model': self.model, 'state': state, 'questions': questions}
            if not request_within_limits(state=state, questions=questions, model=self.model):
                return result('budget_exceeded', 'request_limit')
            if not questions:
                return result('invalid', 'empty_questions')
            for question in questions.values():
                kind, criteria = question['type'], question['criteria']
                if kind == 'score':
                    valid = isinstance(criteria, list) and 2 <= len(criteria) <= 10
                elif kind == 'choice':
                    valid = isinstance(criteria, dict) and 2 <= len(criteria) <= 255
                elif kind == 'noul':
                    valid = isinstance(criteria, dict) and set(criteria) == {'true', 'false'}
                else:
                    valid = False
                if not valid or not question.get('instructions'):
                    return result('invalid', 'invalid_question')
        except (ValueError, TypeError, KeyError, AttributeError):
            return result('invalid', 'invalid_request')
        if not self._slots.acquire(blocking=False):
            return result('budget_exceeded', 'concurrency_limit')
        try:
            response = self.post('https://api.typesafe.ai/v1/systemone',
                                 headers={'Authorization': f'Bearer {self.api_key}'},
                                 json=payload, timeout=self.timeout)
            if not 200 <= response.status_code < 300:
                return result('unavailable', f'http_{response.status_code}')
            body = response.json()
            answers = body.get('answers')
            if (body.get('model') != self.model or not isinstance(answers, dict)
                    or set(answers) != set(questions)
                    or not all(_valid_answer(questions[k], v) for k, v in answers.items())):
                return result('invalid', 'response_contract')
            usage = body.get('usage', {})
            if not isinstance(usage, dict) or not all(type(v) is int and v >= 0 for v in usage.values()):
                return result('invalid', 'usage_contract')
            return result('ok', answers=answers, usage=usage)
        except requests.RequestException:
            return result('unavailable', 'transport_error')
        except (ValueError, TypeError, KeyError, AttributeError):
            return result('invalid', 'response_contract')
        finally:
            self._slots.release()
