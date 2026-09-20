"""Scoped decision identity, safe audit records, and bounded success-only cache."""
from collections import OrderedDict
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import uuid

from .decision_gateway import DecisionGateway, canonical_json


def decision_key(*, state, questions, model, policy_version, scope):
    payload = dict(state=state, questions=questions, model=model, policy_version=policy_version, scope=scope)
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


class DecisionRecords:
    FIELDS = {'decision_id', 'key', 'feature', 'mode', 'model', 'policy_version', 'scope',
              'status', 'answers', 'usage', 'elapsed_ms', 'reason', 'cache_hit', 'candidate_ids', 'baseline_ids', 'selected_ids'}

    def __init__(self, root: Path):
        self.root = Path(root)

    def write(self, record):
        self.root.mkdir(parents=True, exist_ok=True)
        safe = {k: v for k, v in record.items() if k in self.FIELDS}
        # Legends repeat request text; retain numeric judgments only in default logs.
        safe['answers'] = {k: {a: b for a, b in v.items() if a != 'legend'} for k, v in safe.get('answers', {}).items()}
        fd, temporary = tempfile.mkstemp(prefix='.decision-', suffix='.tmp', dir=self.root)
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(canonical_json(safe))
            os.replace(temporary, self.root / f'{uuid.uuid4().hex}.json')
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


class DecisionRunner:
    """One runner per graph/report scope; inference failures always remain values."""
    def __init__(self, scope=None, gateway=None, records=None):
        from ..config import Config
        self.scope = dict(scope or {})
        self.gateway = gateway or DecisionGateway(Config.TYPESAFE_API_KEY, Config.TYPESAFE_MODEL, Config.TYPESAFE_TIMEOUT_SECONDS)
        identifier = self.scope.get('simulation_id')
        if identifier and str(identifier).replace('_', '').replace('-', '').isalnum():
            root = Path(Config.OASIS_SIMULATION_DATA_DIR) / str(identifier) / 'decisions'
        else:
            digest = hashlib.sha256(canonical_json(self.scope).encode()).hexdigest()[:24]
            root = Path(Config.UPLOAD_FOLDER) / 'decisions' / digest
        self.records = records or DecisionRecords(root)
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    def evaluate(self, *, feature, policy_version, state, questions, mode, candidate_ids=None):
        if mode == 'off':
            return self.gateway.evaluate(state=state, questions=questions, mode=mode)
        try:
            key = decision_key(state=state, questions=questions, model=self.gateway.model,
                               policy_version=policy_version, scope=self.scope)
        except (ValueError, TypeError):
            from .decision_gateway import DecisionResult
            return DecisionResult('invalid', model=self.gateway.model, reason='invalid_request')
        with self._lock:
            result = self._cache.get(key)
        hit = result is not None
        if not hit:
            result = self.gateway.evaluate(state=state, questions=questions, mode=mode)
            if result.status == 'ok':
                with self._lock:
                    self._cache[key] = result
                    while len(self._cache) > 512:
                        self._cache.popitem(last=False)
        try:
            self.records.write({**asdict(result), 'key': key, 'feature': feature, 'mode': mode,
                                'policy_version': policy_version, 'scope': self.scope,
                                'candidate_ids': candidate_ids or [], 'cache_hit': hit,
                                'decision_id': uuid.uuid4().hex})
        except OSError:
            # Audit storage failure must not break the existing report/simulation path.
            from .decision_gateway import DecisionResult
            return DecisionResult('unavailable', model=self.gateway.model, reason='record_write_failed')
        return result
