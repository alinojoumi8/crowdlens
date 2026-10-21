"""Two-user authorization regressions, with no provider calls."""
import pytest


@pytest.fixture
def ownership(tmp_path, monkeypatch):
    from app.services import workspace
    store = workspace.WorkspaceStore(tmp_path / 'owners.db')
    monkeypatch.setattr(workspace, '_store', store)
    return workspace, store


def test_ownership_is_immutable_and_unowned_records_are_closed(ownership):
    w, store = ownership
    with w.workspace_scope('alice'):
        w.register('project', 'p1')
        w.require('project', 'p1')
        with pytest.raises(w.WorkspaceDenied): w.require('project', 'legacy')
    with w.workspace_scope('bob'):
        assert not w.visible('project', 'p1')
        with pytest.raises(w.WorkspaceDenied): w.require('project', 'p1')
        with pytest.raises(w.WorkspaceDenied): w.register('project', 'p1')
    with pytest.raises(w.WorkspaceDenied): w.require('project', 'p1')


def test_child_bindings_cannot_reference_foreign_parents(ownership):
    w, store = ownership
    with w.workspace_scope('alice'):
        w.register('project', 'pa')
    with w.workspace_scope('bob'):
        w.register('project', 'pb')
        with pytest.raises(w.WorkspaceDenied):
            w.register('simulation', 's', parents=[('project', 'pa')])
        w.register('simulation', 's', parents=[('project', 'pb')])
        assert store.owner('simulation', 's') == 'bob'


@pytest.fixture
def stores(tmp_path, monkeypatch):
    from app.models.project import ProjectManager
    from app.models.case import CaseManager
    from app.models.task import TaskManager
    from app.services.simulation_manager import SimulationManager
    from app.services.simulation_runner import SimulationRunner
    from app.services.report_agent import ReportManager
    from app.storage.control_db import ControlDatabase
    from app.services.task_execution import TaskRuntime
    db = ControlDatabase(tmp_path / 'control.db')
    for manager, attr, directory in [(ProjectManager, 'PROJECTS_DIR', 'projects'),
            (CaseManager, 'CASES_DIR', 'cases'), (SimulationManager, 'SIMULATION_DATA_DIR', 'simulations'),
            (SimulationRunner, 'RUN_STATE_DIR', 'simulations'), (ReportManager, 'REPORTS_DIR', 'reports')]:
        monkeypatch.setattr(manager, attr, str(tmp_path / directory))
    for manager in (ProjectManager, CaseManager, TaskManager):
        monkeypatch.setattr(manager, '_repository', db)
    runtime = TaskRuntime(db)
    monkeypatch.setattr(TaskManager, '_runtime', runtime)
    monkeypatch.setattr(TaskManager, '_instance', None)
    yield db
    runtime.close()


def bundle(w, owner):
    from app.models.project import ProjectManager
    from app.models.case import CaseManager
    from app.models.task import TaskManager
    from app.services.simulation_manager import SimulationManager
    from app.services.report_agent import ReportManager, Report, ReportStatus
    with w.workspace_scope(owner):
        p = ProjectManager.create_project(owner + ' project')
        ProjectManager.save_extracted_text(p.project_id, owner + ' private document')
        c = CaseManager.create_case(owner + ' case')
        v = CaseManager.create_version(c.case_id, p.project_id, documents=[])
        g = 'graph_' + owner
        w.register('graph', g)
        s = SimulationManager().create_simulation(p.project_id, g)
        r = 'report_' + owner
        w.register('report', r, parents=[('simulation', s.simulation_id), ('graph', g)])
        ReportManager.save_report(Report(r, s.simulation_id, g, 'fictional', ReportStatus.COMPLETED,
                                        markdown_content=owner + ' private report'))
        t = TaskManager().create_task('fixture', resources=[{'key': 'project:' + p.project_id}])
    return dict(project=p.project_id, case=c.case_id, version=v.version_id,
                graph=g, simulation=s.simulation_id, report=r, task=t)


def test_managers_files_and_sqlite_are_isolated(ownership, stores):
    from app.models.project import ProjectManager
    from app.models.case import CaseManager
    from app.models.task import TaskManager
    from app.services.simulation_manager import SimulationManager
    from app.services.report_agent import ReportManager
    w, _ = ownership
    a, b = bundle(w, 'alice'), bundle(w, 'bob')
    with w.workspace_scope('bob'):
        assert [p.project_id for p in ProjectManager.list_projects(1)] == [b['project']]
        assert [c.case_id for c in CaseManager.list_cases()] == [b['case']]
        assert [s.simulation_id for s in SimulationManager().list_simulations()] == [b['simulation']]
        assert [r.report_id for r in ReportManager.list_reports()] == [b['report']]
        assert [t['task_id'] for t in TaskManager().list_tasks()] == [b['task']]
        assert ProjectManager.get_extracted_text(b['project']) == 'bob private document'
        for call in [lambda: ProjectManager.get_project(a['project']),
                     lambda: ProjectManager.get_extracted_text(a['project']),
                     lambda: ProjectManager.save_extracted_text(a['project'], 'overwrite'),
                     lambda: ProjectManager.delete_project(a['project']),
                     lambda: CaseManager.get_case(a['case']),
                     lambda: CaseManager.get_version(b['case'], a['version']),
                     lambda: SimulationManager().get_simulation(a['simulation']),
                     lambda: ReportManager.get_report(a['report']),
                     lambda: ReportManager.delete_report(a['report']),
                     lambda: stores.get_project(a['project']),
                     lambda: stores.put_project({'project_id':a['project'], 'name':'overwrite'}),
                     lambda: stores.delete_task(a['task'])]:
            with pytest.raises(w.WorkspaceDenied): call()
    with w.workspace_scope('alice'):
        assert ProjectManager.get_extracted_text(a['project']) == 'alice private document'
        assert ReportManager.get_report(a['report']).markdown_content == 'alice private report'


def test_real_api_ids_lists_downloads_and_override_rejection(stores, tmp_path):
    from flask import Flask
    from app.authentication import install_authentication
    from app.api import graph_bp, simulation_bp, report_bp
    from app.api.execution import install_workflow_controls
    from app.services import workspace as w
    from test_authentication import login
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='x'*40, AUTH_MODE='oidc', AUTH_ALLOW_HTTP_LOOPBACK=True,
        AUTH_BASE_URL='http://localhost', AUTH_ISSUER='http://localhost:9999', AUTH_CLIENT_ID='test',
        AUTH_CLIENT_SECRET='secret', AUTH_ADMIN_EMAIL='admin@example.test', AUTH_DB_PATH=str(tmp_path/'auth.db'))
    app.extensions['control_db'] = stores
    install_authentication(app)
    for bp, prefix in [(graph_bp, '/api/graph'), (simulation_bp, '/api/simulation'), (report_bp, '/api/report')]:
        app.register_blueprint(bp, url_prefix=prefix)
    install_workflow_controls(app)
    ca, cb = app.test_client(), app.test_client()
    ua, csrf_a = login(app, ca)
    auth = app.extensions['auth_store']
    invite = auth.invite('bob@example.test', ua['id'])
    ub, csrf_b = login(app, cb, 'bob@example.test', 'bob', invite)
    # Test-only promotion makes both principals capable of API operations. A test
    # relying on the tester blanket 403 would not exercise workspace isolation.
    with auth.db() as db:
        db.execute("UPDATE auth_users SET role='admin' WHERE id=?", (ub['id'],))
    from test_administrator_quotas import configure
    configure(app, ca, ua, {'X-CrowdLens-CSRF': csrf_a})
    configure(app, ca, ub, {'X-CrowdLens-CSRF': csrf_a})
    a, b = bundle(w, ua['id']), bundle(w, ub['id'])
    assert cb.get('/api/graph/project/' + b['project']).status_code == 200
    assert ca.get('/api/report/' + a['report'] + '/download').status_code == 200
    assert [p['project_id'] for p in cb.get('/api/graph/project/list').json['data']] == [b['project']]
    paths = ['/api/graph/project/' + a['project'], '/api/graph/case/' + a['case'],
             '/api/graph/task/' + a['task'], '/api/graph/data/' + a['graph'],
             '/api/report/' + a['report'] + '/download', '/api/report/' + a['report'],
             '/api/simulation/' + a['simulation']]
    for path in paths:
        response = cb.get(path)
        assert response.status_code == 404, (path, response.json)
        assert response.json == {'success':False, 'error':'resource_not_found'}
    for method, path, body in [('delete', '/api/graph/project/' + a['project'], {}),
            ('post', '/api/simulation/create', {'project_id': b['project'], 'graph_id': a['graph']}),
            ('post', '/api/graph/case/create', {'name':'bad','workspace_id':ua['id']})]:
        assert getattr(cb, method)(path, json=body, headers={'X-CrowdLens-CSRF':csrf_b}).status_code == 404
    assert cb.get('/api/graph/project/list', headers={'X-Workspace-ID':ua['id']}).status_code == 404
    assert cb.get('/api/graph/project/list?project_id='+b['project']+'&project_id='+a['project']).status_code == 404
    assert ca.get('/api/graph/project/' + a['project']).status_code == 200
    with w._store.connect() as db:
        assert db.execute("SELECT count(*) FROM workspace_audit WHERE workspace_id=? AND action='denied'", (ub['id'],)).fetchone()[0] >= len(paths)


def authorize(ledger, resource):
    return ledger.authorize(request_key='same-key', provider='fixture', model='offline', base_url='http://localhost',
        input_description='fictional fixture', max_requests=2, max_seconds=60, confirmed=True, resources=[resource])['workflow_id']


def test_workflows_are_owned_including_stop_renewal_and_idempotency(ownership, tmp_path):
    from app.services.workflow_execution import WorkflowLedger
    w, _ = ownership
    ledger = WorkflowLedger(tmp_path/'workflows.db')
    ids = {}
    for owner in ('alice', 'bob'):
        with w.workspace_scope(owner):
            w.register('project', owner)
            ids[owner] = authorize(ledger, 'project:' + owner)
    assert ids['alice'] != ids['bob']
    with w.workspace_scope('bob'):
        assert authorize(ledger, 'project:bob') == ids['bob']
        assert ledger.resolve('project:bob') == ids['bob']
        for call in [lambda: ledger.resolve('project:alice'), lambda: ledger.status(ids['alice']),
                lambda: ledger.stop(ids['alice']), lambda: ledger.bind(ids['bob'], 'project:alice'),
                lambda: ledger.reauthorize(ids['alice'], max_requests=3, max_seconds=60, confirmed=True, request_key='renew')]:
            with pytest.raises(w.WorkspaceDenied): call()
        ledger.stop(ids['bob'])
    with w.workspace_scope('alice'):
        assert ledger.status(ids['alice'])['state'] == 'authorized'


def test_background_workers_and_forged_attempts(ownership, stores):
    from app.models.task import TaskManager
    w, _ = ownership
    a, b = bundle(w, 'alice'), bundle(w, 'bob')
    manager = TaskManager()
    results = []
    def worker(owner, own, other):
        results.append(w.current_workspace())
        w.require('project', own)
        with pytest.raises(w.WorkspaceDenied): w.require('project', other)
        manager.runtime.update(manager.attempt(a['task'] if owner == 'alice' else b['task']), {'status':'completed'})
    threads=[]
    for owner, own, other in [('alice',a,b),('bob',b,a)]:
        with w.workspace_scope(owner):
            threads.append(manager.start_task(own['task'], worker, (owner,own['project'],other['project'])))
    for thread in threads: thread.join(timeout=5); assert not thread.is_alive()
    assert sorted(results) == ['alice','bob']
    with w.workspace_scope('bob'):
        with pytest.raises(w.WorkspaceDenied):
            with manager.attempt(a['task']).bind(): pass
        assert manager.runtime.get(b['task'])['status'] == 'completed'
    with w.workspace_scope('alice'):
        assert manager.runtime.get(a['task'])['status'] == 'completed'


def test_proposals_revisions_and_human_review_packets(ownership, stores, tmp_path):
    from app.services.proposal_store import ProposalStore
    from app.services.human_reviews import HumanReviewStore
    w, _ = ownership
    a, b = bundle(w, 'alice'), bundle(w, 'bob')
    proposals = ProposalStore(tmp_path/'reports')
    with w.workspace_scope('alice'):
        record, lease = proposals.admit(a['report'], 'key', 'digest')
        lease.close()
        assert w.visible('report', record['revision_report_id'])
    with w.workspace_scope('bob'):
        assert list(proposals.records()) == []
        for call in [lambda: proposals.read(record['proposal_id']),
                lambda: proposals.get(b['report'], record['proposal_id']),
                lambda: proposals.path(record['revision_report_id']),
                lambda: proposals.reject(a['report'], record['proposal_id']),
                lambda: HumanReviewStore(proposals).view(record)]:
            with pytest.raises(w.WorkspaceDenied): call()


def test_cache_entries_are_not_reused_between_users(ownership, tmp_path):
    from app.storage.extraction_cache import ExtractionCache
    from app.storage.embedding_service import EmbeddingCache
    w, _ = ownership
    extraction, embedding = ExtractionCache(tmp_path/'ner'), EmbeddingCache(tmp_path/'vectors')
    with w.workspace_scope('alice'):
        extraction.set('file','chunk','ontology', {'entities':['private']})
        embedding.set('provider','task','text',[1.0])
        assert extraction.get('file','chunk','ontology')
    with w.workspace_scope('bob'):
        assert extraction.get('file','chunk','ontology') is None
        assert embedding.get('provider','task','text') is None
        embedding.set('provider','task','text',[2.0])
    with w.workspace_scope('alice'):
        assert embedding.get('provider','task','text') == [1.0]


def test_owner_registry_restore_and_unowned_legacy_data(ownership, stores, tmp_path, monkeypatch):
    import sqlite3
    from app.models.project import ProjectManager
    w, store = ownership
    with w.maintenance_scope():
        legacy = ProjectManager.create_project('legacy')
    a = bundle(w, 'alice')
    backup = tmp_path/'restored.db'
    with store.connect() as source, sqlite3.connect(backup) as target:
        source.backup(target)
    monkeypatch.setattr(w, '_store', w.WorkspaceStore(backup))
    with w.workspace_scope('alice'):
        assert ProjectManager.get_project(a['project'])
        with pytest.raises(w.WorkspaceDenied): ProjectManager.get_project(legacy.project_id)
    with w.workspace_scope('bob'):
        assert ProjectManager.list_projects() == []
        with pytest.raises(w.WorkspaceDenied): ProjectManager.get_project(a['project'])


def test_node_uuid_cannot_bypass_graph_ownership(ownership):
    from app.storage.neo4j_storage import Neo4jStorage
    from unittest.mock import MagicMock
    w, _ = ownership
    storage = object.__new__(Neo4jStorage)
    storage._driver = MagicMock()
    session = storage._driver.session.return_value.__enter__.return_value
    tx = MagicMock()
    session.execute_read.side_effect = lambda function: function(tx)
    tx.run.return_value.single.return_value = {'n': {'uuid':'node-secret','graph_id':'ga','name':'Alice secret'}, 'labels':['Entity']}
    with w.workspace_scope('alice'):
        w.register('graph','ga')
        assert storage.get_node('node-secret')['name'] == 'Alice secret'
    with w.workspace_scope('bob'):
        w.register('graph','gb')
        for call in [lambda: storage.get_node('node-secret'), lambda: storage.get_node_edges('node-secret'),
                     lambda: storage.get_graph_data('ga'), lambda: storage.search('ga','query'),
                     lambda: storage.get_source_chunks('ga','case','version'), lambda: storage.delete_graph('ga')]:
            with pytest.raises(w.WorkspaceDenied): call()
    # A foreign ID must be rejected before graph search or any provider call.
    assert tx.run.call_count == 3


def test_subprocess_carries_workspace_and_rejects_foreign_workflow(ownership, tmp_path):
    import os
    import subprocess
    import sys
    from app.services.workflow_execution import WorkflowLedger, ExecutionScope
    w, _ = ownership
    ledger = WorkflowLedger(tmp_path/'workflow.db')
    with w.workspace_scope('alice'):
        w.register('project', 'pa')
        wid = authorize(ledger,'project:pa')
        env = {**os.environ, **ExecutionScope(ledger,wid,1,'simulation').child_env()}
    script = "from app.services.workspace import current_workspace; from app.services.workflow_execution import current_scope; current_scope().checkpoint(); print(current_workspace())"
    good = subprocess.run([sys.executable,'-c',script],env=env,text=True,capture_output=True,timeout=15)
    assert good.returncode == 0, good.stderr
    assert good.stdout.strip() == 'alice'
    bad = subprocess.run([sys.executable,'-c',script],env={**env,'CROWDLENS_WORKSPACE_ID':'bob'},text=True,capture_output=True,timeout=15)
    assert bad.returncode != 0 and 'WorkspaceDenied' in bad.stderr


def test_embedding_memory_and_batch_cache_are_workspace_scoped(ownership, monkeypatch):
    from app.storage.embedding_service import EmbeddingService
    w, _ = ownership
    service = EmbeddingService()
    service._persistent_cache = None
    calls=[]
    def embed(texts, **kwargs):
        calls.append(w.current_workspace())
        return [[float(len(calls))] for text in texts]
    monkeypatch.setattr(service, '_request_embeddings', embed)
    with w.workspace_scope('alice'):
        assert service.embed_batch(['same']) == [[1.0]]
        assert service.embed_batch(['same']) == [[1.0]]
    with w.workspace_scope('bob'):
        assert service.embed_batch(['same']) == [[2.0]]
    assert calls == ['alice','bob']


def test_permission_denial_bypasses_service_fallback_and_returns_generic_404(tmp_path):
    from flask import Flask
    from app.authentication import install_authentication
    from app.services import workspace as w
    from test_authentication import login
    a=Flask('denial-boundary')
    a.config.update(TESTING=True, SECRET_KEY='x'*40, AUTH_MODE='oidc', AUTH_ALLOW_HTTP_LOOPBACK=True,
        AUTH_BASE_URL='http://localhost', AUTH_ISSUER='http://localhost:9999', AUTH_CLIENT_ID='test',
        AUTH_CLIENT_SECRET='secret', AUTH_ADMIN_EMAIL='admin@example.test', AUTH_DB_PATH=str(tmp_path/'auth.db'))
    install_authentication(a)
    fallback=[]
    @a.get('/api/derived-reference')
    def derived_reference():
        try:
            w.require('graph', 'foreign-derived-graph')
        except Exception:
            fallback.append(True)
            return {'traceback':'would leak internal details'},500
        return {'unexpected':True}
    c=a.test_client();login(a,c)
    with w.workspace_scope('other'):
        w.register('graph', 'foreign-derived-graph')
    response=c.get('/api/derived-reference')
    assert response.status_code == 404
    assert response.json == {'success':False,'error':'resource_not_found'}
    assert not fallback
    assert (tmp_path/'auth.db').stat().st_mode & 0o777 == 0o600


def test_listing_loads_owners_once_and_limits_after_filter(ownership, stores, monkeypatch):
    from app.models.project import ProjectManager
    w, store = ownership
    a=bundle(w,'alice');bundle(w,'bob')
    with w.workspace_scope('alice'):
        monkeypatch.setattr(store,'owner',lambda *args: pytest.fail('one connection per row'))
        assert [p.project_id for p in ProjectManager.list_projects(1)] == [a['project']]
        assert ProjectManager.list_projects(0) == []


def test_graph_memory_and_parallel_profiles_keep_workspace(ownership, stores, monkeypatch):
    import threading
    from app.services.graph_memory_updater import GraphMemoryUpdater
    from app.services.oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
    from app.services.entity_reader import EntityNode
    w, _ = ownership
    seen=[]
    for owner in ('alice','bob'):
        with w.workspace_scope(owner):
            w.register('graph', owner)
            updater=GraphMemoryUpdater(owner, None)
            def work(owner=owner):
                w.require('graph',owner)
                seen.append(('memory',w.current_workspace()))
            monkeypatch.setattr(updater,'_worker_loop',work)
            updater.start()
            updater._worker_thread.join(timeout=5)
            assert not updater._worker_thread.is_alive()
            generator=object.__new__(OasisProfileGenerator)
            barrier=threading.Barrier(2)
            def profile(entity,user_id,use_llm,owner=owner):
                w.require('graph',owner)
                seen.append(('profile',w.current_workspace()))
                barrier.wait(timeout=5)
                return OasisAgentProfile(user_id,entity.name,entity.name,'fixture','fixture')
            monkeypatch.setattr(generator,'generate_profile_from_entity',profile)
            monkeypatch.setattr(generator,'_print_generated_profile',lambda *args: None)
            entities=[EntityNode(str(i),'fixture'+str(i),['Person'],'',{}) for i in range(2)]
            profiles=generator.generate_profiles_from_entities(entities,use_llm=False,parallel_count=2,graph_id=owner)
            assert len(profiles)==2
    assert sorted(seen)==sorted([('memory','alice'),('memory','bob'),('profile','alice'),('profile','alice'),('profile','bob'),('profile','bob')])


def test_oidc_application_startup_migrates_legacy_without_assigning_it(stores, tmp_path, monkeypatch):
    import app.storage as storage_module
    from app import create_app
    from app.models.project import ProjectManager
    from app.models.task import TaskManager
    from app.services.simulation_runner import SimulationRunner
    from app.services import workspace as w
    from test_authentication import login
    from test_logging_coverage import FakeNeo4jStorage
    with monkeypatch.context() as local:
        local.setattr(ProjectManager,'_repository',None)
        legacy=ProjectManager.create_project('unowned fictional legacy')
    monkeypatch.setattr(storage_module,'Neo4jStorage',FakeNeo4jStorage)
    monkeypatch.setattr(SimulationRunner,'register_cleanup',classmethod(lambda cls: None))
    monkeypatch.setattr(SimulationRunner,'_repository',None)
    class Configuration:
        TESTING=True
        DEBUG=False
        SECRET_KEY='x'*40
        AUTH_MODE='oidc'
        AUTH_ALLOW_HTTP_LOOPBACK=True
        AUTH_BASE_URL='http://localhost'
        AUTH_ISSUER='http://localhost:9999'
        AUTH_CLIENT_ID='test'
        AUTH_CLIENT_SECRET='secret'
        AUTH_ADMIN_EMAIL='admin@example.test'
        AUTH_DB_PATH=str(tmp_path/'auth.db')
        CONTROL_DB_PATH=str(stores.path)
        UPLOAD_FOLDER=str(tmp_path)
        OASIS_SIMULATION_DATA_DIR=str(tmp_path/'simulations')
        CORS_ORIGINS=[]
    app=create_app(Configuration)
    try:
        client=app.test_client();user,csrf=login(app,client)
        assert app.extensions['control_db_migration']['projects']==1
        assert client.get('/api/graph/project/'+legacy.project_id).status_code==404
        from test_administrator_quotas import configure
        configure(app, client, user, {'X-CrowdLens-CSRF': csrf})
        assert client.get('/api/graph/project/list').json['data']==[]
        created=client.post('/api/graph/case/create',json={'name':'owned fictional case'},headers={'X-CrowdLens-CSRF':csrf})
        assert created.status_code==200, created.json
        assert w._store.owner('case',created.json['data']['case_id'])==user['id']
        with pytest.raises(w.WorkspaceDenied): w.current_workspace()
    finally:
        TaskManager().runtime.close()


def test_audit_failure_cannot_change_authorization_or_completed_response(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import contextmanager
    from flask import Flask
    from app.authentication import install_authentication
    from app.services import workspace as w
    from test_authentication import login
    a=Flask('audit-failure')
    a.config.update(TESTING=True, SECRET_KEY='x'*40, AUTH_MODE='oidc', AUTH_ALLOW_HTTP_LOOPBACK=True,
        AUTH_BASE_URL='http://localhost', AUTH_ISSUER='http://localhost:9999', AUTH_CLIENT_ID='test',
        AUTH_CLIENT_SECRET='secret', AUTH_ADMIN_EMAIL='admin@example.test', AUTH_DB_PATH=str(tmp_path/'auth.db'))
    install_authentication(a)
    completed=[]
    @a.post('/api/write')
    def write():
        completed.append(True)
        return {'success':True}
    @a.get('/api/foreign')
    def foreign():
        w.require('project','foreign')
        return {'secret':'must never be returned'}
    client=a.test_client();_,csrf=login(a,client)
    original=w._store.connect
    @contextmanager
    def failing_audit_connection():
        with original() as db:
            class Connection:
                def execute(self, sql, *args):
                    if sql.startswith('INSERT INTO workspace_audit'):
                        raise sqlite3.OperationalError('fixture disk unavailable')
                    return db.execute(sql,*args)
            yield Connection()
    monkeypatch.setattr(w._store,'connect',failing_audit_connection)
    import logging
    from unittest.mock import Mock
    logger=logging.getLogger('mirofish.workspace')
    logged=Mock(wraps=logger.error)
    monkeypatch.setattr(logger,'error',logged)
    response=client.post('/api/write',headers={'X-CrowdLens-CSRF':csrf})
    assert response.status_code==200 and completed==[True]
    response=client.get('/api/foreign')
    assert response.status_code==404 and response.json=={'success':False,'error':'resource_not_found'}
    assert logged.call_count == 3
    assert all('Workspace audit unavailable' in call.args[0] for call in logged.call_args_list)


def test_empty_workspace_does_not_scan_control_tables(ownership, stores, monkeypatch):
    w, _=ownership
    with w.workspace_scope('empty'):
        monkeypatch.setattr(stores,'_transaction',lambda: pytest.fail('empty workspace scanned table'))
        assert stores.list_projects()==[]


def test_owner_lookup_failure_is_a_permission_denial(ownership, monkeypatch):
    import sqlite3
    w, store=ownership
    def unavailable(*args): raise sqlite3.OperationalError('fixture unavailable')
    monkeypatch.setattr(store,'owner',unavailable)
    monkeypatch.setattr(store,'owned_ids',unavailable)
    with w.workspace_scope('alice'):
        with pytest.raises(w.WorkspaceDenied): w.require('project','p')
        with pytest.raises(w.WorkspaceDenied): w.visible_ids('project')
