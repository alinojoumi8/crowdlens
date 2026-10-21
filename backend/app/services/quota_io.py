"""Bound managed artifact writes before publication; local operator I/O is unchanged."""
import builtins
from contextlib import contextmanager
from contextvars import ContextVar
import io
import json
import re

from . import administrator_quotas as quotas
from .workspace import current_workspace
_REMEDIATION = ContextVar('quota_remediation', default=False)
_ORIGINAL_OPEN = builtins.open
_CHILD_DATABASE = None
_CHILD_OWNER = None


def configure_child(database, owner):
    global _CHILD_DATABASE, _CHILD_OWNER
    _CHILD_DATABASE, _CHILD_OWNER = database, owner


@contextmanager
def remediation():
    """Trusted cancellation repairs only; never grants admission or model calls."""
    token = _REMEDIATION.set(True)
    try:
        yield
    finally:
        _REMEDIATION.reset(token)


def ledger_for_workspace():
    owner = _CHILD_OWNER if _CHILD_DATABASE else current_workspace()
    if not owner or _REMEDIATION.get():
        return None, None
    from .workflow_execution import current_scope, WorkflowLedger
    if _CHILD_DATABASE:
        ledger = WorkflowLedger(_CHILD_DATABASE)
        with ledger.transaction() as db:
            if not quotas.managed(db):
                quotas.halt('child_configuration_invalid')
        return ledger, owner
    scope = current_scope()
    if scope and scope.ledger:
        ledger = scope.ledger
    else:
        from ..models.task import TaskManager
        repository = TaskManager._repository
        if repository is None:
            # Standalone ownership utilities are also used outside an app.
            # OIDC app installation separately requires a durable control DB.
            return None, None
        ledger = WorkflowLedger(repository.path)
    with ledger.transaction() as db:
        return (ledger, owner) if quotas.managed(db) else (None, None)


def remaining():
    ledger, owner = ledger_for_workspace()
    if ledger is None:
        return None
    with ledger.transaction() as db:
        configured = quotas.policies(db, owner, admission=False)
        return min(p['limits']['storage_write_bytes'] - quotas.usage(db, scope, ledger.clock())['storage_write_bytes']
                   for scope, p in configured)


def charge(size):
    ledger, owner = ledger_for_workspace()
    if ledger:
        with ledger.transaction() as db:
            quotas.charge_storage(db, owner, ledger.clock(), size)


def charge_operation():
    ledger, owner = ledger_for_workspace()
    if ledger:
        with ledger.transaction() as db:
            quotas.begin_operation(db, owner, ledger.clock(), active=False)


class _Writer:
    def __init__(self, path, mode, args, kwargs, available):
        self.name, self.mode, self.args, self.kwargs = path, mode, args, kwargs
        self.encoding = kwargs.get('encoding') or (args[1] if len(args) > 1 else None) or 'utf-8'
        self.errors = kwargs.get('errors') or (args[2] if len(args) > 2 else None) or 'strict'
        self.newline = kwargs.get('newline', args[3] if len(args) > 3 else None)
        self.buffer = io.BytesIO() if 'b' in mode else io.StringIO()
        self.available = available
        self.closed = False

    def write(self, value):
        # Check before buffering, and recheck atomically before publication.
        encoded = self._encode(value)
        if len(encoded) + self.size() > self.available:
            quotas.halt('storage_write_bytes_limit')
        return self.buffer.write(value)

    def size(self):
        return len(self._encode(self.buffer.getvalue()))

    def _encode(self, value):
        if isinstance(value, (bytes, bytearray, memoryview)):
            return bytes(value)
        if self.newline not in (None, '', '\n'):
            value = value.replace('\n', self.newline)
        return value.encode(self.encoding, errors=self.errors)

    def writelines(self, values):
        for value in values:
            self.write(value)

    def flush(self):
        if self.closed:
            raise ValueError('I/O operation on closed file')
        value = self.buffer.getvalue()
        charge(self.size())
        with _ORIGINAL_OPEN(self.name, self.mode, *self.args, **self.kwargs) as stream:
            stream.write(value)
        self.buffer = io.BytesIO() if 'b' in self.mode else io.StringIO()
        # Subsequent explicit flushes append; a failed quota check never truncates
        # the existing file. Normal artifact writers publish once on context exit.
        self.mode = 'ab' if 'b' in self.mode else 'a'
        self.available = remaining()

    def fileno(self):
        # A raw descriptor would let a subprocess bypass write accounting.
        quotas.halt('unmetered_file_descriptor_unsupported')

    def close(self):
        if not self.closed:
            self.flush()
            self.closed = True
            self.buffer.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None:
            self.close()
        else:
            self.closed = True
            self.buffer.close()


def open(path, mode='r', *args, **kwargs):
    if not any(letter in mode for letter in 'wax+'):
        return _ORIGINAL_OPEN(path, mode, *args, **kwargs)
    available = remaining()
    if available is None:
        return _ORIGINAL_OPEN(path, mode, *args, **kwargs)
    if '+' in mode or not isinstance(path, (str, bytes)) and not hasattr(path, '__fspath__'):
        quotas.halt('unmetered_file_descriptor_unsupported')
    return _Writer(path, mode, args, kwargs, available)


class GraphTransaction:
    def __init__(self, transaction):
        self.transaction = transaction

    def __getattr__(self, name):
        return getattr(self.transaction, name)

    def run(self, query, parameters=None, **kwargs):
        if re.search(r'\b(CREATE|MERGE|SET)\b', str(query), re.I):
            # Logical Cypher write bytes, including retries; database/index
            # overhead remains a separate host capacity requirement.
            charge(len(str(query).encode()) + len(json.dumps([parameters, kwargs], default=str).encode()))
        return self.transaction.run(query, **({'parameters': parameters} if parameters is not None else {}), **kwargs)


class GraphSession(GraphTransaction):
    def __enter__(self):
        self.transaction.__enter__()
        return self

    def __exit__(self, *args):
        return self.transaction.__exit__(*args)

    def execute_write(self, function, *args, **kwargs):
        return self.transaction.execute_write(lambda tx, *a, **k: function(GraphTransaction(tx), *a, **k), *args, **kwargs)


class GraphDriver:
    def __init__(self, driver):
        self.driver = driver

    def __getattr__(self, name):
        return getattr(self.driver, name)

    def session(self, *args, **kwargs):
        return GraphSession(self.driver.session(*args, **kwargs))
