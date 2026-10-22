"""Logical I/O metering installed only inside one managed simulation subprocess.

The server interpreter is never patched. SQLite's physical pages/index overhead
and native-library diagnostics are host capacity concerns, not logical bytes.
"""
import builtins
import io
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import unquote, urlparse

from . import quota_io, administrator_quotas as quotas

_CONNECT = sqlite3.connect
_INSTALLED = False
_EXEMPT_DATABASES = set()


def _size(value):
    if isinstance(value, memoryview):
        return value.nbytes
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    if isinstance(value, str):
        return len(value.encode('utf-8'))
    if isinstance(value, dict):
        return sum(_size(k) + _size(v) for k, v in value.items())
    if isinstance(value, (tuple, list)):
        return sum(_size(item) for item in value)
    try:
        return memoryview(value).nbytes
    except TypeError:
        pass
    return len(str(value).encode('utf-8'))


def _charge_query(sql, parameters=()):
    # These SQLite features can copy data/write outside ordinary parameterized
    # mutations; OASIS does not need them. Do not silently permit an unmetered path.
    if re.search(r'\b(VACUUM|ATTACH|load_extension)\b', sql, re.I):
        quotas.halt('sqlite_operation_unsupported')
    if re.search(r'\b(INSERT|UPDATE|REPLACE|CREATE|ALTER)\b', sql, re.I):
        quota_io.charge(_size(sql) + _size(parameters))


class _Cursor(sqlite3.Cursor):
    def execute(self, sql, parameters=()):
        _charge_query(sql, parameters)
        return super().execute(sql, parameters)

    def executemany(self, sql, parameters):
        def metered():
            for row in parameters:
                _charge_query(sql, row)
                yield row
        return super().executemany(sql, metered())

    def executescript(self, sql):
        _charge_query(sql)
        return super().executescript(sql)


class _Connection(sqlite3.Connection):
    def cursor(self, factory=None):
        if factory not in (None, sqlite3.Cursor, _Cursor):
            quotas.halt('sqlite_cursor_unsupported')
        return super().cursor(_Cursor)

    def execute(self, sql, parameters=()):
        return self.cursor().execute(sql, parameters)

    def executemany(self, sql, parameters):
        return self.cursor().executemany(sql, parameters)

    def executescript(self, sql):
        return self.cursor().executescript(sql)

    def backup(self, *args, **kwargs):
        quotas.halt('sqlite_operation_unsupported')

    def blobopen(self, *args, **kwargs):
        quotas.halt('sqlite_operation_unsupported')


def _database_path(database):
    value = os.fsdecode(database)
    if value.startswith('file:'):
        value = unquote(urlparse(value).path)
    return str(Path(value).resolve())


def _connect(database, *args, **kwargs):
    if _database_path(database) in _EXEMPT_DATABASES:
        return _CONNECT(database, *args, **kwargs)
    # A custom C connection/cursor could bypass execute accounting.
    if kwargs.get('factory') not in (None, sqlite3.Connection, _Connection):
        quotas.halt('sqlite_connection_unsupported')
    if len(args) >= 5:
        if args[4] not in (sqlite3.Connection, _Connection):
            quotas.halt('sqlite_connection_unsupported')
        args = (*args[:4], _Connection, *args[5:])
    else:
        kwargs['factory'] = _Connection
    return _CONNECT(database, *args, **kwargs)


class _DescriptorWriter:
    def __init__(self, stream):
        self.stream = stream

    def __getattr__(self, name):
        return getattr(self.stream, name)

    @property
    def buffer(self):
        return _DescriptorWriter(self.stream.buffer)

    def write(self, value):
        quota_io.charge(_size(value))
        return self.stream.write(value)

    def writelines(self, values):
        for value in values:
            self.write(value)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)


def _fdopen(fd, mode='r', *args, **kwargs):
    stream = quota_io._ORIGINAL_OPEN(fd, mode, *args, **kwargs)
    return _DescriptorWriter(stream) if any(c in mode for c in 'wax+') else stream


def install():
    global _INSTALLED
    if _INSTALLED:
        return
    database = os.environ.get('CROWDLENS_QUOTA_DB')
    owner = os.environ.get('CROWDLENS_WORKSPACE_ID')
    auth_database = os.environ.get('CROWDLENS_WORKSPACE_DB')
    if not database or not owner or not auth_database:
        quotas.halt('child_configuration_invalid')
    # Launcher-supplied values are immutable for this one workspace process.
    _EXEMPT_DATABASES.update({_database_path(database), _database_path(auth_database)})
    quota_io.configure_child(database, owner)
    ledger, owner = quota_io.ledger_for_workspace()
    with ledger.transaction() as db:
        quotas.policies(db, owner)
    sqlite3.connect = _connect
    sqlite3.dbapi2.connect = _connect
    builtins.open = quota_io.open
    io.open = quota_io.open
    os.fdopen = _fdopen
    _INSTALLED = True


def capture_stdout(process, path):
    """Bound each chunk before writing the child pipe to a persistent log."""
    from .workflow_execution import WorkflowHalt
    try:
        while True:
            data = process.stdout.read(8192)
            if not data:
                break
            with quota_io.open(path, 'ab') as stream:
                stream.write(data)
    except (WorkflowHalt, OSError) as exc:
        process._crowdlens_quota_error = getattr(exc, 'reason', 'quota_output_capture_failed')
        if process.poll() is None:
            process.terminate()
            import subprocess
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
    finally:
        process.stdout.close()
