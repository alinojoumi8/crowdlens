"""Tests for website-URL ingestion: parsing, SSRF guard, and HTML-to-text."""

from dataclasses import dataclass, field

import pytest

from app.utils.url_fetcher import _fetch_url as fetch_url, parse_urls, _assert_public_host, _HTMLTextExtractor


def test_parse_urls_normalizes_and_dedupes():
    result = parse_urls("example.com\nhttps://foo.com/page, bar.org  https://foo.com/page")
    assert result == ["https://example.com", "https://foo.com/page", "https://bar.org"]


def test_parse_urls_accepts_list():
    assert parse_urls(["https://a.com", "b.com"]) == ["https://a.com", "https://b.com"]


def test_parse_urls_empty():
    assert parse_urls("") == []
    assert parse_urls(None) == []


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "169.254.169.254", "10.0.0.5", "::1", "0.0.0.0"])
def test_ssrf_guard_blocks_internal_hosts(host):
    with pytest.raises(ValueError):
        _assert_public_host(host)


def test_html_extractor_strips_tags_and_captures_title():
    html = (
        "<html><head><title> NovaCity News </title><style>.x{}</style></head>"
        "<body><nav>menu</nav><h1>Plan Approved</h1>"
        "<p>The council voted 7-2 to <b>approve</b> the plan.</p>"
        "<script>evil()</script><p>Opponents warned of costs.</p></body></html>"
    )
    ex = _HTMLTextExtractor()
    ex.feed(html)
    assert ex.title.strip() == "NovaCity News"
    text = ex.get_text()
    assert "Plan Approved" in text
    assert "approve the plan" in text
    assert "Opponents warned of costs" in text
    # Skipped content must not leak through.
    assert "evil()" not in text
    assert "menu" not in text


@dataclass
class _FakeResponse:
    url: str
    status_code: int
    headers: dict
    body: bytes = b""
    history: list = field(default_factory=list)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=65536):
        del chunk_size
        yield self.body

    @property
    def status(self):
        return self.status_code

    def getheader(self, key, default=None):
        return self.headers.get(key, default)

    def read(self, amount):
        data, self.body = self.body[:amount], self.body[amount:]
        return data

    def close(self):
        return None


class _FakeConnection:
    def __init__(self, response):
        self.response = response
        self.closed = False
        self.request_args = None

    def request(self, *args, **kwargs):
        self.request_args = (args, kwargs)

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


def test_fetch_url_rejects_private_redirect_before_requesting_it(monkeypatch):
    calls = []

    def connect(parsed, host, address):
        calls.append(parsed.geturl())
        return _FakeConnection(_FakeResponse(parsed.geturl(), 302,
            {'Location': 'http://127.0.0.1/api/tags'}))

    def public(host):
        if host == '127.0.0.1':
            raise ValueError('private host')
        return ('93.184.216.34',)

    monkeypatch.setattr('app.utils.url_fetcher._assert_public_host', public)
    monkeypatch.setattr('app.utils.url_fetcher._open_connection', connect)

    with pytest.raises(ValueError, match="private host"):
        fetch_url("https://public.example/start")

    assert calls == ['https://public.example/start']


def test_fetch_url_follows_public_redirect_and_preserves_readable_content(monkeypatch):
    responses = {
        "https://public.example/start": _FakeResponse(
            url="https://public.example/start",
            status_code=301,
            headers={"Location": "/article"},
        ),
        "https://public.example/article": _FakeResponse(
            url="https://public.example/article",
            status_code=200,
            headers={"Content-Type": "text/plain"},
            body=b"A legitimate public article with enough readable text.",
        ),
    }

    monkeypatch.setattr("app.utils.url_fetcher._assert_public_host", lambda host: ('93.184.216.34',))
    monkeypatch.setattr(
        "app.utils.url_fetcher._open_connection",
        lambda parsed, host, address: _FakeConnection(responses[parsed.geturl()]),
    )

    result = fetch_url("https://public.example/start")

    assert result == {
        "url": "https://public.example/article",
        "title": "public.example",
        "text": "A legitimate public article with enough readable text.",
    }
