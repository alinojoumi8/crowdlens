"""Durable, aggregate physical-request admission. See docs/workflow-execution.md.

WorkflowHalt deliberately bypasses application fallback/retry `except Exception`
blocks. It is handled at HTTP, task-thread, and simulation boundaries, so a
control decision cannot turn into an unmetered fallback or a successful report.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
from functools import wraps
import inspect
from .workflow_spend import price_terms, micro_usd, estimated_micro_usd, token_counts

_SCOPE = ContextVar('workflow_execution', default=None)
_ISSUER = ContextVar('workflow_issuing_owner', default=None)
_ALLOW_UNSCOPED = False  # Test-only injection; HTTP/CLI generation requires a scope.


class WorkflowHalt(BaseException):
    def __init__(self, reason, workflow_id=None):
        self.reason, self.workflow_id = reason, workflow_id
        super().__init__(reason)


def endpoint_identity(base_url):
    value = (base_url or '').rstrip('/')
    for suffix in ('/v1/messages', '/chat/completions', '/v1'):
        if value.endswith(suffix):
            value = value[:-len(suffix)]
    return hashlib.sha256(value.encode()).hexdigest()


class WorkflowLedger:
    def __init__(self, path, *, clock=time.time):
        self.path = str(Path(path).resolve())
        self.clock = clock
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS workflows ('
                       'workflow_id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS workflow_resources ('
                       'resource_key TEXT PRIMARY KEY, workflow_id TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS workflow_requests ('
                       'request_id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, payload TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS workflow_request_root ON workflow_requests(workflow_id)')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA busy_timeout=30000')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _read(db, wid):
        row = db.execute('SELECT payload FROM workflows WHERE workflow_id=?', (wid,)).fetchone()
        if not row:
            raise WorkflowHalt('authorization_required', wid)
        return json.loads(row[0])

    @staticmethod
    def _save(db, record):
        db.execute('UPDATE workflows SET payload=? WHERE workflow_id=?',
                   (json.dumps(record), record['workflow_id']))

    def _expire(self, record):
        if record['state'] in ('authorized', 'request_limit', 'spend_limit', 'spend_estimate_exceeded') and record.get('deadline_at') is not None:
            if self.clock() >= record['deadline_at']:
                record['state'] = 'runtime_limit'
                record['reason'] = 'runtime_limit'

    @staticmethod
    def _limits(max_requests, max_seconds, confirmed):
        if confirmed is not True:
            raise ValueError('explicit_confirmation_required')
        if type(max_requests) is not int or not 1 <= max_requests <= 100000:
            raise ValueError('invalid_max_requests')
        if type(max_seconds) is not int or not 1 <= max_seconds <= 86400:
            raise ValueError('invalid_max_seconds')

    def authorize(self, *, request_key, provider, model, base_url, input_description,
                  max_requests, max_seconds, confirmed, consumed_requests=0, input_fingerprint=None, resources=(), spend=None):
        self._limits(max_requests, max_seconds, confirmed)
        if not all(isinstance(x, str) and 0 < len(x) <= 500 for x in
                   (request_key, provider, model, base_url, input_description)):
            raise ValueError('invalid_authorization_identity')
        if type(consumed_requests) is not int or not 0 <= consumed_requests < max_requests:
            raise ValueError('invalid_consumed_requests')
        identity = dict(provider=provider, model=model, endpoint_identity=endpoint_identity(base_url),
                        input_description=input_description, max_requests=max_requests,
                        max_seconds=max_seconds, imported_requests=consumed_requests, input_fingerprint=input_fingerprint)
        if spend is not None:
            if consumed_requests:
                raise ValueError('legacy_usage_cannot_be_priced')
            identity['spend'] = price_terms(spend)
        if input_fingerprint is not None and (not isinstance(input_fingerprint, str) or len(input_fingerprint) != 64
                or any(c not in '0123456789abcdef' for c in input_fingerprint)):
            raise ValueError('invalid_input_fingerprint')
        with self.transaction() as db:
            row = db.execute('SELECT payload FROM workflows WHERE request_key=?', (request_key,)).fetchone()
            if row:
                old = json.loads(row[0])
                if old['initial_authorization'] != identity:
                    raise ValueError('authorization_key_conflict')
                for resource in resources:
                    self._bind(db, old['workflow_id'], resource)
                return old
            record = dict(identity, workflow_id='wf_' + uuid.uuid4().hex, request_key=request_key,
                          initial_authorization=identity, authorizations=[dict(identity, at=self.clock(), epoch=1)],
                          state='authorized', reason=None, epoch=1, admitted=consumed_requests,
                          created_at=self.clock(), started_at=None, deadline_at=None)
            if spend is not None:
                record['spend'] = dict(identity['spend'], estimated_micro_usd=0, reserved_micro_usd=0, overrun_attempts=0)
            db.execute('INSERT INTO workflows VALUES(?,?,?)',
                       (record['workflow_id'], request_key, json.dumps(record)))
            for resource in resources:
                self._bind(db, record['workflow_id'], resource)
        return record

    @staticmethod
    def _bind(db, wid, resource):
        row = db.execute('SELECT workflow_id FROM workflow_resources WHERE resource_key=?', (resource,)).fetchone()
        if row and row[0] != wid:
            raise ValueError('resource_has_different_authorization')
        db.execute('INSERT OR IGNORE INTO workflow_resources VALUES(?,?)', (resource, wid))

    def bind(self, wid, resource):
        with self.transaction() as db:
            self._read(db, wid)
            self._bind(db, wid, resource)

    def resolve(self, resource):
        with self.transaction() as db:
            row = db.execute('SELECT workflow_id FROM workflow_resources WHERE resource_key=?', (resource,)).fetchone()
            return row[0] if row else None

    def resources(self, wid):
        with self.transaction() as db:
            return [row[0] for row in db.execute('SELECT resource_key FROM workflow_resources WHERE workflow_id=?', (wid,))]

    def checkpoint(self, wid, epoch):
        with self.transaction() as db:
            record = self._read(db, wid)
            self._expire(record)
            self._save(db, record)
        if epoch != record['epoch']:
            raise WorkflowHalt('authorization_superseded', wid)
        if record['state'] in ('stopped', 'runtime_limit', 'spend_estimate_exceeded'):
            raise WorkflowHalt(record['reason'], wid)
        return record

    def require_scheduling(self, wid, epoch):
        record = self.checkpoint(wid, epoch)
        if record['state'] != 'authorized' or record['admitted'] >= record['max_requests']:
            raise WorkflowHalt(record['reason'] or 'request_limit', wid)
        return record

    def admit(self, wid, epoch, stage, model, base_url, *, attempt_number=1, task_id=None, owner_attempt=None):
        reason, ticket = None, None
        with self.transaction() as db:
            record = self._read(db, wid)
            self._expire(record)
            if epoch != record['epoch']:
                reason = 'authorization_superseded'
            elif model != record['model'] or endpoint_identity(base_url) != record['endpoint_identity']:
                reason = 'provider_not_authorized'
            elif record['state'] != 'authorized':
                reason = record['reason'] or record['state']
            elif record['admitted'] >= record['max_requests']:
                reason = record['state'] = record['reason'] = 'request_limit'
            spend = record.get('spend')
            if reason is None and spend and (spend['estimated_micro_usd'] + spend['reserved_micro_usd']
                    + spend['reserve_micro_usd'] > spend['budget_micro_usd']):
                reason = record['state'] = record['reason'] = 'spend_limit'
            if reason is None:
                now = self.clock()
                if record['started_at'] is None:
                    record['started_at'] = now
                    record['deadline_at'] = now + record['max_seconds']
                record['admitted'] += 1
                ticket = dict(request_id='req_' + uuid.uuid4().hex, workflow_id=wid, epoch=epoch,
                    sequence=record['admitted'], stage=stage, model=model, task_id=task_id,
                    owner_attempt=owner_attempt, attempt_number=attempt_number, admitted_at=now,
                    finished_at=None, status='in_flight', usage=None, http_status=None)
                if spend:
                    ticket['spend'] = dict(reserved_micro_usd=spend['reserve_micro_usd'],
                                           estimated_micro_usd=None, reservation_exceeded=False)
                    spend['reserved_micro_usd'] += spend['reserve_micro_usd']
                db.execute('INSERT INTO workflow_requests VALUES(?,?,?)',
                           (ticket['request_id'], wid, json.dumps(ticket)))
                if record['admitted'] == record['max_requests']:
                    record['state'] = record['reason'] = 'request_limit'
            self._save(db, record)
        if reason:
            raise WorkflowHalt(reason, wid)
        return ticket

    def finish(self, ticket, *, status, usage=None, http_status=None):
        if not isinstance(usage, dict):
            usage = None
        try:
            json.dumps(usage, allow_nan=False)
        except (TypeError, ValueError):
            usage = None  # Invalid provider usage cannot release a reservation.
        with self.transaction() as db:
            row = db.execute('SELECT payload FROM workflow_requests WHERE request_id=?', (ticket['request_id'],)).fetchone()
            record = json.loads(row[0])
            if record['finished_at'] is not None:
                return
            record.update(finished_at=self.clock(), status=status, usage=usage if isinstance(usage, dict) else None, http_status=http_status)
            if record.get('spend'):
                workflow = self._read(db, record['workflow_id'])
                spend = workflow['spend']
                estimate = estimated_micro_usd(usage, spend)
                if estimate is not None:
                    reserved = record['spend']['reserved_micro_usd']
                    record['spend'].update(estimated_micro_usd=estimate, reserved_micro_usd=0,
                                          reservation_exceeded=estimate > reserved)
                    spend['reserved_micro_usd'] -= reserved
                    spend['estimated_micro_usd'] += estimate
                    if estimate > reserved:
                        spend['overrun_attempts'] += 1
                        # A bad reservation invalidates the assumptions. Never
                        # silently reopen Stop or an expired/superseded allowance.
                        if workflow['state'] not in ('stopped', 'runtime_limit'):
                            workflow['state'] = workflow['reason'] = 'spend_estimate_exceeded'
                self._save(db, workflow)
            record['elapsed_seconds'] = max(0, self.clock() - record['admitted_at'])
            db.execute('UPDATE workflow_requests SET payload=? WHERE request_id=?',
                       (json.dumps(record), record['request_id']))

    def stop(self, wid):
        with self.transaction() as db:
            record = self._read(db, wid)
            record.update(state='stopped', reason='stopped', stopped_at=self.clock())
            self._save(db, record)
        return self.status(wid)

    def reauthorize(self, wid, *, max_requests, max_seconds, confirmed,
                    acknowledge_unknown=False, request_key, budget_usd=None):
        self._limits(max_requests, max_seconds, confirmed)
        if not isinstance(request_key, str) or not 1 <= len(request_key) <= 128:
            raise ValueError('invalid_reauthorization_key')
        with self.transaction() as db:
            record = self._read(db, wid)
            terms = dict(max_requests=max_requests, max_seconds=max_seconds, request_key=request_key)
            spend = record.get('spend')
            if budget_usd is not None and not spend:
                raise ValueError('cannot_add_pricing_to_existing_workflow')
            if spend:
                if budget_usd is None:
                    raise ValueError('explicit_spend_budget_required')
                terms['budget_micro_usd'] = micro_usd(budget_usd, positive=True)
            replay = next((item for item in record['authorizations'] if item.get('request_key') == request_key), None)
            if replay:
                if any(replay[k] != v for k, v in terms.items()):
                    raise ValueError('reauthorization_key_conflict')
                return record
            if max_requests <= record['admitted']:
                raise ValueError('new_total_ceiling_must_exceed_consumed')
            if spend:
                if terms['budget_micro_usd'] < (spend['estimated_micro_usd'] + spend['reserved_micro_usd'] + spend['reserve_micro_usd']):
                    raise ValueError('budget_cannot_reserve_next_request')
                spend['budget_micro_usd'] = terms['budget_micro_usd']
            uncertain = any(json.loads(row[0])['finished_at'] is None for row in db.execute(
                'SELECT payload FROM workflow_requests WHERE workflow_id=?', (wid,)))
            if uncertain and acknowledge_unknown is not True:
                raise ValueError('acknowledge_in_flight_delivery_unknown')
            record.update(epoch=record['epoch'] + 1, state='authorized', reason=None,
                          max_requests=max_requests, max_seconds=max_seconds,
                          deadline_at=self.clock() + max_seconds)
            record['authorizations'].append(dict(terms, at=self.clock(), epoch=record['epoch'],
                acknowledge_unknown=acknowledge_unknown))
            self._save(db, record)
        return record

    def status(self, wid):
        with self.transaction() as db:
            record = self._read(db, wid)
            self._expire(record)
            self._save(db, record)
            attempts = [json.loads(row[0]) for row in db.execute(
                'SELECT payload FROM workflow_requests WHERE workflow_id=?', (wid,))]
        stages = {}
        for item in attempts:
            stage = stages.setdefault(item['stage'], dict(attempts=0, unknown_usage_attempts=0))
            stage['attempts'] += 1
            if not self.usage_complete(item['usage']):
                stage['unknown_usage_attempts'] += 1
            for key, value in (item['usage'] or {}).items():
                if type(value) is int and value >= 0:
                    stage[key] = stage.get(key, 0) + value
        record.update(remaining_requests=max(0, record['max_requests'] - record['admitted']),
            elapsed_seconds=max(0, self.clock() - record['started_at']) if record['started_at'] else 0,
            in_flight=sum(item['finished_at'] is None for item in attempts),
            finished=sum(item['finished_at'] is not None for item in attempts),
            unknown_usage_attempts=record['imported_requests'] + sum(not self.usage_complete(item['usage']) for item in attempts),
            usage_by_stage=stages, attempts=sorted(attempts, key=lambda item: item['sequence']),
            admission_closed=record['state'] != 'authorized', billing_amount=None)
        if record.get('spend'):
            spend = record['spend']
            spend['available_micro_usd'] = max(0, spend['budget_micro_usd'] - spend['estimated_micro_usd'] - spend['reserved_micro_usd'])
            spend['unpriced_attempts'] = sum(item.get('spend', {}).get('estimated_micro_usd') is None for item in attempts)
            spend['guarantee'] = 'admission_reservations_only_not_provider_billing'
        return record

    @staticmethod
    def usage_complete(usage):
        return token_counts(usage) is not None


@dataclass(frozen=True)
class ExecutionScope:
    ledger: WorkflowLedger
    workflow_id: str
    epoch: int
    stage: str

    def checkpoint(self):
        record = self.ledger.checkpoint(self.workflow_id, self.epoch)
        from .task_execution import current_attempt
        owner = current_attempt()
        if owner:
            with owner.runtime.gate():
                owner.runtime.validate(owner)
        elif os.environ.get('CROWDLENS_TASK_ID'):
            runtime = self._child_runtime()
            with runtime.gate():
                self._validate_child(runtime)
        return record

    def _child_runtime(self):
        from .task_execution import TaskRuntime
        from ..storage.control_db import ControlDatabase
        return TaskRuntime(ControlDatabase(self.ledger.path))

    def _validate_child(self, runtime):
        from .task_execution import OwnershipLost
        try:
            runtime.validate_child(os.environ['CROWDLENS_TASK_ID'], os.environ['CROWDLENS_OWNER_ATTEMPT'],
                                   json.loads(os.environ['CROWDLENS_TASK_OWNER']))
            issuer = _ISSUER.get()
            if issuer:
                runtime.validate_child(issuer['task_id'], issuer['attempt_id'], issuer['owner'])
        except OwnershipLost:
            raise WorkflowHalt('task_ownership_lost', self.workflow_id)

    def admit(self, model, base_url, attempt_number):
        from .task_execution import current_attempt
        owner = current_attempt()
        if owner:
            with owner.runtime.gate():
                owner.runtime.validate(owner)
                return self.ledger.admit(self.workflow_id, self.epoch, self.stage, model, base_url,
                    attempt_number=attempt_number, task_id=owner.task_id, owner_attempt=owner.attempt_id)
        child_task = os.environ.get('CROWDLENS_TASK_ID')
        if child_task:
            runtime = self._child_runtime()
            with runtime.gate():
                self._validate_child(runtime)
                issuer = _ISSUER.get()
                return self.ledger.admit(self.workflow_id, self.epoch, self.stage, model, base_url,
                    attempt_number=attempt_number, task_id=issuer['task_id'] if issuer else child_task,
                    owner_attempt=issuer['attempt_id'] if issuer else os.environ['CROWDLENS_OWNER_ATTEMPT'])
        return self.ledger.admit(self.workflow_id, self.epoch, self.stage, model, base_url,
                                attempt_number=attempt_number)

    def child_env(self):
        result = dict(CROWDLENS_WORKFLOW_DB=self.ledger.path, CROWDLENS_WORKFLOW_ID=self.workflow_id,
                    CROWDLENS_WORKFLOW_EPOCH=str(self.epoch), CROWDLENS_WORKFLOW_STAGE='simulation')
        from .task_execution import current_attempt
        owner = current_attempt()
        if owner:
            result.update(CROWDLENS_TASK_ID=owner.task_id, CROWDLENS_OWNER_ATTEMPT=owner.attempt_id,
                          CROWDLENS_TASK_OWNER=json.dumps(owner.runtime.owner))
        return result


def current_scope():
    scope = _SCOPE.get()
    if scope is False:
        return None
    if scope is not None:
        return scope
    wid = os.environ.get('CROWDLENS_WORKFLOW_ID')
    if wid:
        return ExecutionScope(WorkflowLedger(os.environ['CROWDLENS_WORKFLOW_DB']), wid,
            int(os.environ['CROWDLENS_WORKFLOW_EPOCH']), os.environ.get('CROWDLENS_WORKFLOW_STAGE', 'simulation'))
    return None


@contextmanager
def without_execution_scope():
    token = _SCOPE.set(False)
    try:
        yield
    finally:
        _SCOPE.reset(token)


@contextmanager
def execution_scope(ledger, wid, stage, *, epoch=None):
    scope = ExecutionScope(ledger, wid, epoch or ledger.status(wid)['epoch'], stage)
    token = _SCOPE.set(scope)
    try:
        yield scope
    finally:
        _SCOPE.reset(token)


@contextmanager
def transport_attempt(model, base_url, attempt_number=1):
    scope = current_scope()
    if scope is None and not _ALLOW_UNSCOPED:
        raise WorkflowHalt('authorization_required')
    ticket = scope.admit(model, base_url, attempt_number) if scope else None
    receipt = dict(usage=None, http_status=None)
    try:
        yield receipt
    except BaseException:
        if ticket:
            scope.ledger.finish(ticket, status='delivery_or_usage_unknown', **receipt)
        raise
    else:
        if ticket:
            scope.ledger.finish(ticket, status='response', **receipt)
    if scope:
        scope.checkpoint()


def workflow_stage(stage):
    """Keep stage labels through threads and asyncio.to_thread without global env mutation."""
    def decorate(function):
        @contextmanager
        def bind():
            scope = current_scope()
            if scope and scope.workflow_id:
                with execution_scope(scope.ledger, scope.workflow_id, stage, epoch=scope.epoch):
                    yield
            else:
                yield
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def wrapped(*args, **kwargs):
                with bind():
                    return await function(*args, **kwargs)
        else:
            @wraps(function)
            def wrapped(*args, **kwargs):
                with bind():
                    return function(*args, **kwargs)
        return wrapped
    return decorate


def ipc_authorization(simulation_id):
    """Reject legacy/old-epoch environments rather than authorize them by polling."""
    scope = current_scope()
    if not scope or not scope.workflow_id:
        if _ALLOW_UNSCOPED:
            return None
        raise WorkflowHalt('interview_authorization_required')
    from .simulation_runner import SimulationRunner
    execution = getattr(SimulationRunner.get_run_state(simulation_id), 'execution', {}) or {}
    if execution.get('workflow_id') != scope.workflow_id or execution.get('workflow_epoch') != scope.epoch:
        raise WorkflowHalt('simulation_environment_authorization_unavailable', scope.workflow_id)
    scope.ledger.require_scheduling(scope.workflow_id, scope.epoch)
    from .task_execution import current_attempt
    owner = current_attempt()
    if owner:
        with owner.runtime.gate():
            owner.runtime.validate(owner)
    return dict(workflow_id=scope.workflow_id, epoch=scope.epoch,
        issuer=dict(task_id=owner.task_id, attempt_id=owner.attempt_id, owner=owner.runtime.owner) if owner else None)


@contextmanager
def ipc_execution_context(command):
    if command.get('command_type') not in ('interview', 'batch_interview'):
        yield
        return
    scope = current_scope()
    identity = (command.get('args') or {}).get('workflow_execution')
    if not scope or not identity or identity.get('workflow_id') != scope.workflow_id or identity.get('epoch') != scope.epoch:
        raise WorkflowHalt('interview_authorization_required', scope.workflow_id if scope else None)
    token = _ISSUER.set(identity.get('issuer'))
    try:
        with execution_scope(scope.ledger, scope.workflow_id, 'interview', epoch=scope.epoch):
            yield
    finally:
        _ISSUER.reset(token)
