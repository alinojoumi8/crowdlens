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


@pytest.mark.parametrize('body', [[], {}, {'section_index': True, 'request_key':'a'},
    {'section_index': 1, 'request_key': 'a', 'scope': {}}, {'section_index': 20, 'request_key':'a'}])
def test_bad_creation_never_calls_model(app, body):
    app.extensions['evidence_llm_factory'] = lambda *a: pytest.fail('must not call model')
    assert app.test_client().post('/api/report/report_root/evidence-proposals', json=body).status_code == 400


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
