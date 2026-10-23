"""Fetch and extract readable text from a web URL.

Lets users seed a simulation from a website link alongside uploaded PDF/MD/TXT
files. Uses pinned standard-library HTTP connections inside a bounded worker.
Every redirect is validated before connecting; internal services and translated
address forms are refused.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from html.parser import HTMLParser
from typing import Dict, List
from urllib.parse import urljoin, urlparse

import http.client
import ssl
import time

# Conservative caps for a user-initiated fetch.
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
REQUEST_TIMEOUT = 20  # seconds
MAX_REDIRECTS = 5
USER_AGENT = "CrowdLens/1.0 (+document ingestion)"

# Tags whose inner content is never readable page text. (Not "head": <title> lives
# there and is captured separately; head's script/style/meta carry no body text.)
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "nav", "footer"}
# Block-level tags that should introduce a line break in the extracted text.
_BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "section", "article", "header",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "ul", "ol", "table",
}


class _HTMLTextExtractor(HTMLParser):
    """Strip HTML to plain text, skipping non-content tags and capturing <title>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self.title = ""
        self._parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._in_title:
            self.title += data
        if data.strip():
            self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        # Collapse runs of spaces/tabs and excess blank lines.
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def parse_urls(raw) -> List[str]:
    """Split a free-form string (or list) of URLs into a clean, de-duplicated list."""
    items: List[str] = []
    if isinstance(raw, (list, tuple)):
        if any(not isinstance(item, str) for item in raw):
            raise ValueError('Source URLs must be strings.')
        candidates = [part for item in raw for part in re.split(r'[\s,]+', item)]
    elif isinstance(raw, str):
        candidates = re.split(r"[\s,]+", raw)
    else:
        return []
    seen = set()
    for candidate in candidates:
        if not isinstance(candidate, str):
            raise ValueError('Source URLs must be strings.')
        url = candidate.strip()
        if not url:
            continue
        if re.match(r'^[a-z][a-z0-9+.-]*:', url, re.IGNORECASE) and not re.match(r'^https?://', url, re.IGNORECASE):
            raise ValueError('Only HTTP/HTTPS source URLs are supported.')
        if not re.match(r"^https?://", url, re.IGNORECASE):
            url = "https://" + url
        _validated_url(url)
        if url not in seen:
            seen.add(url)
            items.append(url)
    return items


def _assert_public_host(host: str):
    """Resolve once; every address must be globally routable before connecting."""
    if not host or '%' in host:
        raise ValueError('URL has no valid public host.')
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        raise ValueError('Could not resolve URL host.') from None
    addresses = []
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        translated = isinstance(ip, ipaddress.IPv6Address) and any(ip in ipaddress.ip_network(n)
            for n in ('64:ff9b::/96', '64:ff9b:1::/48', '2002::/16', '2001::/32'))
        if not ip.is_global or ip.is_multicast or translated or getattr(ip, 'ipv4_mapped', None):
            raise ValueError('Refusing to fetch internal/private or translated address.')
        addresses.append(str(ip))
    if not addresses:
        raise ValueError('URL host has no public addresses.')
    return tuple(dict.fromkeys(addresses))


def _validated_url(url):
    if not isinstance(url, str) or len(url) > 4096 or any(ord(c) <= 32 or ord(c) == 127 for c in url) or '\\' in url:
        raise ValueError('Invalid source URL.')
    try:
        parsed = urlparse(url)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or
                parsed.username is not None or parsed.password is not None or
                parsed.port not in {None, 80 if parsed.scheme == 'http' else 443}):
            raise ValueError('Only public HTTP/HTTPS URLs on their standard ports are supported.')
        host = parsed.hostname.encode('idna').decode('ascii')
    except (UnicodeError, ValueError):
        raise ValueError('Only public HTTP/HTTPS URLs without credentials on standard ports are supported.') from None
    return parsed, host


def _open_connection(parsed, host, address):
    """Pin the socket to the validated IP; retain hostname verification and SNI.

    No proxy environment, cookie jar, netrc authentication or second hostname DNS
    lookup participates in this connection.
    """
    port = 443 if parsed.scheme == 'https' else 80
    if parsed.scheme == 'https':
        import certifi
        conn = http.client.HTTPSConnection(host, port, timeout=REQUEST_TIMEOUT,
                                          context=ssl.create_default_context(cafile=certifi.where()))
    else:
        conn = http.client.HTTPConnection(host, port, timeout=REQUEST_TIMEOUT)
    conn._create_connection = lambda ignored, timeout, source_address=None: socket.create_connection(
        (address, port), timeout, source_address)
    try:
        conn.connect()
        if ipaddress.ip_address(conn.sock.getpeername()[0]) != ipaddress.ip_address(address):
            raise ValueError('Source connection address did not match the validated address.')
        return conn
    except BaseException:
        conn.close()
        raise


def _domain_name(url: str) -> str:
    return urlparse(url).netloc


def fetch_url(url: str) -> Dict[str, str]:
    from .ingestion import run_ingestion
    _validated_url(url)
    return run_ingestion('url', url)


def _fetch_url(url: str) -> Dict[str, str]:
    current_url = url
    deadline = time.monotonic() + REQUEST_TIMEOUT
    for redirect_count in range(MAX_REDIRECTS + 1):
        parsed, host = _validated_url(current_url)
        addresses = _assert_public_host(host)
        conn = _open_connection(parsed, host, addresses[0])
        response = None
        try:
            path = parsed.path or '/'
            if parsed.query:
                path += '?' + parsed.query
            conn.request('GET', path, headers={'User-Agent': USER_AGENT,
                'Accept': 'text/html,text/plain,text/markdown,application/pdf', 'Accept-Encoding': 'identity'})
            response = conn.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader('Location')
                if not location or redirect_count >= MAX_REDIRECTS:
                    raise ValueError('Missing redirect destination or too many redirects.')
                current_url = urljoin(current_url, location)
                continue
            if response.status != 200:
                raise ValueError('Source server did not return a successful document.')
            if response.getheader('Content-Encoding', 'identity').lower() not in {'', 'identity'}:
                raise ValueError('Compressed source responses are not supported.')
            length = response.getheader('Content-Length')
            if length is not None and (not length.isdecimal() or int(length) > MAX_BYTES):
                raise ValueError('Source response exceeds its byte limit or has invalid length.')
            chunks, total = [], 0
            while True:
                if time.monotonic() > deadline:
                    raise ValueError('Source response exceeded its time limit.')
                chunk = response.read(min(65536, MAX_BYTES + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError('Source response exceeds its byte limit; partial sources are not accepted.')
                chunks.append(chunk)
            raw = b''.join(chunks)
            if length is not None and total != int(length):
                raise ValueError('Source response was incomplete; partial sources are not accepted.')
            content_type_header = response.getheader('Content-Type') or ''
            content_type = content_type_header.split(';')[0].strip().lower()
            charset = re.search(r'charset\s*=\s*["\']?([\w.-]+)', content_type_header, re.I)
            charset = charset.group(1) if charset else None
        finally:
            if response is not None:
                response.close()
            conn.close()
        if content_type == 'application/pdf':
            text, title = _extract_pdf_bytes(raw), ''
        elif content_type in {'text/html', 'application/xhtml+xml'}:
            extractor = _HTMLTextExtractor()
            if __package__:
                from .ingestion_worker import text_bytes
            else:
                from ingestion_worker import text_bytes
            extractor.feed(text_bytes(raw, charset))
            text, title = extractor.get_text(), extractor.title.strip()
        elif content_type in {'text/plain', 'text/markdown'}:
            # Loaded standalone only inside the constrained worker.
            if __package__:
                from .ingestion_worker import text_bytes
            else:
                from ingestion_worker import text_bytes
            text, title = text_bytes(raw, charset), ''
        else:
            raise ValueError('Unsupported source content type; use PDF, HTML or plain text.')
        if not text or len(text.strip()) < 20 or len(text) > 4_000_000:
            raise ValueError('Source has no readable text or exceeds its character limit.')
        return {'url': current_url, 'title': (title or _domain_name(current_url))[:200], 'text': text}
    raise ValueError('Too many source redirects.')


def _extract_pdf_bytes(data):
    if __package__:
        from .ingestion_worker import extract_pdf_bytes
    else:
        from ingestion_worker import extract_pdf_bytes
    return extract_pdf_bytes(data)
