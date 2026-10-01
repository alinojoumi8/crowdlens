from types import SimpleNamespace as NS
from unittest.mock import Mock
import pytest
import requests
from app.utils.llm_client import LLMClient


def client(url):
    c = LLMClient.__new__(LLMClient)
    c.base_url, c.api_key, c.model, c.timeout, c._num_ctx = url, 'synthetic', 'fake', 300, 8192
    return c


@pytest.mark.parametrize('error', [requests.Timeout(), requests.ConnectionError(),
    requests.HTTPError(response=NS(status_code=429)), requests.HTTPError(response=NS(status_code=500))])
def test_anthropic_bounded_request_makes_one_attempt(monkeypatch, error):
    post = Mock(side_effect=error)
    monkeypatch.setattr('app.utils.llm_client.requests.post', post)
    with pytest.raises(requests.RequestException):
        client('https://example.invalid/anthropic').chat([], request_timeout=2, request_max_retries=0)
    assert post.call_count == 1
    assert post.call_args.kwargs['timeout'] == 2


def test_openai_client_is_request_scoped_and_usage_captured():
    c = client('https://example.invalid/v1')
    response = NS(model='actual', usage=NS(model_dump=lambda: {'prompt_tokens': 4, 'completion_tokens': 2}),
                  choices=[NS(message=NS(content='{}'))])
    bounded = NS(chat=NS(completions=NS(create=Mock(return_value=response))))
    c.client = NS(with_options=Mock(return_value=bounded))
    usage = Mock()
    assert c.chat_json([], request_timeout=7, request_max_retries=0, usage_callback=usage) == {}
    c.client.with_options.assert_called_once_with(timeout=7, max_retries=0)
    assert usage.call_args.args[1] == 'actual'


def test_native_ollama_timeout(monkeypatch):
    post = Mock(return_value=NS(raise_for_status=lambda: None,
        json=lambda: {'model': 'actual', 'message': {'content': '{}'}, 'prompt_eval_count': 3, 'eval_count': 4}))
    monkeypatch.setattr('app.utils.llm_client.requests.post', post)
    usage = Mock()
    assert client('http://localhost:11434/v1').chat_json([], disable_reasoning=True,
            request_timeout=3, request_max_retries=0, usage_callback=usage) == {}
    assert post.call_count == 1 and post.call_args.kwargs['timeout'] == 3
    assert usage.call_count == 1


def test_embedding_override_no_retry_no_model_pull(monkeypatch):
    from app.storage.embedding_service import EmbeddingService, EmbeddingError
    post = Mock(side_effect=requests.HTTPError(response=NS(status_code=500, text='private-response')))
    monkeypatch.setattr('app.storage.embedding_service.requests.post', post)
    monkeypatch.setattr('app.storage.embedding_service.requests.get', Mock(side_effect=AssertionError('no readiness/pull')))
    embedder = EmbeddingService(auto_pull=True)
    with pytest.raises(EmbeddingError):
        embedder.embed('synthetic', request_timeout=2, request_max_retries=0)
    assert post.call_count == 1 and post.call_args.kwargs['timeout'] == 2
