"""Backup LLM on rate limits. No model calls: all transports are fakes."""
import json

import httpx
import pytest
import requests
from openai import OpenAI

from app.services.workflow_execution import WorkflowLedger, WorkflowHalt, execution_scope
from app.utils import llm_fallback
from app.utils.llm_client import LLMClient

MAIN = 'http://127.0.0.1:1/anthropic'
BACKUP = 'http://127.0.0.1:2/v1'
FALLBACK = dict(provider='openrouter', model='backup-model', base_url=BACKUP)
REPLY = {'id': 'chat_fixture', 'object': 'chat.completion', 'created': 0, 'model': 'backup-model',
         'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'from backup'}, 'finish_reason': 'stop'}],
         'usage': {'prompt_tokens': 4, 'completion_tokens': 2, 'total_tokens': 6}}


@pytest.fixture(autouse=True)
def backup_env(monkeypatch):
    monkeypatch.setenv('LLM_FALLBACK_API_KEY', 'synthetic')
    monkeypatch.setenv('LLM_FALLBACK_BASE_URL', BACKUP)
    monkeypatch.setenv('LLM_FALLBACK_MODEL_NAME', 'backup-model')
    monkeypatch.setenv('LLM_HTTP_MAX_RETRIES', '0')
    monkeypatch.setenv('LLM_FALLBACK_REASONING', 'off')
    monkeypatch.setattr('time.sleep', lambda seconds: None)
    llm_fallback.reset()
    yield
    llm_fallback.reset()


def authorize(ledger, fallback=FALLBACK, spend=None, key='fallback'):
    return ledger.authorize(request_key=key, provider='minimax', model='main-model', base_url=MAIN,
        input_description='fictional fixture', max_requests=10, max_seconds=60, confirmed=True,
        fallback=fallback, spend=spend)['workflow_id']


def response(status, body):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body).encode()
    return result


def test_workflow_admits_only_the_authorized_backup(tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite')
    wid = authorize(ledger)
    assert ledger.admit(wid, 1, 'report', 'backup-model', BACKUP)
    with pytest.raises(WorkflowHalt, match='provider_not_authorized'):
        ledger.admit(wid, 1, 'report', 'other-model', BACKUP)
    plain = authorize(ledger, fallback=None, key='plain')
    with pytest.raises(WorkflowHalt, match='provider_not_authorized'):
        ledger.admit(plain, 1, 'report', 'backup-model', BACKUP)


def test_priced_workflow_gets_no_backup(tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite')
    spend = dict(currency='USD', budget_usd='0.10', reserve_usd='0.05', input_usd_per_million='1',
                 output_usd_per_million='2', price_reference='fictional v1')
    wid = authorize(ledger, spend=spend)
    assert 'fallback' not in ledger.status(wid)
    with pytest.raises(WorkflowHalt, match='provider_not_authorized'):
        ledger.admit(wid, 1, 'report', 'backup-model', BACKUP)


def test_invalid_backup_identity_is_rejected(tmp_path):
    with pytest.raises(ValueError, match='invalid_fallback_identity'):
        authorize(WorkflowLedger(tmp_path / 'control.sqlite'), fallback=dict(provider='openrouter'))


def backup_transport(client, calls):
    backup = client._backup()
    def handler(request):
        calls.append('backup')
        assert json.loads(request.content)['reasoning'] == {'enabled': False}
        return httpx.Response(200, json=REPLY)
    backup.client = OpenAI(api_key='synthetic', base_url=BACKUP, max_retries=0,
                           http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_app_client_uses_backup_on_rate_limit_then_skips_main(monkeypatch, tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite')
    wid = authorize(ledger)
    calls = []
    def main(*args, **kwargs):
        calls.append('main')
        return response(429, {'error': {'type': 'rate_limit_error'}})
    monkeypatch.setattr(requests, 'post', main)
    with execution_scope(ledger, wid, 'report'):
        client = LLMClient(api_key='synthetic', base_url=MAIN, model='main-model')
        backup_transport(client, calls)
        assert client.chat([{'role': 'user', 'content': 'fixture'}]) == 'from backup'
        assert client.chat([{'role': 'user', 'content': 'fixture'}]) == 'from backup'
    # The second call skipped the limited main model.
    assert calls == ['main', 'backup', 'backup']
    assert [a['model'] for a in ledger.status(wid)['attempts']] == ['main-model', 'backup-model', 'backup-model']


def test_app_client_does_not_hide_other_errors(monkeypatch, tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite')
    wid = authorize(ledger)
    calls = []
    monkeypatch.setattr(requests, 'post', lambda *a, **k: response(400, {'error': 'bad request'}))
    with execution_scope(ledger, wid, 'report'):
        client = LLMClient(api_key='synthetic', base_url=MAIN, model='main-model')
        backup_transport(client, calls)
        with pytest.raises(requests.HTTPError):
            client.chat([{'role': 'user', 'content': 'fixture'}])
    assert calls == [] and not llm_fallback.primary_limited('main-model', MAIN)


def test_no_backup_without_configuration(monkeypatch):
    monkeypatch.delenv('LLM_FALLBACK_API_KEY')
    assert llm_fallback.fallback_settings() is None
    assert LLMClient(api_key='synthetic', base_url=MAIN, model='main-model')._backup() is None


def test_simulation_agent_uses_backup_on_rate_limit(monkeypatch, tmp_path):
    from scripts.llm_provider_adapter import AnthropicMessagesModel
    ledger = WorkflowLedger(tmp_path / 'control.sqlite')
    wid = authorize(ledger)
    urls = []
    def post(url, **kwargs):
        urls.append(url)
        if url.startswith(MAIN):
            return response(529, {'error': {'type': 'overloaded_error'}})
        assert kwargs['json']['model'] == 'backup-model'
        return response(200, REPLY)
    monkeypatch.setattr(requests, 'post', post)
    model = AnthropicMessagesModel(model_type='main-model', api_key='synthetic', url=MAIN, max_retries=0)
    with execution_scope(ledger, wid, 'simulation'):
        result = model.run([{'role': 'user', 'content': 'fixture'}])
    assert result.choices[0].message.content == 'from backup'
    assert urls == [MAIN + '/v1/messages', BACKUP + '/chat/completions']


@pytest.mark.parametrize('status, body, limited', [
    (429, '', True),
    (529, '', True),
    (400, '{"error": "insufficient balance"}', True),
    (403, '{"error": "Usage limit exceeded for this plan"}', True),
    (400, '{"error": "invalid prompt"}', False),
])
def test_limit_error_detection(status, body, limited):
    result = requests.Response()
    result.status_code = status
    result._content = body.encode()
    assert llm_fallback.is_limit_error(requests.HTTPError(response=result)) is limited


def test_configuration_and_authorization_include_the_backup(monkeypatch, tmp_path):
    from app import create_app
    from app.config import Config
    monkeypatch.setattr(Config, 'LLM_API_KEY', 'synthetic')
    monkeypatch.setattr(Config, 'LLM_MODEL_NAME', 'main-model')
    monkeypatch.setattr(Config, 'LLM_BASE_URL', MAIN)
    monkeypatch.setattr(Config, 'LLM_DEFAULT_PROVIDER', 'minimax')
    monkeypatch.setenv('LLM_FALLBACK_PROVIDER', 'openrouter')
    app = create_app()
    client = app.test_client()
    data = client.get('/api/execution/configuration').get_json()['data']
    assert data['fallback'] == dict(provider='openrouter', model='backup-model')
    assert 'api_key' not in json.dumps(data)


def test_workflow_without_backup_keeps_using_main_during_cooldown(monkeypatch, tmp_path):
    ledger = WorkflowLedger(tmp_path / 'control.sqlite')
    wid = authorize(ledger, fallback=None)
    llm_fallback.mark_primary_limited('main-model', MAIN)
    monkeypatch.setattr(requests, 'post', lambda *a, **k: response(
        200, {'content': [{'type': 'text', 'text': 'from main'}], 'usage': {'output_tokens': 2}}))
    with execution_scope(ledger, wid, 'report'):
        client = LLMClient(api_key='synthetic', base_url=MAIN, model='main-model')
        assert client.chat([{'role': 'user', 'content': 'fixture'}]) == 'from main'
        # A rate limit on a workflow with no backup keeps the original error.
        monkeypatch.setattr(requests, 'post', lambda *a, **k: response(429, {'error': 'rate limit'}))
        with pytest.raises(requests.HTTPError):
            client.chat([{'role': 'user', 'content': 'fixture'}])


def test_backup_keeps_agent_generation_settings_and_may_share_the_model_name(monkeypatch, tmp_path):
    from scripts.llm_provider_adapter import AnthropicMessagesModel
    monkeypatch.setenv('LLM_FALLBACK_MODEL_NAME', 'main-model')
    ledger = WorkflowLedger(tmp_path / 'control.sqlite')
    wid = authorize(ledger, fallback=dict(FALLBACK, model='main-model'))
    bodies = []
    def post(url, **kwargs):
        if url.startswith(MAIN):
            return response(429, {'error': 'rate limit'})
        bodies.append(kwargs['json'])
        return response(200, REPLY)
    monkeypatch.setattr(requests, 'post', post)
    model = AnthropicMessagesModel(model_type='main-model', api_key='synthetic', url=MAIN, max_retries=0,
                                   model_config_dict={'max_tokens': 128, 'temperature': 0})
    with execution_scope(ledger, wid, 'simulation'):
        model.run([{'role': 'user', 'content': 'fixture'}])
    assert bodies[0]['max_tokens'] == 128 and bodies[0]['temperature'] == 0
    assert bodies[0]['reasoning'] == {'enabled': False}


@pytest.mark.parametrize('sent, accepted', [
    (dict(provider='openrouter', model='backup-model'), True),
    (None, False),
    (dict(provider='openrouter', model='old-model'), False),
])
def test_authorization_rejects_a_backup_the_user_did_not_see(monkeypatch, tmp_path, sent, accepted):
    from app import create_app
    from app.config import Config
    for name, value in dict(LLM_API_KEY='synthetic', LLM_MODEL_NAME='main-model', LLM_BASE_URL=MAIN,
                            LLM_DEFAULT_PROVIDER='minimax').items():
        monkeypatch.setattr(Config, name, value)
    monkeypatch.setenv('LLM_FALLBACK_PROVIDER', 'openrouter')
    client = create_app().test_client()
    result = client.post('/api/execution/authorize', json=dict(provider='minimax', model='main-model',
        fallback=sent, request_key='key-' + str(accepted) + str(sent), input_description='fictional',
        max_requests=5, max_seconds=60, confirmed=True))
    if accepted:
        assert result.status_code == 201
        assert result.get_json()['data']['fallback']['model'] == 'backup-model'
    else:
        assert result.status_code == 409 and result.get_json()['error'] == 'provider_identity_changed'


def test_cooldown_belongs_to_one_main_model():
    llm_fallback.mark_primary_limited('main-model', MAIN)
    assert llm_fallback.primary_limited('main-model', MAIN + '/v1/messages')
    assert not llm_fallback.primary_limited('other-model', MAIN)


@pytest.mark.parametrize('provider, setting, expected', [
    ('openrouter', 'off', {'reasoning': {'enabled': False}}),
    ('openrouter', None, {}),
    ('other', 'off', {}),
])
def test_thinking_off_is_opt_in_for_openrouter(monkeypatch, provider, setting, expected):
    monkeypatch.setenv('LLM_FALLBACK_PROVIDER', provider)
    monkeypatch.delenv('LLM_FALLBACK_REASONING')
    if setting:
        monkeypatch.setenv('LLM_FALLBACK_REASONING', setting)
    assert llm_fallback.fallback_settings()['extra_body'] == expected
