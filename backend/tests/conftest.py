"""Unit tests are offline regardless of an operator's local rollout flags."""
import pytest


@pytest.fixture(autouse=True)
def forbid_real_external_http(monkeypatch):
    """Tests may use controlled loopback providers or mocked HTTP, never paid inference."""
    from urllib.parse import urlparse
    import requests
    import httpx
    from app.services import workflow_execution
    # Existing transport unit tests call mocked providers outside app workflows.
    # Their actual network transports remain fenced below.
    monkeypatch.setattr(workflow_execution, '_ALLOW_UNSCOPED', True)
    def check(url):
        parsed = urlparse(str(url))
        if parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise AssertionError('External HTTP blocked in offline tests')
        if parsed.port == 11434 or parsed.path.endswith('/api/pull'):
            raise AssertionError('Existing model services and downloads blocked in offline tests')
    original_request = requests.sessions.Session.request
    def guarded_request(self, method, url, *args, **kwargs):
        check(url)
        return original_request(self, method, url, *args, **kwargs)
    original_send = httpx.Client.send
    def guarded_send(self, request, *args, **kwargs):
        if not isinstance(self._transport, httpx.MockTransport):
            check(request.url)
        return original_send(self, request, *args, **kwargs)
    original_async_send = httpx.AsyncClient.send
    async def guarded_async_send(self, request, *args, **kwargs):
        if not isinstance(self._transport, httpx.MockTransport):
            check(request.url)
        return await original_async_send(self, request, *args, **kwargs)
    monkeypatch.setattr(requests.sessions.Session, 'request', guarded_request)
    monkeypatch.setattr(httpx.Client, 'send', guarded_send)
    monkeypatch.setattr(httpx.AsyncClient, 'send', guarded_async_send)


@pytest.fixture(autouse=True)
def disable_live_jev(monkeypatch):
    from app.config import Config
    for name in ('JEV_INTERVIEW_MODE', 'JEV_RERANK_MODE', 'JEV_EVIDENCE_MODE'):
        monkeypatch.setattr(Config, name, 'off')
