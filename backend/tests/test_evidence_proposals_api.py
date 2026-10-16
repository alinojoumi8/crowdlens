import time
from flask import Flask
import pytest
from evidence_draft_samples import sample_report
from app.services.report_agent import ReportManager
from app.services.proposal_store import ProposalStore
from test_evidence_drafting import FakeLLM, SourceStorage


@pytest.fixture
def app(tmp_path, monkeypatch):
    from app.api import report_bp
    from app.models.task import TaskManager
    monkeypatch.setattr(ReportManager, 'REPORTS_DIR', str(tmp_path))
    monkeypatch.setattr(TaskManager, '_repository', None)
    ReportManager.save_report(sample_report())
    app = Flask(__name__)
    app.register_blueprint(report_bp, url_prefix='/api/report')
    store = ProposalStore(tmp_path)
    app.extensions.update(neo4j_storage=SourceStorage(), evidence_proposal_store=store,
        evidence_llm_factory=lambda identifier: FakeLLM(store, identifier), evidence_embedder_factory=lambda: None)
    yield app
    import threading
    for thread in threading.enumerate():
        if thread.name == 'evidence-proposal':
            thread.join(10)
            assert not thread.is_alive(), 'proposal worker leaked beyond test'


def terminal(client, identifier):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f'/api/report/report_root/evidence-proposals/{identifier}')
        data = response.json['data']
        if data['state'] not in {'queued', 'running'}:
            return data
        time.sleep(.01)
    pytest.fail('worker did not finish')


def test_create_poll_accept_retry_and_guards(app):
    client = app.test_client()
    url = '/api/report/report_root/evidence-proposals'
    body = {'section_index': 1, 'request_key': 'api-key'}
    created = client.post(url, json=body)
    assert created.status_code == 202
    identifier = created.json['data']['proposal_id']
    assert client.post(url, json=body).json['data']['proposal_id'] == identifier
    assert client.post(url, json={**body, 'section_index': 2}).status_code == 409
    proposal = terminal(client, identifier)
    assert proposal['state'] == 'ready'
    import threading
    for worker in threading.enumerate():
        if worker.name == 'evidence-proposal': worker.join(10)
    accepted = client.post(url+f'/{identifier}/accept', json={'proposal_digest': proposal['proposal_digest']})
    assert accepted.status_code == 200
    revision = accepted.json['data']['report_id']
    assert client.post(url+f'/{identifier}/accept', json={'proposal_digest': proposal['proposal_digest']}).json['data']['report_id'] == revision
    assert client.post(f'/api/report/{revision}/section/1/regenerate', json={}).status_code == 409
    assert client.post(f'/api/report/{revision}/resume', json={}).status_code == 409
    assert client.get('/api/report/report_root/revisions').status_code == 200
    assert client.get(f'/api/report/other/evidence-proposals/{identifier}').status_code == 404


def test_staged_continuation_is_explicit_idempotent_and_reopens(app):
    from test_staged_source_review import large_storage, StagedLLM
    import threading
    store = app.extensions['evidence_proposal_store']
    app.extensions.update(neo4j_storage=large_storage(), evidence_llm_factory=lambda identifier: StagedLLM(store, identifier))
    client = app.test_client()
    url = '/api/report/report_root/evidence-proposals'
    identifier = client.post(url, json={'section_index': 1, 'request_key': 'staged'}).json['data']['proposal_id']
    record = terminal(client, identifier)
    assert record['state'] == 'review_pending'
    snapshot = store.read(identifier)
    storage = app.extensions.pop('neo4j_storage')
    unavailable = client.post(url + f'/{identifier}/continue', json={'proposal_digest': record['proposal_digest']})
    assert unavailable.status_code == 503 and unavailable.json['error'] == 'sources_unavailable'
    assert store.read(identifier) == snapshot
    app.extensions['neo4j_storage'] = storage
    assert client.post(url + f'/{identifier}/continue', json={'proposal_digest': 'wrong'}).status_code == 409
    assert client.post(f'/api/report/other/evidence-proposals/{identifier}/continue', json={'proposal_digest': record['proposal_digest']}).status_code == 404
    while record['state'] == 'review_pending':
        for worker in threading.enumerate():
            if worker.name == 'evidence-proposal': worker.join(10)
        digest = record['proposal_digest']
        body = {'proposal_digest': digest}
        response = client.post(url + f'/{identifier}/continue', json=body)
        assert response.status_code == 202
        record = terminal(client, identifier)
        replay = client.post(url + f'/{identifier}/continue', json=body)
        assert replay.status_code == 202 and replay.json['data']['proposal_digest'] == record['proposal_digest']
        assert client.get(url + f'/{identifier}').json['data']['source_review'] == record['source_review']
    assert record['state'] == 'ready' and record['source_completeness']['complete']
    for worker in threading.enumerate():
        if worker.name == 'evidence-proposal': worker.join(10)
    assert client.post(url + f'/{identifier}/accept', json={'proposal_digest': record['proposal_digest']}).status_code == 200


@pytest.mark.parametrize('body', [[], {}, {'section_index': True, 'request_key':'a'},
    {'section_index': 1, 'request_key': 'a', 'scope': {}}, {'section_index': 20, 'request_key':'a'}])
def test_bad_creation_never_calls_model(app, body):
    app.extensions['evidence_llm_factory'] = lambda *a: pytest.fail('must not call model')
    assert app.test_client().post('/api/report/report_root/evidence-proposals', json=body).status_code == 400


def legacy_project_scope(app, monkeypatch):
    """A real general report has no grounding and its saved config omits case IDs."""
    from types import SimpleNamespace
    from app.models.case import CaseManager
    from app.models.project import ProjectManager
    from evidence_draft_samples import SCOPE
    report = ReportManager.get_report('report_root')
    report.source_grounding = {}
    ReportManager.save_report(report)
    config = {'project_id': 'project_original', 'graph_id': SCOPE['graph_id']}
    original = SimpleNamespace(project_id='project_original', graph_id=SCOPE['graph_id'],
                               version_id=SCOPE['case_version_id'])
    newer = SimpleNamespace(project_id='project_newer', graph_id='graph_newer', version_id='version_newer')
    project = SimpleNamespace(case_id=SCOPE['case_id'], case_version_id='version_newer', graph_id='graph_newer')
    case = SimpleNamespace(case_id=SCOPE['case_id'], versions=[original, newer])
    monkeypatch.setattr('app.api.evidence_proposals.load_simulation_config', lambda _: config)
    monkeypatch.setattr(ProjectManager, 'get_project', lambda identifier: project if identifier == 'project_original' else None)
    monkeypatch.setattr(CaseManager, 'get_case', lambda identifier: case if identifier == SCOPE['case_id'] else None)
    return config, project, case


def test_general_report_proposal_uses_original_graph_version_without_mutating_parent(app, monkeypatch):
    from pathlib import Path
    from evidence_draft_samples import SCOPE
    legacy_project_scope(app, monkeypatch)
    root = Path(app.extensions['evidence_proposal_store'].root, 'report_root')
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    client = app.test_client()
    response = client.post('/api/report/report_root/evidence-proposals', json={'section_index': 1, 'request_key': 'general-scope'})
    assert response.status_code == 202
    proposal = terminal(client, response.json['data']['proposal_id'])
    assert proposal['state'] == 'ready'
    assert proposal['scope'] == SCOPE
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


@pytest.mark.parametrize('problem', ['missing_case', 'ambiguous_version', 'wrong_project', 'wrong_graph', 'wrong_case', 'wrong_version'])
def test_general_report_scope_recovery_fails_closed_without_model_calls(app, monkeypatch, problem):
    config, project, case = legacy_project_scope(app, monkeypatch)
    if problem == 'missing_case': project.case_id = 'case_missing'
    elif problem == 'ambiguous_version': case.versions.append(case.versions[0])
    elif problem == 'wrong_project': case.versions[0].project_id = 'project_other'
    elif problem == 'wrong_graph': config['graph_id'] = 'graph_other'
    elif problem == 'wrong_case': config['case_id'] = 'case_other'
    elif problem == 'wrong_version': config['case_version_id'] = 'version_other'
    app.extensions['evidence_llm_factory'] = lambda *a: pytest.fail('must not call model')
    response = app.test_client().post('/api/report/report_root/evidence-proposals', json={'section_index': 1, 'request_key': problem})
    assert response.status_code == 409
    assert response.json['error'] == 'missing_or_inconsistent_scope'


def test_watchdog_fences_late_response_without_releasing_capacity(app, monkeypatch):
    import threading
    entered, release = threading.Event(), threading.Event()
    original = app.extensions['evidence_llm_factory']
    def factory(identifier):
        llm = original(identifier)
        call = llm.chat_json
        def delayed(*args, **kw):
            entered.set(); release.wait(5)
            return call(*args, **kw)
        llm.chat_json = delayed
        return llm
    app.extensions['evidence_llm_factory'] = factory
    timers = []
    class ManualTimer:
        def __init__(self, seconds, callback):
            self.callback = callback
            timers.append(self)
        def start(self): pass
        def cancel(self): pass
    monkeypatch.setattr('app.api.evidence_proposals.threading.Timer', ManualTimer)
    client = app.test_client()
    response = client.post('/api/report/report_root/evidence-proposals', json={'section_index':1,'request_key':'slow'})
    identifier = response.json['data']['proposal_id']
    try:
        assert entered.wait(10)
        timers[0].callback()
        assert terminal(client, identifier)['state'] == 'failed'
        assert client.post('/api/report/report_root/evidence-proposals', json={'section_index':1,'request_key':'second'}).status_code == 409
    finally:
        release.set()
    time.sleep(.03)
    assert terminal(client, identifier)['state'] == 'failed'


@pytest.mark.parametrize('cancel', ['deadline', 'reject'])
def test_cancelled_worker_keeps_usage_from_completed_and_late_calls(app, monkeypatch, cancel):
    import threading
    entered, release = threading.Event(), threading.Event()
    original = app.extensions['evidence_llm_factory']
    def factory(identifier):
        llm = original(identifier)
        call = llm.chat_json
        def measured(*args, **kwargs):
            if len(llm.calls) == 1:
                entered.set(); release.wait(10)
            value = call(*args, **kwargs)
            kwargs['usage_callback']('synthetic', llm.model, {'input_tokens': 20, 'output_tokens': 10}, 5)
            return value
        llm.chat_json = measured
        return llm
    app.extensions['evidence_llm_factory'] = factory
    timers = []
    class ManualTimer:
        def __init__(self, seconds, callback): timers.append(callback)
        def start(self): pass
        def cancel(self): pass
    monkeypatch.setattr('app.api.evidence_proposals.threading.Timer', ManualTimer)
    client = app.test_client()
    url = '/api/report/report_root/evidence-proposals'
    identifier = client.post(url, json={'section_index': 1, 'request_key': 'measured'}).json['data']['proposal_id']
    try:
        assert entered.wait(10)
        if cancel == 'deadline':
            timers[0]()
        else:
            assert client.post(url + f'/{identifier}/reject', json={}).status_code == 200
    finally:
        release.set()
    for worker in threading.enumerate():
        if worker.name == 'evidence-proposal': worker.join(10)
    record = terminal(client, identifier)
    assert record['state'] == ('failed' if cancel == 'deadline' else 'rejected')
    assert len(record['usage']['calls']) == 2
    assert record['usage']['calls'][1]['output_tokens'] == 10
    assert record['timing']['drafting'] >= 0
    assert record['proposal_digest'] is None


def test_delete_busy_report_returns_conflict_without_traceback(app):
    store = app.extensions['evidence_proposal_store']
    with store.operation('report_root'):
        response = app.test_client().delete('/api/report/report_root')
    assert response.status_code == 409
    assert response.json == {'success': False, 'error': 'report_busy'}


@pytest.mark.parametrize('committed', [False, True])
def test_accept_endpoint_recovers_interrupted_publication(app, monkeypatch, committed):
    from app.services.report_revisions import ReportRevisionService
    client = app.test_client()
    url = '/api/report/report_root/evidence-proposals'
    identifier = client.post(url, json={'section_index': 1, 'request_key': 'recover'}).json['data']['proposal_id']
    proposal = terminal(client, identifier)
    import threading
    for worker in threading.enumerate():
        if worker.name == 'evidence-proposal': worker.join(10)
    original = ReportRevisionService._publish
    def interrupted(self, *args):
        if committed: original(self, *args)
        raise OSError('interrupted')
    monkeypatch.setattr(ReportRevisionService, '_publish', interrupted)
    body = {'proposal_digest': proposal['proposal_digest']}
    assert client.post(url + f'/{identifier}/accept', json=body).status_code == 503
    assert client.get(url + f'/{identifier}').json['data']['state'] == 'accepting'
    monkeypatch.setattr(ReportRevisionService, '_publish', original)
    response = client.post(url + f'/{identifier}/accept', json=body)
    assert response.status_code == 200
    assert response.json['data']['report_id'] == proposal['revision_report_id']


def test_milestone2_digest_concurrency_and_parent_integrity(app):
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    store = app.extensions['evidence_proposal_store']
    before = {p.name: p.read_bytes() for p in Path(store.root, 'report_root').iterdir()}
    client = app.test_client(); url = '/api/report/report_root/evidence-proposals'
    identifier = client.post(url, json={'section_index': 1, 'request_key': 'm2-concurrent'}).json['data']['proposal_id']
    proposal = terminal(client, identifier)
    import threading
    for worker in threading.enumerate():
        if worker.name == 'evidence-proposal': worker.join(10)
    assert client.post(url + f'/{identifier}/accept', json={'proposal_digest': 'stale'}).status_code == 409
    body = {'proposal_digest': proposal['proposal_digest']}
    def accept():
        with app.test_client() as other:
            return other.post(url + f'/{identifier}/accept', json=body).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: accept(), range(2)))
    assert all(status in {200, 409} for status in statuses) and 200 in statuses
    revision = client.post(url + f'/{identifier}/accept', json=body).json['data']
    assert revision['status'] == 'needs_review'
    assert revision['outline']['sections'][1] == sample_report().to_dict()['outline']['sections'][1]
    assert len(client.get('/api/report/report_root/revisions').json['data']) == 2
    assert {p.name:p.read_bytes() for p in Path(store.root, 'report_root').iterdir()} == before


def test_milestone2_new_store_recovers_published_revision_without_sources(app, monkeypatch):
    from app.services.report_revisions import ReportRevisionService
    client = app.test_client(); url = '/api/report/report_root/evidence-proposals'
    identifier = client.post(url, json={'section_index':1,'request_key':'m2-restart'}).json['data']['proposal_id']
    proposal = terminal(client, identifier)
    import threading
    for worker in threading.enumerate():
        if worker.name == 'evidence-proposal': worker.join(10)
    original = ReportRevisionService._publish
    def crash(self, *args):
        original(self, *args)
        raise OSError('synthetic post-publication interruption')
    monkeypatch.setattr(ReportRevisionService, '_publish', crash)
    body = {'proposal_digest':proposal['proposal_digest']}
    assert client.post(url+f'/{identifier}/accept',json=body).status_code == 503
    monkeypatch.setattr(ReportRevisionService, '_publish', original)
    app.extensions['evidence_proposal_store'] = ProposalStore(app.extensions['evidence_proposal_store'].root)
    app.extensions['neo4j_storage'] = None
    recovered = client.post(url+f'/{identifier}/accept',json=body)
    assert recovered.status_code == 200
    assert recovered.json['data']['report_id'] == proposal['revision_report_id']
    assert recovered.json['data']['status'] == 'needs_review'


def test_focused_creation_save_and_request_key_conflict(app):
    from types import SimpleNamespace
    from evidence_draft_samples import SCOPE
    from test_focused_correction import CORRECTION, Sources
    parent = ReportManager.get_report('report_root')
    parent.outline.sections[0].content = 'Alex denies signing in the May 29, 2025 affidavit.'
    ReportManager.save_report(parent)
    app.extensions['neo4j_storage'] = Sources()
    app.extensions['evidence_llm_factory'] = lambda _: SimpleNamespace(model='synthetic', chat_json=lambda *a, **kw: {'outcome':'supported','detail':'The same affidavit is dated 2023 in the original notice.'})
    client = app.test_client()
    url = '/api/report/report_root/evidence-proposals'
    body = {'section_index': 1, 'request_key': 'focused-api', 'focused_correction': CORRECTION}
    created = client.post(url, json=body)
    assert created.status_code == 202
    identifier = created.json['data']['proposal_id']
    changed = {**body, 'focused_correction': {**CORRECTION, 'old_text': 'May 29, 2024'}}
    assert client.post(url, json=changed).status_code == 409
    proposal = terminal(client, identifier)
    assert proposal['state'] == 'ready'
    # Ready content is visible before worker cleanup releases the operation lock.
    import threading
    for worker in threading.enumerate():
        if worker.name == 'evidence-proposal':
            worker.join(10)
            assert not worker.is_alive()
    accepted = client.post(url+f'/{identifier}/accept', json={'proposal_digest':proposal['proposal_digest']})
    assert accepted.status_code == 200, accepted.json
    revision = ReportManager.get_report(accepted.json['data']['report_id'])
    assert 'May 29, 2023' in revision.outline.sections[0].content
    assert revision.outline.summary == parent.outline.summary


def test_focused_bad_request_never_admits_model(app):
    app.extensions['evidence_llm_factory'] = lambda _: pytest.fail('must not call model')
    response = app.test_client().post('/api/report/report_root/evidence-proposals', json={
        'section_index':1, 'request_key':'invalid-focused', 'focused_correction':{'old_text':'could','new_text':'will','source_quote':'will'}})
    assert response.status_code == 400
