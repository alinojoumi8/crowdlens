"""Local task ownership, leased execution and serialized publication/recovery.

The SQLite payload is authoritative. A shared file lock serializes ownership
transitions with short database/filesystem/graph publication operations. Leases
are admission deadlines, not proof of process death or automatic continuation.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
import fcntl
import json
import os
from pathlib import Path
import threading
import time
import uuid

ACTIVE = {'pending', 'processing'}
LEASE_SECONDS = 30.0
RECOVERY_INTERVAL_SECONDS = 5.0
_CURRENT = ContextVar('task_attempt', default=None)
_GATES = {}
_GATES_LOCK = threading.Lock()


class OwnershipLost(RuntimeError):
    pass


class TaskBusy(RuntimeError):
    pass


def timestamp():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Attempt:
    runtime: object
    task_id: str
    attempt_id: str
    worker_id: str

    @contextmanager
    def bind(self):
        token = _CURRENT.set(self)
        try:
            yield self
        finally:
            _CURRENT.reset(token)


@contextmanager
def recovery_context():
    token = _CURRENT.set(None)
    try:
        yield
    finally:
        _CURRENT.reset(token)


def current_attempt():
    return _CURRENT.get()


@contextmanager
def publication_guard(resource=None):
    """Fence publication and ownership change under the same cross-process lock."""
    attempt = current_attempt()
    if attempt is None:
        from ..models.task import TaskManager
        runtime = TaskManager().runtime
    else:
        runtime = attempt.runtime
    with runtime.gate():
        if attempt is not None:
            runtime.validate(attempt)
        elif resource:
            binding = runtime.binding(resource)
            task = runtime.get(binding['task_id']) if binding else None
            if task and task['status'] in ACTIVE:
                raise TaskBusy('resource_has_active_task')
        yield


def fenced(function):
    """Protect a short publication performed by the current execution attempt."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with publication_guard():
            return function(*args, **kwargs)
    return wrapped


def project_write(function):
    @wraps(function)
    def wrapped(cls, project, *args, **kwargs):
        with publication_guard('project:' + project.project_id):
            return function(cls, project, *args, **kwargs)
    return wrapped


def simulation_write(function):
    @wraps(function)
    def wrapped(manager, state, *args, **kwargs):
        with publication_guard('simulation:' + state.simulation_id):
            return function(manager, state, *args, **kwargs)
    return wrapped


def report_write(function):
    @wraps(function)
    def wrapped(cls, report_or_id, *args, **kwargs):
        identifier = getattr(report_or_id, 'report_id', report_or_id)
        with publication_guard('report:' + identifier):
            return function(cls, report_or_id, *args, **kwargs)
    return wrapped


class TaskRuntime:
    def __init__(self, repository, *, clock=time.time):
        self.repository, self.clock = repository, clock
        # PID is diagnostic only; a new runtime/process always has a fresh nonce.
        self.owner = {'worker_id': uuid.uuid4().hex, 'pid': os.getpid()}
        self._memory, self._resources, self.handles, self.workers = {}, {}, {}, {}
        self._workers_lock = threading.RLock()
        self._stop = threading.Event()
        self._monitor = None
        key = (os.getpid(), str(repository.path) if repository else id(self))
        with _GATES_LOCK:
            self._mutex, self._depth = _GATES.setdefault(key, (threading.RLock(), threading.local()))

    @contextmanager
    def gate(self):
        with self._mutex:
            depth = getattr(self._depth, 'value', 0)
            lock_file = None
            if depth == 0 and self.repository:
                lock_file = open(str(self.repository.path) + '.tasks.lock', 'a+b')
                fcntl.flock(lock_file, fcntl.LOCK_EX)
            self._depth.value = depth + 1
            try:
                yield
            finally:
                self._depth.value = depth
                if lock_file:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
                    lock_file.close()

    def get(self, task_id):
        value = self.repository.get_task(task_id) if self.repository else self._memory.get(task_id)
        return json.loads(json.dumps(value)) if value else None

    def records(self):
        return (self.repository.list_tasks(limit=2147483647) if self.repository
                else list(self._memory.values()))

    def put(self, payload):
        if self.repository:
            self.repository.put_task(payload)
        else:
            self._memory[payload['task_id']] = json.loads(json.dumps(payload))

    def binding(self, key):
        if not self.repository:
            return self._resources.get(key)
        with self.repository._transaction() as connection:
            row = connection.execute('SELECT task_id, attempt_id FROM task_resources WHERE resource_key=?', (key,)).fetchone()
        return dict(row) if row else None

    def _bind_resource(self, key, attempt):
        value = {'task_id':attempt.task_id, 'attempt_id':attempt.attempt_id}
        if self.repository:
            with self.repository._transaction() as connection:
                connection.execute('INSERT INTO task_resources VALUES (?, ?, ?) ON CONFLICT(resource_key) '
                                   'DO UPDATE SET task_id=excluded.task_id, attempt_id=excluded.attempt_id',
                                   (key, attempt.task_id, attempt.attempt_id))
        else:
            self._resources[key] = value

    def admit(self, payload, resources=()):
        with self.gate():
            self.reconcile(raise_on_error=False)
            for resource in resources:
                bound = self.binding(resource['key'])
                prior = self.get(bound['task_id']) if bound else None
                if prior and (prior['status'] in ACTIVE or (prior.get('recovery') or {}).get('pending')):
                    raise TaskBusy('resource_has_active_task')
            attempt = Attempt(self, payload['task_id'], uuid.uuid4().hex, self.owner['worker_id'])
            payload = {**payload, 'execution': {'attempt_id':attempt.attempt_id,
                       'owner':dict(self.owner), 'heartbeat_at':self.clock(),
                       'lease_until':self.clock()+LEASE_SECONDS, 'resources':list(resources)}}
            self.put(payload)
            # No related state is written before all bindings are installed.
            # A crash here leaves an expiring task; repair only touches bound resources.
            for resource in resources:
                self._bind_resource(resource['key'], attempt)
            self.handles[attempt.task_id] = attempt
            return attempt

    def validate(self, attempt):
        task = self.get(attempt.task_id)
        execution = (task or {}).get('execution') or {}
        if (self.owner['pid'] != os.getpid() or attempt.runtime is not self or attempt.worker_id != self.owner['worker_id']
                or execution.get('owner', {}).get('worker_id') != attempt.worker_id
                or execution.get('attempt_id') != attempt.attempt_id
                or (task or {}).get('status') not in ACTIVE
                or execution.get('lease_until', 0) <= self.clock()):
            raise OwnershipLost('task_ownership_lost')
        for resource in execution.get('resources', []):
            if self.binding(resource['key']) != {'task_id':attempt.task_id, 'attempt_id':attempt.attempt_id}:
                raise OwnershipLost('task_attempt_replaced')
        return task

    def update(self, attempt, changes):
        with self.gate():
            task = self.validate(attempt)
            task.update(changes)
            task['updated_at'] = timestamp()
            if task['status'] == 'failed':
                task['recovery'] = {'reason':task.get('error') or 'task_failed', 'pending':True}
            self.put(task)
            return task

    def heartbeat(self, attempt):
        with self.gate():
            task = self.validate(attempt)
            task['execution'].update(heartbeat_at=self.clock(), lease_until=self.clock()+LEASE_SECONDS)
            self.put(task)

    def _owns_resource(self, task, key):
        return self.binding(key) == {'task_id':task['task_id'], 'attempt_id':task['execution']['attempt_id']}

    def _repair_related(self, task):
        """Idempotent outbox: mark task first, repair owned resources, then acknowledge."""
        from .proposal_store import atomic_json
        reason = task['recovery']['reason']
        for resource in task.get('execution', {}).get('resources', []):
            if not self._owns_resource(task, resource['key']):
                continue
            kind = resource['key'].split(':', 1)[0]
            identifier = resource['key'].split(':', 1)[1]
            if kind == 'project':
                project_path = Path(resource.get('root', '.'))/identifier/'project.json'
                project = (self.repository.get_project(identifier) if self.repository else
                           json.loads(project_path.read_text()) if project_path.exists() else None)
                if (project and project.get('graph_build_task_id') == task['task_id']
                        and project.get('status') == 'graph_building'):
                    project.update(status='failed', error=reason, updated_at=timestamp())
                    if self.repository:
                        self.repository.put_project(project)
                    else:
                        atomic_json(project_path, project)
            elif kind == 'proposal':
                from .proposal_store import ProposalStore, ProposalError
                store = ProposalStore(resource['root'])
                try:
                    store.update(identifier, {'queued','running'},
                                 {'state':'failed','error_code':reason})
                except ProposalError as exc:
                    record = store.read(identifier)
                    if record.get('state') in {'queued','running'}:
                        raise
            elif kind in {'report', 'simulation'}:
                root = Path(resource['root']).resolve()
                folder = (root/identifier).resolve()
                if folder.parent != root:
                    raise ValueError('invalid_task_resource_path')
                path = folder/('meta.json' if kind == 'report' else 'state.json')
                if not path.exists():
                    continue
                if path.is_symlink():
                    raise ValueError('invalid_task_resource_path')
                data = json.loads(path.read_text())
                terminal = {'completed','needs_review'} if kind == 'report' else {'ready','completed'}
                if data.get('status') in terminal or (data.get('revision') or {}).get('immutable'):
                    continue
                data.update(status='interrupted' if kind == 'report' else 'failed',
                            error=reason, updated_at=timestamp())
                atomic_json(path, data)
                if kind == 'report':
                    progress = folder/'progress.json'
                    atomic_json(progress, {'status':'interrupted','progress':task.get('progress',0),
                                           'message':reason,'updated_at':timestamp()})
        task['recovery']['pending'] = False
        self.put(task)

    def reconcile(self, *, raise_on_error=True):
        errors = []
        counts = {'failed':0,'repaired':0,'unknown':0,'repair_failed':0}
        with self.gate(), recovery_context():
            for task in self.records():
                execution = task.get('execution')
                if task['status'] in ACTIVE:
                    if not execution:
                        if not task.get('recovery'):
                            task['recovery'] = {'reason':'ownership_unknown', 'pending':False}
                            task['message'] = 'Ownership unknown; verify legacy execution before manual recovery.'
                            self.put(task)
                        counts['unknown'] += 1
                        continue
                    if execution['lease_until'] <= self.clock():
                        task.update(status='failed', error='ownership_lease_expired',
                                    message='Execution ownership expired; manual retry required.',
                                    updated_at=timestamp(), recovery={'reason':'ownership_lease_expired','pending':True})
                        self.put(task)
                        counts['failed'] += 1
                if (task.get('recovery') or {}).get('pending'):
                    try:
                        self._repair_related(task)
                        counts['repaired'] += 1
                    except Exception as exc:
                        errors.append(exc)
                        counts['repair_failed'] += 1
        if errors and raise_on_error:
            raise errors[0]
        return counts

    def tick(self):
        with self._workers_lock:
            workers = list(self.workers.values())
        for attempt, thread, children in workers:
            try:
                if thread.is_alive():
                    # A parent cannot renew on behalf of an exited required child.
                    if all(child.poll() is None for child in list(children)):
                        self.heartbeat(attempt)
                else:
                    self.update(attempt, {'status':'failed', 'error':'execution_worker_exited'})
            except OwnershipLost:
                with self._workers_lock:
                    self.workers.pop(attempt.task_id, None)
        self.reconcile()

    def start_monitor(self):
        if self._monitor and self._monitor.is_alive():
            return
        def monitor():
            while not self._stop.wait(RECOVERY_INTERVAL_SECONDS):
                try:
                    self.tick()
                except Exception:
                    # A failed storage operation must not renew an attempt or kill recovery.
                    import logging
                    logging.getLogger(__name__).exception('Task recovery pass failed')
        self._monitor = threading.Thread(target=monitor, daemon=True, name='task-recovery')
        self._monitor.start()

    def start(self, attempt, target, args=(), *, name=None):
        def run():
            with attempt.bind():
                try:
                    target(*args)
                except BaseException:
                    try:
                        self.update(attempt, {'status':'failed', 'error':'execution_worker_exited'})
                    except OwnershipLost:
                        pass
                finally:
                    try:
                        self.update(attempt, {'status':'failed', 'error':'execution_ended_without_result'})
                    except OwnershipLost:
                        pass
                    self.reconcile(raise_on_error=False)
        thread = threading.Thread(target=run, daemon=True, name=name)
        with self.gate():
            self.validate(attempt)
            with self._workers_lock:
                self.workers[attempt.task_id] = (attempt, thread, [])
            thread.start()
        self.start_monitor()
        return thread

    @contextmanager
    def watch_child(self, attempt, child):
        with self._workers_lock:
            children = self.workers[attempt.task_id][2]
            children.append(child)
        try:
            yield
        finally:
            with self._workers_lock:
                children.remove(child)

    def close(self):
        self._stop.set()
        if self._monitor and self._monitor is not threading.current_thread():
            self._monitor.join(timeout=1)
