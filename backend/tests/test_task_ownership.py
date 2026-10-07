"""Task leases and publication fencing: synthetic SQLite, threads and subprocesses."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from app.models.task import TaskManager, TaskStatus
from app.storage.control_db import ControlDatabase


class Clock:
    def __init__(self): self.now = 1000.0
    def __call__(self): return self.now
    def advance(self, seconds=31): self.now += seconds


@pytest.fixture
def owned(tmp_path):
    from app.services.task_execution import TaskRuntime
    db = ControlDatabase(tmp_path/'control.db')
    clock = Clock()
    runtime = TaskRuntime(db, clock=clock)
    yield runtime, db, clock
    runtime.close()


def payload(identifier='task_synthetic', **metadata):
    return {'task_id':identifier,'task_type':'graph_build','status':'processing',
            'created_at':'2026-10-02T00:00:00','updated_at':'2026-10-02T00:00:00',
            'metadata':metadata}


def test_expired_owned_task_becomes_failed_and_rejects_old_writes(owned):
    from app.services.task_execution import OwnershipLost
    runtime, db, clock = owned
    attempt = runtime.admit(payload())
    clock.advance()
    runtime.reconcile()
    task = db.get_task('task_synthetic')
    assert task['status'] == 'failed'
    assert task['error'] == 'ownership_lease_expired'
    with pytest.raises(OwnershipLost):
        runtime.update(attempt, {'status':'completed', 'result':{'stale':True}})
    with pytest.raises(OwnershipLost): runtime.heartbeat(attempt)


def test_live_other_backend_is_preserved_and_pid_reuse_cannot_renew(owned):
    from app.services.task_execution import TaskRuntime, OwnershipLost
    runtime, db, clock = owned
    attempt = runtime.admit(payload())
    other = TaskRuntime(ControlDatabase(db.path), clock=clock)
    assert other.owner['pid'] == runtime.owner['pid']
    assert other.owner['worker_id'] != runtime.owner['worker_id']
    other.reconcile()
    assert db.get_task('task_synthetic')['status'] == 'processing'
    with pytest.raises(OwnershipLost): other.heartbeat(attempt)
    clock.advance(20)
    runtime.heartbeat(attempt)
    clock.advance(11)
    other.reconcile()
    assert db.get_task('task_synthetic')['status'] == 'processing'
    other.close()


def test_legacy_unknown_and_completed_tasks_are_preserved(owned):
    runtime, db, clock = owned
    db.put_task(payload('legacy'))
    done=payload('done'); done['status']='completed'; done['result']={'keep':True}
    db.put_task(done)
    clock.advance(1000)
    runtime.reconcile(); runtime.reconcile()
    assert db.get_task('legacy')['status'] == 'processing'
    assert db.get_task('legacy')['recovery']['reason'] == 'ownership_unknown'
    assert db.get_task('done') == done


def test_owning_subprocess_exit_is_recovered_by_another_process(tmp_path):
    code = '''
import sys,json
from app.models.task import TaskManager, TaskStatus
from app.storage.control_db import ControlDatabase
TaskManager.configure_repository(ControlDatabase(sys.argv[1]))
m=TaskManager(); i=m.create_task('graph_build'); m.update_task(i,status=TaskStatus.PROCESSING)
print(json.dumps({'task_id':i}))
'''
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path/'control.db')],
                          capture_output=True,text=True,check=True)
    identifier=json.loads(result.stdout.splitlines()[-1])['task_id']
    from app.services.task_execution import TaskRuntime
    import time
    db=ControlDatabase(tmp_path/'control.db')
    runtime=TaskRuntime(db,clock=lambda:time.time()+31)
    runtime.reconcile()
    assert db.get_task(identifier)['status']=='failed'
    assert db.get_task(identifier)['recovery']['reason']=='ownership_lease_expired'
    runtime.close()


def test_task_thread_exit_is_recovered_while_parent_is_alive(owned):
    runtime, db, clock = owned
    attempt=runtime.admit(payload())
    def terminate(): raise SystemExit('synthetic worker exit')
    worker=runtime.start(attempt, terminate)
    worker.join(2)
    assert not worker.is_alive()
    assert db.get_task(attempt.task_id)['status']=='failed'
    assert db.get_task(attempt.task_id)['error']=='execution_worker_exited'
    assert os.getpid()==runtime.owner['pid']


def test_required_child_exit_stops_renewal_while_parent_thread_lives(owned):
    runtime, db, clock = owned
    attempt=runtime.admit(payload())
    entered, release = threading.Event(), threading.Event()
    child=subprocess.Popen([sys.executable,'-c','pass'])
    def parent_task():
        with runtime.watch_child(attempt, child):
            entered.set(); release.wait(3)
    parent=runtime.start(attempt,parent_task)
    try:
        assert entered.wait(1)
        child.wait(timeout=3)
        assert parent.is_alive()
        clock.advance()
        runtime.tick()
        assert db.get_task(attempt.task_id)['status']=='failed'
        assert db.get_task(attempt.task_id)['error']=='ownership_lease_expired'
    finally:
        release.set(); parent.join(2)


def test_periodic_recovery_runs_without_restart_or_status_poll(owned, monkeypatch):
    import time
    import app.services.task_execution as module
    runtime, db, clock = owned
    attempt=runtime.admit(payload())
    monkeypatch.setattr(module,'RECOVERY_INTERVAL_SECONDS',.02)
    runtime.start_monitor()
    clock.advance()
    deadline=time.monotonic()+2
    while db.get_task(attempt.task_id)['status']!='failed' and time.monotonic()<deadline:
        time.sleep(.01)
    assert db.get_task(attempt.task_id)['status']=='failed'


@pytest.mark.parametrize('winner',['heartbeat','completion','expiry'])
def test_recovery_race_is_serialized_with_heartbeat_or_completion(owned, winner):
    from app.services.task_execution import OwnershipLost
    runtime, db, clock = owned
    attempt=runtime.admit(payload())
    done=threading.Event()
    # Hold the real publication gate while the competing recovery thread queues.
    with runtime.gate():
        reader=threading.Thread(target=lambda:(runtime.reconcile(),done.set()))
        reader.start()
        if winner=='heartbeat':
            clock.advance(29); runtime.heartbeat(attempt); clock.advance(2)
        elif winner=='completion':
            runtime.update(attempt,{'status':'completed','result':{'keep':True}}); clock.advance()
        else:
            clock.advance()
            with pytest.raises(OwnershipLost): runtime.heartbeat(attempt)
    reader.join(2)
    assert done.is_set()
    expected={'heartbeat':'processing','completion':'completed','expiry':'failed'}[winner]
    assert db.get_task(attempt.task_id)['status']==expected


def test_related_repair_is_repeatable_and_cannot_overwrite_new_attempt(owned, monkeypatch):
    runtime, db, clock = owned
    resource={'key':'project:proj_test'}
    old=runtime.admit(payload('old'),[resource])
    db.put_project({'project_id':'proj_test','status':'graph_building','graph_build_task_id':'old'})
    original=db.put_project
    def interrupted(value):
        original(value)
        raise OSError('synthetic interruption after related write')
    monkeypatch.setattr(db,'put_project',interrupted)
    clock.advance()
    with pytest.raises(OSError): runtime.reconcile()
    assert db.get_task('old')['recovery']['pending'] is True
    assert db.get_project('proj_test')['status']=='failed'
    monkeypatch.setattr(db,'put_project',original)
    runtime.reconcile(); runtime.reconcile()
    assert db.get_task('old')['recovery']['pending'] is False
    new=runtime.admit(payload('new'),[resource])
    db.put_project({'project_id':'proj_test','status':'graph_building','graph_build_task_id':'new'})
    # Replay an interrupted old outbox after a newer binding has been admitted.
    task=db.get_task('old');task['recovery']['pending']=True;db.put_task(task)
    runtime.reconcile()
    assert db.get_project('proj_test')['graph_build_task_id']=='new'
    assert db.get_project('proj_test')['status']=='graph_building'
    from app.services.task_execution import publication_guard, OwnershipLost
    with old.bind(),pytest.raises(OwnershipLost),publication_guard():
        db.put_project({'project_id':'proj_test','status':'graph_completed'})
    assert db.get_task(new.task_id)['status']=='processing'


@pytest.mark.parametrize('terminal',['generating','completed','needs_review','immutable'])
def test_report_repair_preserves_success_and_fences_stale_publication(owned,tmp_path,monkeypatch,terminal):
    from app.services.report_agent import ReportManager, ReportSection
    from app.services.task_execution import OwnershipLost
    runtime, db, clock=owned
    monkeypatch.setattr(ReportManager,'REPORTS_DIR',str(tmp_path/'reports'))
    monkeypatch.setattr(ReportManager,'FALLBACK_REPORTS_DIR',str(tmp_path/'reports'))
    folder=tmp_path/'reports'/'report_synthetic';folder.mkdir(parents=True)
    completed=terminal!='generating'
    status='generating' if terminal=='immutable' else terminal
    meta={'report_id':'report_synthetic','status':status,
          'revision':{'immutable':terminal=='immutable'},'created_at':'2026-10-02T00:00:00'}
    (folder/'meta.json').write_text(json.dumps(meta))
    (folder/'section_01.md').write_text('Preserve synthetic section')
    before={p.name:p.read_bytes() for p in folder.iterdir()}
    attempt=runtime.admit(payload(),[{'key':'report:report_synthetic','root':str(tmp_path/'reports')}])
    clock.advance();runtime.reconcile()
    assert (folder/'section_01.md').read_bytes()==before['section_01.md']
    assert json.loads((folder/'meta.json').read_text())['status']==(status if completed else 'interrupted')
    if completed: assert {p.name:p.read_bytes() for p in folder.iterdir()}==before
    with attempt.bind(),pytest.raises(OwnershipLost):
        ReportManager.save_section('report_synthetic',1,ReportSection(title='Synthetic',content='late'))
    assert (folder/'section_01.md').read_bytes()==before['section_01.md']


def test_report_recovery_retries_after_interruption_between_files(owned,tmp_path,monkeypatch):
    import app.services.proposal_store as module
    runtime,db,clock=owned
    folder=tmp_path/'reports'/'report_retry';folder.mkdir(parents=True)
    (folder/'meta.json').write_text(json.dumps({'status':'generating','revision':{}}))
    runtime.admit(payload(),[{'key':'report:report_retry','root':str(tmp_path/'reports')}])
    original=module.atomic_json
    def fail_progress(path,value):
        if path.name=='progress.json': raise OSError('synthetic interrupted progress write')
        original(path,value)
    monkeypatch.setattr(module,'atomic_json',fail_progress)
    clock.advance()
    with pytest.raises(OSError):runtime.reconcile()
    assert db.get_task('task_synthetic')['recovery']['pending'] is True
    monkeypatch.setattr(module,'atomic_json',original)
    runtime.reconcile();runtime.reconcile()
    assert json.loads((folder/'progress.json').read_text())['status']=='interrupted'
    assert db.get_task('task_synthetic')['recovery']['pending'] is False


def test_graph_api_recovers_task_and_project_and_admits_manual_retry(owned,tmp_path,monkeypatch):
    from flask import Flask
    from app.api import graph_bp
    from app.models.project import ProjectManager,ProjectStatus
    from app.services.graph_builder import GraphBuilderService
    runtime,db,clock=owned
    monkeypatch.setattr(TaskManager,'_repository',db)
    monkeypatch.setattr(TaskManager,'_runtime',runtime)
    monkeypatch.setattr(ProjectManager,'_repository',db)
    monkeypatch.setattr(ProjectManager,'PROJECTS_DIR',str(tmp_path/'projects'))
    project=ProjectManager.create_project('Synthetic ownership recovery')
    project.status=ProjectStatus.GRAPH_BUILDING;project.graph_build_task_id='abandoned'
    project.ontology={'entity_types':[],'edge_types':[]}
    ProjectManager.save_project(project)
    attempt=runtime.admit(payload('abandoned'),[{'key':'project:'+project.project_id}])
    app=Flask(__name__);app.register_blueprint(graph_bp,url_prefix='/api/graph')
    app.extensions['neo4j_storage']=object()  # No graph/model calls: dispatch is captured below.
    client=app.test_client()
    clock.advance()
    task=client.get('/api/graph/task/abandoned').json['data']
    assert task['status']=='failed' and task['error']=='ownership_lease_expired'
    loaded=client.get('/api/graph/project/'+project.project_id).json['data']
    assert loaded['status']=='failed'
    monkeypatch.setattr(ProjectManager,'get_extracted_text',classmethod(lambda cls,_:'Synthetic source'))
    monkeypatch.setattr(ProjectManager,'get_document_texts',classmethod(lambda cls,_:[]))
    dispatched=[]
    monkeypatch.setattr(TaskManager,'start_task',lambda self,*args,**kw:dispatched.append(args[0]))
    response=client.post('/api/graph/build',json={'project_id':project.project_id})
    assert response.status_code==200,response.json
    new_id=response.json['data']['task_id']
    assert dispatched==[new_id] and new_id!='abandoned'
    assert db.get_project(project.project_id)['status']=='graph_building'
    assert db.get_project(project.project_id)['graph_build_task_id']==new_id
    # Delayed old completion cannot replace new task/project state.
    from app.services.task_execution import OwnershipLost
    with attempt.bind(),pytest.raises(OwnershipLost):
        project.status=ProjectStatus.GRAPH_COMPLETED;ProjectManager.save_project(project)
    assert db.get_project(project.project_id)['graph_build_task_id']==new_id
    assert client.post('/api/graph/build',json={'project_id':project.project_id,'force':True}).status_code in {400,409}


def test_other_backend_real_live_execution_is_not_recovered(tmp_path):
    import time
    code = '''
import sys,time,json
from pathlib import Path
from app.models.task import TaskManager,TaskStatus
from app.storage.control_db import ControlDatabase
root=Path(sys.argv[1]);TaskManager.configure_repository(ControlDatabase(root/'control.db'))
m=TaskManager();identifier=m.create_task('synthetic_live')
def work():
 m.update_task(identifier,status=TaskStatus.PROCESSING)
 (root/'ready.json').write_text(json.dumps({'task_id':identifier}))
 while not (root/'finish').exists():time.sleep(.02)
 m.complete_task(identifier,{'synthetic':True})
thread=m.start_task(identifier,work);thread.join(8)
m.runtime.close()
'''
    writer=subprocess.Popen([sys.executable,'-c',code,str(tmp_path)],stdout=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+5
        while not (tmp_path/'ready.json').exists() and time.monotonic()<deadline:time.sleep(.02)
        identifier=json.loads((tmp_path/'ready.json').read_text())['task_id']
        from app.services.task_execution import TaskRuntime
        db=ControlDatabase(tmp_path/'control.db');reader=TaskRuntime(db)
        for _ in range(3):reader.reconcile()
        assert writer.poll() is None
        assert db.get_task(identifier)['status']=='processing'
        (tmp_path/'finish').touch();writer.wait(timeout=5)
        reader.reconcile()
        assert db.get_task(identifier)['status']=='completed'
        reader.close()
    finally:
        if writer.poll() is None:writer.terminate();writer.wait(timeout=5)


def test_expired_proposal_cannot_publish_or_replace_snapshot(owned,tmp_path):
    from app.services.proposal_store import ProposalStore
    from app.services.task_execution import OwnershipLost
    runtime,db,clock=owned
    store=ProposalStore(tmp_path/'reports')
    record,lease=store.admit('report_root','synthetic_request','synthetic_digest')
    identifier=record['proposal_id']
    attempt=runtime.admit(payload(),[{'key':'proposal:'+identifier,'root':str(store.root)}])
    with attempt.bind():
        store.update(identifier,{'queued'},{'state':'running'})
        store.save_snapshot(identifier,'sources',{'synthetic':True})
    clock.advance();runtime.reconcile()
    assert store.read(identifier)['state']=='failed'
    with attempt.bind(),pytest.raises(OwnershipLost):
        store.update(identifier,{'running'},{'state':'ready'})
    with attempt.bind(),pytest.raises(OwnershipLost):
        store.save_snapshot(identifier,'sources',{'late':True})
    lease.close()


def test_expired_graph_thread_cannot_execute_database_write(owned):
    from app.storage.neo4j_storage import Neo4jStorage
    from app.services.task_execution import OwnershipLost
    runtime,db,clock=owned
    attempt=runtime.admit(payload())
    clock.advance();runtime.reconcile()
    storage=Neo4jStorage.__new__(Neo4jStorage)
    calls=[]
    with attempt.bind(),pytest.raises(OwnershipLost):
        storage._call_with_retry(lambda:calls.append('write'))
    assert calls==[]


def test_unrepairable_resource_does_not_block_other_expired_tasks(owned,tmp_path):
    runtime,db,clock=owned
    folder=tmp_path/'reports'/'report_broken';folder.mkdir(parents=True)
    (folder/'meta.json').write_text('{broken synthetic json')
    runtime.admit(payload('broken'),[{'key':'report:report_broken','root':str(tmp_path/'reports')}])
    runtime.admit(payload('other'))
    clock.advance()
    result=runtime.reconcile(raise_on_error=False)
    assert result['repair_failed']==1
    assert db.get_task('broken')['recovery']['pending'] is True
    assert db.get_task('other')['status']=='failed'
    assert (folder/'meta.json').read_text()=='{broken synthetic json'


def test_legacy_build_is_not_swept_or_force_replaced(owned,tmp_path,monkeypatch):
    from flask import Flask
    from app.api import graph_bp
    from app.models.project import ProjectManager,ProjectStatus
    runtime,db,clock=owned
    monkeypatch.setattr(TaskManager,'_repository',db);monkeypatch.setattr(TaskManager,'_runtime',runtime)
    monkeypatch.setattr(ProjectManager,'_repository',db)
    monkeypatch.setattr(ProjectManager,'PROJECTS_DIR',str(tmp_path/'projects'))
    project=ProjectManager.create_project('Synthetic legacy uncertainty')
    project.status=ProjectStatus.GRAPH_BUILDING;project.graph_build_task_id='legacy'
    ProjectManager.save_project(project);db.put_task(payload('legacy'))
    clock.advance(10000)
    app=Flask(__name__);app.register_blueprint(graph_bp,url_prefix='/api/graph')
    response=app.test_client().post('/api/graph/build',json={'project_id':project.project_id,'force':True})
    assert response.status_code in {400,409}
    assert db.get_task('legacy')['status']=='processing'
    assert db.get_task('legacy')['recovery']['reason']=='ownership_unknown'
    assert db.get_project(project.project_id)['status']=='graph_building'


def test_schema_upgrade_preserves_legacy_records_and_adds_bindings(tmp_path):
    db=ControlDatabase(tmp_path/'control.db')
    legacy=payload('legacy');db.put_task(legacy)
    with db._transaction() as connection:
        connection.execute('DROP TABLE task_resources')
        connection.execute("UPDATE schema_migrations SET version=1 WHERE name='schema'")
    reopened=ControlDatabase(db.path)
    assert reopened.health_status()['schema_version']==2
    assert reopened.get_task('legacy')==legacy
    with reopened._transaction() as connection:
        assert connection.execute('SELECT count(*) FROM task_resources').fetchone()[0]==0


def test_unowned_project_mutation_cannot_bypass_active_binding(owned,tmp_path,monkeypatch):
    from app.models.project import ProjectManager,ProjectStatus
    from app.services.task_execution import TaskBusy
    runtime,db,clock=owned
    monkeypatch.setattr(TaskManager,'_repository',db);monkeypatch.setattr(TaskManager,'_runtime',runtime)
    monkeypatch.setattr(ProjectManager,'_repository',db)
    monkeypatch.setattr(ProjectManager,'PROJECTS_DIR',str(tmp_path/'projects'))
    project=ProjectManager.create_project('Synthetic active build')
    attempt=runtime.admit(payload(),[{'key':'project:'+project.project_id}])
    with attempt.bind():
        project.status=ProjectStatus.GRAPH_BUILDING;ProjectManager.save_project(project)
    with pytest.raises(TaskBusy):
        project.status=ProjectStatus.CREATED;ProjectManager.save_project(project)
    assert db.get_project(project.project_id)['status']=='graph_building'


def test_observed_normal_child_exit_allows_finalization_beyond_lease(owned):
    from types import SimpleNamespace
    runtime,db,clock=owned
    attempt=runtime.admit(payload('finalizing'))
    child=SimpleNamespace(poll=lambda:0)
    runtime.workers[attempt.task_id]=(attempt,SimpleNamespace(is_alive=lambda:True),[child])
    runtime.release_child(attempt,child)
    for _ in range(4):
        clock.advance(20)
        runtime.tick()
        runtime.validate(attempt)
    assert db.get_task(attempt.task_id)['status']=='processing'
    assert runtime.workers[attempt.task_id][2]==[]
