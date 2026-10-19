"""Server-resolved workspace ownership. Missing context and legacy records fail closed.

Local operator mode is intentionally unchanged. Maintenance privileges are internal
only; neither administrator roles nor request parameters can select a workspace.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import inspect
import logging
import os
from pathlib import Path
import re
import sqlite3
import time

_SCOPE = ContextVar('workspace', default=None)
_SYSTEM = object()
_store = None
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,199}\Z')


class WorkspaceDenied(BaseException):
    """Authorization is control flow, never a model/retrieval fallback."""
    def __init__(self):
        super().__init__('Resource not found')


class WorkspaceStore:
    def __init__(self, path):
        self.path = str(Path(path).resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # Create identity/ownership databases with private permissions from the outset.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS workspace_resources ('
                       'kind TEXT NOT NULL, resource_id TEXT NOT NULL, workspace_id TEXT NOT NULL, '
                       'PRIMARY KEY(kind, resource_id))')
            db.execute('CREATE INDEX IF NOT EXISTS workspace_owner ON workspace_resources(workspace_id)')
            db.execute('CREATE TABLE IF NOT EXISTS workspace_audit ('
                       'at REAL NOT NULL, workspace_id TEXT, action TEXT NOT NULL, kind TEXT, resource_id TEXT)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def owner(self, kind, identifier):
        with self.connect() as db:
            row = db.execute('SELECT workspace_id FROM workspace_resources WHERE kind=? AND resource_id=?',
                             (kind, identifier)).fetchone()
        return row[0] if row else None

    def owned_ids(self, workspace_id, kind):
        with self.connect() as db:
            return {row[0] for row in db.execute(
                "SELECT resource_id FROM workspace_resources WHERE workspace_id=? AND kind=?",
                (workspace_id, kind))}

    def audit(self, workspace_id, action, kind='', identifier=''):
        try:
            with self.connect() as db:
                db.execute('INSERT INTO workspace_audit VALUES(?,?,?,?,?)',
                           (time.time(), workspace_id, action, kind, identifier))
        except sqlite3.Error as exc:
            # Access telemetry cannot change a committed response or suppress a
            # denial. Creation audit below stays atomic with owner registration.
            logging.getLogger('mirofish.workspace').error(
                'Workspace audit unavailable: workspace=%r action=%r resource=%r:%r error=%s',
                workspace_id, action, kind, identifier, type(exc).__name__)

    def register(self, workspace_id, kind, identifier):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT workspace_id FROM workspace_resources WHERE kind=? AND resource_id=?',
                             (kind, identifier)).fetchone()
            if row:
                # Creation cannot adopt an existing or deleted resource, even by its owner.
                raise WorkspaceDenied()
            db.execute('INSERT INTO workspace_resources VALUES(?,?,?)', (kind, identifier, workspace_id))
            db.execute('INSERT INTO workspace_audit VALUES(?,?,?,?,?)',
                       (time.time(), workspace_id, 'create', kind, identifier))


def configure(path=None):
    global _store
    _store = WorkspaceStore(path) if path else None


def current_workspace():
    if _store is None:
        return None
    value = _SCOPE.get()
    if value is _SYSTEM:
        return None
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise WorkspaceDenied()
    return value


@contextmanager
def workspace_scope(workspace_id):
    if not isinstance(workspace_id, str) or not _ID.fullmatch(workspace_id):
        raise WorkspaceDenied()
    token = _SCOPE.set(workspace_id)
    try:
        yield
    finally:
        _SCOPE.reset(token)


@contextmanager
def maintenance_scope():
    token = _SCOPE.set(_SYSTEM)
    try:
        yield
    finally:
        _SCOPE.reset(token)


def maintenance(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with maintenance_scope():
            return function(*args, **kwargs)
    return wrapped


def visible(kind, identifier):
    workspace_id = current_workspace()
    if workspace_id is None:
        return True
    try:
        return isinstance(identifier, str) and bool(_ID.fullmatch(identifier)) and _store.owner(kind, identifier) == workspace_id
    except sqlite3.Error:
        raise WorkspaceDenied() from None


def visible_ids(kind):
    """Load one owner set for a listing; None denotes trusted local/maintenance."""
    workspace_id = current_workspace()
    try:
        return None if workspace_id is None else _store.owned_ids(workspace_id, kind)
    except sqlite3.Error:
        raise WorkspaceDenied() from None


def require(kind, identifier):
    if not visible(kind, identifier):
        _store.audit(current_workspace(), 'denied', kind, str(identifier)[:200])
        raise WorkspaceDenied()


def register(kind, identifier, parents=()):
    workspace_id = current_workspace()
    if workspace_id is None:
        return
    if not isinstance(identifier, str) or not _ID.fullmatch(identifier):
        raise WorkspaceDenied()
    for parent_kind, parent_id in parents:
        if parent_id:
            require(parent_kind, parent_id)
    _store.register(workspace_id, kind, identifier)


def require_resource(resource):
    if current_workspace() is None:
        return
    if not isinstance(resource, str) or ':' not in resource:
        raise WorkspaceDenied()
    kind, identifier = resource.split(':', 1)
    require('simulation' if kind in {'simulation-runtime', 'report-generation', 'ensemble'} else kind, identifier)


def owned(kind, argument):
    """Explicit decorator for service entry points, including worker calls."""
    def decorate(function):
        signature = inspect.signature(function)
        @wraps(function)
        def wrapped(*args, **kwargs):
            values = signature.bind(*args, **kwargs).arguments
            identifier = values.get(argument)
            if identifier is not None:
                require(kind, identifier)
            return function(*args, **kwargs)
        return wrapped
    return decorate


def cache_namespace():
    return current_workspace() or ''


def child_environment():
    workspace_id = current_workspace()
    return ({'CROWDLENS_WORKSPACE_ID': workspace_id, 'CROWDLENS_WORKSPACE_DB': _store.path}
            if workspace_id else {})


# These values are supplied only by the trusted subprocess launcher, never HTTP.
if os.environ.get('CROWDLENS_WORKSPACE_DB'):
    configure(os.environ['CROWDLENS_WORKSPACE_DB'])
    _SCOPE.set(os.environ.get('CROWDLENS_WORKSPACE_ID'))


def check_request_references(request):
    """Reject cross-workspace IDs before endpoint lookup, side effects or streaming."""
    if current_workspace() is None:
        return
    kinds = {'project_id': 'project', 'case_id': 'case', 'graph_id': 'graph',
             'simulation_id': 'simulation', 'report_id': 'report', 'parent_report_id': 'report',
             'task_id': 'task', 'workflow_id': 'workflow', 'wid': 'workflow',
             'proposal_id': 'proposal', 'case_version_id': 'version', 'version_id': 'version',
             'from_version_id': 'version', 'to_version_id': 'version'}
    def check(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {'workspace_id', 'owner_id'}:
                    raise WorkspaceDenied()
                if key in kinds and item:
                    require(kinds[key], item)
                elif key == 'resource' and item:
                    require_resource(item)
                elif key == 'resources' and isinstance(item, list):
                    for resource in item:
                        require_resource(resource.get('key') if isinstance(resource, dict) else resource)
                elif isinstance(item, (dict, list)):
                    check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
    if request.headers.get('X-Workspace-ID'):
        raise WorkspaceDenied()
    check(request.view_args or {})
    # Check all repeated values, not merely the first value selected by MultiDict.
    for source in (request.args, request.form):
        for key, items in source.lists():
            for item in items:
                check({key: item})
    check(request.get_json(silent=True) if request.is_json else {})
    wid = request.headers.get('X-Workflow-ID')
    if wid:
        require('workflow', wid)
