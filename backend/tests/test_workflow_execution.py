import concurrent.futures
import pytest

from app.services.workflow_execution import WorkflowLedger, WorkflowHalt, execution_scope
from app.utils.llm_client import LLMClient


def authorize(ledger, limit=3, seconds=60):
    return ledger.authorize(request_key='synthetic', provider='synthetic', model='synthetic',
        base_url='http://127.0.0.1:1/anthropic', input_description='fictional fixture',
        max_requests=limit, max_seconds=seconds, confirmed=True)['workflow_id']


def test_atomic_admission_persists_across_connections_and_restart(tmp_path):
    path = tmp_path / 'control.sqlite'
    ledger = WorkflowLedger(path)
    wid = authorize(ledger, 4)
    def submit(i):
        try:
            return WorkflowLedger(path).admit(wid, 1, 'graph', 'synthetic',
                'http://127.0.0.1:1/anthropic', attempt_number=i)
        except WorkflowHalt:
            return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(submit, range(20)))
    assert len([x for x in results if x]) == 4
    after = WorkflowLedger(path).status(wid)
    assert after['admitted'] == 4 and after['unknown_usage_attempts'] == 4
    assert authorize(ledger, 4) == wid
    assert ledger.status(wid)['admitted'] == 4


def test_stop_and_runtime_close_admission_without_refund(tmp_path):
    now = [1000.0]
    ledger = WorkflowLedger(tmp_path / 'control.sqlite', clock=lambda: now[0])
    wid = authorize(ledger)
    ticket = ledger.admit(wid, 1, 'simulation', 'synthetic', 'http://127.0.0.1:1/anthropic')
    ledger.stop(wid)
    with pytest.raises(WorkflowHalt, match='stopped'):
        ledger.admit(wid, 1, 'report', 'synthetic', 'http://127.0.0.1:1/anthropic')
    ledger.finish(ticket, status='response', usage={'input_tokens': 10}, http_status=200)
    assert ledger.status(wid)['admitted'] == 1
    assert ledger.status(wid)['in_flight'] == 0
    ledger.reauthorize(wid, max_requests=5, max_seconds=30, confirmed=True,
        acknowledge_unknown=True, request_key='explicit-extension')
    with pytest.raises(WorkflowHalt, match='superseded'):
        ledger.checkpoint(wid, 1)
    now[0] += 31
    with pytest.raises(WorkflowHalt, match='runtime_limit'):
        ledger.admit(wid, 2, 'report', 'synthetic', 'http://127.0.0.1:1/anthropic')
    assert ledger.status(wid)['admitted'] == 1


def test_physical_retries_are_counted_and_late_result_is_rejected(tmp_path, monkeypatch):
    import requests
    from types import SimpleNamespace
    ledger = WorkflowLedger(tmp_path / 'control.sqlite')
    wid = authorize(ledger, 2)
    calls = []
    def transport(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise requests.Timeout('injected timeout; delivery unknown')
        ledger.stop(wid)
        return SimpleNamespace(status_code=200, raise_for_status=lambda: None,
            json=lambda: {'content': [{'type':'text','text':'late'}], 'usage': {'output_tokens':7}})
    monkeypatch.setattr(requests, 'post', transport)
    monkeypatch.setattr('app.utils.llm_client.time.sleep', lambda n: None)
    with execution_scope(ledger, wid, 'report'):
        client = LLMClient(api_key='synthetic', base_url='http://127.0.0.1:1/anthropic', model='synthetic')
        with pytest.raises(WorkflowHalt):
            client.chat([{'role':'user','content':'fixture'}], request_max_retries=3)
    status = ledger.status(wid)
    assert len(calls) == status['admitted'] == 2
    assert status['unknown_usage_attempts'] == 2
    assert status['usage_by_stage']['report']['output_tokens'] == 7


def test_unscoped_application_transport_requires_authorization(monkeypatch):
    from app.services import workflow_execution as controls
    from types import SimpleNamespace
    monkeypatch.setattr(controls, '_ALLOW_UNSCOPED', False, raising=False)
    calls = []
    def transport(*a, **k):
        calls.append(1)
        return SimpleNamespace(status_code=200, raise_for_status=lambda:None,
            json=lambda:{'content':[{'type':'text','text':'unapproved'}]})
    monkeypatch.setattr('app.utils.llm_client.requests.post', transport)
    client = LLMClient(api_key='synthetic', base_url='http://127.0.0.1:1/anthropic', model='synthetic')
    with pytest.raises(WorkflowHalt, match='authorization_required'):
        client.chat([{'role':'user','content':'fixture'}])
    assert calls == []


@pytest.mark.parametrize('kind',['openai','oasis-anthropic','oasis-openai'])
def test_transport_retries_share_physical_allowance(tmp_path,monkeypatch,kind):
    import httpx, requests, json
    from openai import OpenAI
    ledger=WorkflowLedger(tmp_path/'transport.sqlite')
    base='http://127.0.0.1:1/anthropic' if kind=='oasis-anthropic' else 'http://127.0.0.1:1/v1'
    wid=ledger.authorize(request_key='transport',provider='synthetic',model='synthetic',base_url=base,input_description='fictional',max_requests=2,max_seconds=60,confirmed=True)['workflow_id']
    calls=[]
    reply={'id':'chat_fixture','object':'chat.completion','created':0,'model':'synthetic','choices':[{'index':0,'message':{'role':'assistant','content':'fixture'},'finish_reason':'stop'}],'usage':{'prompt_tokens':4,'completion_tokens':2,'total_tokens':6}}
    monkeypatch.setattr('time.sleep',lambda seconds:None)
    if kind=='openai':
        def handler(request):
            calls.append(1)
            return httpx.Response(503,json={'error':{'message':'injected'}}) if len(calls)==1 else httpx.Response(200,json=reply)
        client=LLMClient(api_key='synthetic',base_url=base,model='synthetic')
        client.client=OpenAI(api_key='synthetic',base_url=base,max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        generate=lambda:client.chat([{'role':'user','content':'fixture'}],request_max_retries=5)
    else:
        from scripts.llm_provider_adapter import AnthropicMessagesModel,CountedOpenAIModel
        def post(*a,**k):
            calls.append(1);response=requests.Response();response.status_code=503 if len(calls)==1 else 200
            content={'content':[{'type':'text','text':'fixture'}],'usage':{'input_tokens':4,'output_tokens':2}} if kind=='oasis-anthropic' else reply
            response._content=json.dumps({'error':'injected'} if len(calls)==1 else content).encode()
            return response
        monkeypatch.setattr(requests,'post',post)
        model=(AnthropicMessagesModel if kind=='oasis-anthropic' else CountedOpenAIModel)(model_type='synthetic',api_key='synthetic',url=base,max_retries=5)
        generate=lambda:model.run([{'role':'user','content':'fixture'}])
    with execution_scope(ledger,wid,'simulation'):
        assert generate()
        with pytest.raises(WorkflowHalt,match='request_limit'):generate()
    status=ledger.status(wid)
    assert len(calls)==status['admitted']==2
    assert status['unknown_usage_attempts']==1
    assert len([item for item in status['attempts'] if item['stage']=='simulation'])==2


def test_native_ollama_records_usage_without_contacting_local_model(tmp_path,monkeypatch):
    from types import SimpleNamespace
    ledger=WorkflowLedger(tmp_path/'native.sqlite');base='http://127.0.0.1:11434/v1'
    wid=ledger.authorize(request_key='native',provider='synthetic',model='synthetic',base_url=base,input_description='fictional',max_requests=1,max_seconds=60,confirmed=True)['workflow_id']
    calls=[]
    def post(url,**kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=200,raise_for_status=lambda:None,json=lambda:{'message':{'content':'{"fixture":true}'},'prompt_eval_count':3,'eval_count':2})
    monkeypatch.setattr('requests.post',post)
    with execution_scope(ledger,wid,'ontology'):
        assert LLMClient(api_key='synthetic',base_url=base,model='synthetic').chat_json([{'role':'user','content':'fixture'}],disable_reasoning=True)=={'fixture':True}
    assert calls==['http://127.0.0.1:11434/api/chat']
    assert ledger.status(wid)['unknown_usage_attempts']==0


def test_non_retryable_http_error_consumes_only_one_attempt(tmp_path,monkeypatch):
    import requests
    ledger=WorkflowLedger(tmp_path/'error.sqlite');wid=authorize(ledger)
    calls=[]
    def post(*a,**kw):
        calls.append(1);response=requests.Response();response.status_code=400
        raise requests.HTTPError('injected validation failure',response=response)
    monkeypatch.setattr(requests,'post',post)
    with execution_scope(ledger,wid,'report'),pytest.raises(requests.HTTPError):
        LLMClient(api_key='synthetic',base_url='http://127.0.0.1:1/anthropic',model='synthetic').chat([{'role':'user','content':'fixture'}],request_max_retries=4)
    assert len(calls)==ledger.status(wid)['admitted']==1
