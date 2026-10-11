import errno
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

import pytest
import requests
from app.services import readiness as r


class Response:
    def __init__(self, body, status=200):
        self.body = json.dumps(body).encode()
        self.status_code = status
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def iter_content(self, chunk_size): yield self.body


@pytest.fixture(autouse=True)
def clear_probe_caches(monkeypatch):
    monkeypatch.setattr(r, 'MODEL_CACHE', r.ProbeCache())
    monkeypatch.setattr(r, 'DISK_CACHE', r.ProbeCache())


def test_metadata_get_is_cached_and_never_inference(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response({'data': [{'id':'model-x'}]})
    monkeypatch.setattr(r.requests, 'get', get)
    first = r.model_metadata('minimax', 'https://provider.invalid/v1', 'model-x', 'secret-test')
    again = r.model_metadata('minimax', 'https://provider.invalid/v1', 'model-x', 'secret-test')
    assert first['state'] == 'reachable' and first['model_available'] is True
    assert first['inference_verified'] is False and again['cached'] is True
    assert len(calls) == 1 and calls[0][0].endswith('/v1/models')
    assert calls[0][1]['allow_redirects'] is False and calls[0][1]['timeout'] == (1, 2)
    assert 'secret-test' not in json.dumps(first)
    r.model_metadata('minimax', 'https://provider.invalid/v1', 'other-model', 'secret-test')
    assert len(calls) == 2


@pytest.mark.parametrize('body,status,state', [
    ({'data': []},200,'missing_model'),
    ({'data': [],'has_more':True},200,'unverified'),
    ({'unexpected':True},200,'unverified'),
    ({},404,'unverified'), ({},405,'unverified'), ({},401,'unavailable'),
    ({},429,'unavailable'), ({},302,'unavailable'),
])
def test_metadata_states(monkeypatch, body, status, state):
    monkeypatch.setattr(r.requests, 'get', lambda *a, **k: Response(body, status))
    result = r.model_metadata('openai','https://provider.invalid/v1','model-x','key')
    assert result['state'] == state and result['inference_verified'] is False


def test_timeout_is_safe_and_does_not_return_old_healthy_result(monkeypatch):
    def timeout(*a, **k): raise requests.Timeout('includes-secret-url')
    monkeypatch.setattr(r.requests, 'get', timeout)
    result = r.model_metadata('openai','https://provider.invalid/v1','model-x','key')
    assert result['state'] == 'unavailable'
    assert 'includes-secret' not in json.dumps(result)


def test_local_model_tag_and_unsupported_provider(monkeypatch):
    seen=[]
    def get(url, **kwargs):
        seen.append(url)
        return Response({'models':[{'name':'nomic-embed-text:latest'}]})
    monkeypatch.setattr(r.requests, 'get', get)
    assert r.model_metadata('ollama','http://127.0.0.1:9999/v1','nomic-embed-text')['healthy']
    assert seen == ['http://127.0.0.1:9999/api/tags']
    assert r.model_metadata('other','https://provider.invalid','model','key')['state'] == 'unverified'
    assert r.model_metadata('openai','https://provider.invalid','model',None)['state'] == 'unconfigured'
    assert len(seen) == 1


def test_oversized_response_cannot_claim_ready(monkeypatch):
    response=Response({'data': [{'id':'model'}]});response.body=b'x'*(256*1024+1)
    monkeypatch.setattr(r.requests,'get',lambda *a, **k:response)
    assert r.model_metadata('openai','https://provider.invalid','model','key')['state']=='unverified'


def test_concurrent_polling_uses_one_probe_and_retry_uses_cache():
    cache=r.ProbeCache(); entered=Event(); finish=Event()
    def probe(): entered.set();finish.wait(2);return {'state':'reachable','healthy':True}
    with ThreadPoolExecutor() as pool:
        future=pool.submit(cache.get,'key',probe);assert entered.wait(1)
        assert cache.get('key',probe)['state']=='checking'
        finish.set();assert future.result()['healthy']
    assert cache.get('key',lambda:pytest.fail('not cached'))['cached']


def test_disk_probe_checks_actual_write_and_cleans_up(tmp_path):
    result=r.disk_readiness({'uploads':tmp_path},warning_bytes=0,critical_bytes=0)
    assert result['state']=='ready' and result['areas'][0]['writable']
    assert result['areas'][0]['free_bytes']>0
    assert list(tmp_path.iterdir())==[]


@pytest.mark.parametrize('free,state',[(10,'critical'),(1000,'warning'),(10000,'ready')])
def test_low_disk_is_actionable(tmp_path,monkeypatch,free,state):
    monkeypatch.setattr(r.os,'statvfs',lambda path:SimpleNamespace(f_bavail=free,f_frsize=1,f_blocks=20000,f_favail=10,f_files=10))
    result=r.disk_readiness({'uploads':tmp_path},warning_bytes=2000,critical_bytes=100)
    assert result['state']==state
    assert result['healthy'] == (state != 'critical')


def test_write_denied_and_missing_path_are_not_ready(tmp_path, monkeypatch):
    def denied(**kwargs): raise PermissionError(errno.EACCES,'private path')
    monkeypatch.setattr(r.tempfile,'NamedTemporaryFile',denied)
    result=r.disk_readiness({'uploads':tmp_path,'reports':tmp_path/'missing'})
    assert result['state']=='unavailable'
    assert all(not x['writable'] for x in result['areas'])
    assert 'private path' not in json.dumps(result)


def test_embedding_status_never_embeds_or_pulls(monkeypatch):
    from app.storage.embedding_service import EmbeddingService
    monkeypatch.setattr('app.storage.embedding_service.Config.GRAPH_EMBEDDING_CACHE_ENABLED',False)
    monkeypatch.setattr(r.requests,'get',lambda *a,**k:Response({'models':[{'name':'nomic-embed-text:latest'}]}))
    service=EmbeddingService(provider='ollama',model='nomic-embed-text',auto_pull=True)
    monkeypatch.setattr(service,'embed',lambda *a,**k:pytest.fail('inference from status'))
    monkeypatch.setattr(service,'ensure_ready',lambda *a,**k:pytest.fail('auto pull from status'))
    assert service.health_status()['healthy']
    assert service.health_status()['inference_verified'] is False


def test_overall_state_cannot_hide_missing_model_or_full_disk():
    from app.api.status import readiness_state
    healthy={'healthy':True};disk={'healthy':True,'state':'ready'};provider={'healthy':True,'state':'reachable'}
    assert readiness_state(healthy,provider,healthy,disk,provider)=='ready'
    assert readiness_state(healthy,provider,healthy,{**disk,'state':'warning'},provider)=='warning'
    assert readiness_state(healthy,provider,healthy,{**disk,'state':'critical'},provider)=='unavailable'
    assert readiness_state(healthy,provider,healthy,disk,{'state':'missing_model'})=='unavailable'
    assert readiness_state(healthy,provider,healthy,disk,{'state':'unverified'})=='unverified'
    assert readiness_state(healthy,provider,healthy,disk,{'state':'checking'})=='checking'


def test_gemini_uses_metadata_and_keeps_key_out_of_url(monkeypatch):
    calls=[]
    def get(url, **kwargs):
        calls.append((url,kwargs))
        return Response({'models':[{'name':'models/gemini-embedding-2'}]})
    monkeypatch.setattr(r.requests,'get',get)
    result=r.model_metadata('gemini','https://provider.invalid/v1beta','gemini-embedding-2','secret-test')
    assert result['state']=='reachable' and result['inference_verified'] is False
    assert calls[0][0]=='https://provider.invalid/v1beta/models'
    assert calls[0][1]['headers']=={'x-goog-api-key':'secret-test'}
