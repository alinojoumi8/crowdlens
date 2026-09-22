"""Private proposal artifacts and process-shared, crash-released ownership."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import uuid

from .claim_ledger import canonical_digest

_REGISTRY = {}
_REGISTRY_GUARD = threading.Lock()
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
ACTIVE = {'queued', 'running'}
TRANSITIONS = {
    'queued': {'running', 'failed', 'rejected'},
    'running': {'ready', 'blocked', 'failed', 'rejected'},
    'ready': {'accepting', 'stale', 'rejected', 'failed'},
    'blocked': {'rejected'},
    'accepting': {'accepted', 'stale', 'failed'},
    'accepted': set(), 'rejected': set(), 'failed': set(), 'stale': {'rejected'},
}
CONTENT_FIELDS = ('scope', 'before', 'after', 'source_digest', 'parent_digest', 'section_index',
                  'ledger', 'sources', 'paragraphs', 'summary_edits', 'findings', 'policy', 'model',
                  'limitations', 'parent_report_id', 'revision_report_id')


class ProposalError(ValueError):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


def now():
    return datetime.now(timezone.utc).isoformat()


def proposal_digest(record):
    return canonical_digest({key: record.get(key) for key in CONTENT_FIELDS})


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path, payload):
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        fsync_directory(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class OperationLease:
    def __init__(self, descriptor, local_lock):
        self.descriptor, self.local_lock = descriptor, local_lock
        self.guard = threading.Lock()

    def close(self):
        with self.guard:
            if self.descriptor is not None:
                fcntl.flock(self.descriptor, fcntl.LOCK_UN)
                os.close(self.descriptor)
                self.descriptor = None
                self.local_lock.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class LeaseBundle:
    def __init__(self, *leases):
        self.leases = leases

    def close(self):
        for lease in reversed(self.leases):
            lease.close()


class ProposalStore:
    def __init__(self, root):
        self.root = Path(root).absolute()
        if self.root.is_symlink():
            raise ProposalError('unsafe_path', 400)
        self.root.mkdir(parents=True, exist_ok=True)
        for directory in ('.evidence-locks', '.evidence-proposals', '.evidence-staging', '.evidence-tombstones'):
            self.path(directory).mkdir(exist_ok=True)

    def path(self, *parts):
        result = self.root.joinpath(*parts)
        try:
            relative = result.relative_to(self.root)
        except ValueError:
            raise ProposalError('unsafe_path', 400)
        if '..' in relative.parts or any((self.root.joinpath(*relative.parts[:i])).is_symlink()
                                       for i in range(len(relative.parts) + 1)):
            raise ProposalError('unsafe_path', 400)
        return result

    @staticmethod
    def identifier(value):
        if not isinstance(value, str) or not ID.fullmatch(value):
            raise ProposalError('invalid_id', 400)
        return value

    def lock(self, name, code='report_busy', status=409):
        self.identifier(name)
        path = self.path('.evidence-locks', name + '.lock')
        key = (os.getpid(), str(path))
        with _REGISTRY_GUARD:
            local_lock = _REGISTRY.setdefault(key, threading.Lock())
        if not local_lock.acquire(blocking=False):
            raise ProposalError(code, status)
        fd = None
        try:
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return OperationLease(fd, local_lock)
        except (OSError, BlockingIOError):
            if fd is not None:
                os.close(fd)
            local_lock.release()
            raise ProposalError(code, status)

    def operation(self, report_id):
        return self.lock('operation-' + self.identifier(report_id))

    def _file(self, proposal_id, name='record'):
        self.identifier(proposal_id)
        if name not in {'record', 'parent', 'sources'}:
            raise ProposalError('invalid_snapshot', 400)
        return self.path('.evidence-proposals', proposal_id, name + '.json')

    def read(self, proposal_id):
        try:
            return json.loads(self._file(proposal_id).read_text(encoding='utf-8'))
        except FileNotFoundError:
            raise ProposalError('not_found', 404)

    def get(self, parent_report_id, proposal_id):
        self.identifier(parent_report_id)
        record = self.read(proposal_id)
        if record['parent_report_id'] != parent_report_id:
            raise ProposalError('not_found', 404)
        return record

    def records(self):
        for path in sorted(self.path('.evidence-proposals').iterdir()):
            if path.is_dir() and ID.fullmatch(path.name):
                try:
                    yield self.read(path.name)
                except ProposalError as exc:
                    if exc.status != 404:
                        raise

    def admit(self, parent_report_id, request_key, request_digest):
        self.identifier(parent_report_id)
        if not isinstance(request_key, str) or not 1 <= len(request_key) <= 200:
            raise ProposalError('invalid_request_key', 400)
        key_hash = canonical_digest(request_key)
        with self.lock('admission', 'admission_busy', 503):
            for record in self.records():
                if record['parent_report_id'] == parent_report_id and record['request_key_hash'] == key_hash:
                    if record['request_digest'] != request_digest:
                        raise ProposalError('idempotency_conflict')
                    return record, None
            operation = self.operation(parent_report_id)
            slot = None
            try:
                for index in range(2):
                    try:
                        slot = self.lock(f'worker-{index}', 'capacity', 503)
                        break
                    except ProposalError:
                        continue
                if slot is None:
                    raise ProposalError('capacity', 503)
                identifier = 'proposal_' + uuid.uuid4().hex
                record = dict(schema_version=1, proposal_id=identifier, parent_report_id=parent_report_id,
                              revision_report_id='report_' + uuid.uuid4().hex,
                              request_key_hash=key_hash, request_digest=request_digest, state='queued',
                              phase='queued', created_at=now(), updated_at=now(), deadline_at=time.time() + 180,
                              before={}, after={}, ledger=[], sources=[], findings=[], usage={}, timing={},
                              limitations=[], accepted_report_id=None, proposal_digest=None)
                self._file(identifier).parent.mkdir(mode=0o700)
                atomic_json(self._file(identifier), record)
                return record, LeaseBundle(operation, slot)
            except BaseException:
                if slot:
                    slot.close()
                operation.close()
                raise

    def update(self, proposal_id, expected_states, changes):
        with self.lock('record-' + self.identifier(proposal_id), 'state_busy'):
            record = self.read(proposal_id)
            old, new = record['state'], changes.get('state', record['state'])
            if old not in expected_states or (new != old and new not in TRANSITIONS[old]):
                raise ProposalError('state_conflict')
            if old not in ACTIVE and any(key in CONTENT_FIELDS for key in changes):
                raise ProposalError('immutable_proposal')
            if new in {'running', 'ready'} and time.time() >= record['deadline_at']:
                raise ProposalError('deadline_exceeded')
            record.update(changes)
            record['updated_at'] = now()
            if new in {'ready', 'blocked'} and old == 'running':
                record['proposal_digest'] = proposal_digest(record)
            atomic_json(self._file(proposal_id), record)
            return record

    def save_snapshot(self, proposal_id, name, value):
        path = self._file(proposal_id, name)
        atomic_json(path, value)
        return canonical_digest(value)

    def load_snapshot(self, proposal_id, name, expected_digest):
        try:
            value = json.loads(self._file(proposal_id, name).read_text(encoding='utf-8'))
        except FileNotFoundError:
            raise ProposalError('snapshot_missing')
        if canonical_digest(value) != expected_digest:
            raise ProposalError('snapshot_mismatch')
        return value

    def finish(self, proposal_id, changes):
        return self.update(proposal_id, {'running'}, changes)

    def reject(self, parent_report_id, proposal_id):
        record = self.get(parent_report_id, proposal_id)
        if record['state'] == 'rejected':
            return record
        return self.update(proposal_id, {'queued', 'running', 'ready', 'blocked', 'stale'}, {'state': 'rejected'})

    def reconcile(self):
        interrupted = 0
        for record in self.records():
            if record['state'] not in ACTIVE:
                continue
            try:
                with self.operation(record['parent_report_id']):
                    self.update(record['proposal_id'], ACTIVE, {'state': 'failed', 'phase': 'interrupted',
                                'error_code': 'worker_interrupted'})
                    interrupted += 1
            except ProposalError as exc:
                if exc.code not in {'report_busy', 'state_conflict', 'state_busy'}:
                    raise
        return {'interrupted': interrupted}
