"""Hostile sources are rejected offline before any model work."""
import io
import json
import time
from pathlib import Path

import fitz
import pytest

from app.utils.file_parser import FileParser
from app.utils import url_fetcher as urls
from test_url_fetcher import _FakeResponse, _FakeConnection


def test_binary_file_cannot_masquerade_as_text(tmp_path):
    path = tmp_path / 'fake.txt'
    path.write_bytes(b'MZ\x00\x01' + b'executable' * 20)
    with pytest.raises(ValueError):
        FileParser.extract_text(str(path))


def test_pdf_with_non_pdf_prefix_is_rejected(tmp_path):
    path = tmp_path / 'polyglot.pdf'
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((30, 30), 'Fictional readable evidence for signature validation.')
        raw = doc.tobytes()
    path.write_bytes(b'<script>alert(1)</script>\n' + raw)
    with pytest.raises(ValueError):
        FileParser.extract_text(str(path))


def test_url_response_limit_rejects_instead_of_accepting_partial_source(monkeypatch):
    monkeypatch.setattr(urls, 'MAX_BYTES', 32)
    monkeypatch.setattr(urls, '_assert_public_host', lambda host: ('93.184.216.34',))
    response = _FakeResponse('https://public.example/', 200, {'Content-Type': 'text/plain'}, b'x' * 100)
    monkeypatch.setattr(urls, '_open_connection', lambda *a: _FakeConnection(response))
    with pytest.raises(ValueError):
        urls._fetch_url(response.url)


def test_xml_tool_envelope_requires_allowlisted_name_and_object_arguments():
    from app.services.report_agent import ReportAgent
    agent = object.__new__(ReportAgent)
    for call in [dict(name='fetch_url', parameters={'url': 'http://169.254.169.254/'}),
                 dict(name='quick_search', parameters=['not', 'an', 'object']), ['quick_search']]:
        assert agent._parse_tool_calls('<tool_call>' + json.dumps(call) + '</tool_call>') == []


@pytest.mark.parametrize('value', ['file:///etc/passwd', 'gopher://example.com', 'https://a@b.com/',
    'http://example.com:11434/', 'https://example.com:80/', 'http://example.com/\r\nInjected: x',
    'http://example.com\\@127.0.0.1/', 'https://[::1%25lo]/', 'http://example.com:bad'])
def test_url_syntax_rejected_before_connection(value):
    with pytest.raises(ValueError):
        urls.fetch_url(value)


@pytest.mark.parametrize('ip', ['127.0.0.1', '10.2.3.4', '169.254.169.254', '100.100.100.200',
    '0.0.0.0', '224.0.0.1', '::1', 'fe80::1', 'fc00::1', '::ffff:127.0.0.1',
    '64:ff9b::a9fe:a9fe', '2002:7f00:1::'])
def test_dns_private_metadata_shared_and_translated_addresses_rejected(monkeypatch, ip):
    monkeypatch.setattr(urls.socket, 'getaddrinfo', lambda *a, **kw: [(0, 0, 0, '', (ip, 0))])
    with pytest.raises(ValueError):
        urls._assert_public_host('attacker.example')


def test_mixed_and_empty_dns_answers_fail_closed(monkeypatch):
    for ips in [[], ['93.184.216.34', '127.0.0.1']]:
        monkeypatch.setattr(urls.socket, 'getaddrinfo', lambda *a, **kw: [(0, 0, 0, '', (ip, 0)) for ip in ips])
        with pytest.raises(ValueError):
            urls._assert_public_host('attacker.example')


def test_connection_pins_ip_with_original_tls_hostname_and_ignores_proxy(monkeypatch):
    calls = []
    class Socket:
        def getpeername(self):
            return ('93.184.216.34', 443)
    class Connection:
        def __init__(self, host, port, **kwargs):
            calls.append((host, port, kwargs))
        def connect(self):
            self.sock = self._create_connection(('rebind.example', 443), 20)
        def close(self):
            pass
    monkeypatch.setenv('HTTPS_PROXY', 'http://127.0.0.1:11434')
    monkeypatch.setattr(urls.http.client, 'HTTPSConnection', Connection)
    monkeypatch.setattr(urls.socket, 'create_connection', lambda address, *a: calls.append(address) or Socket())
    parsed, host = urls._validated_url('https://rebind.example/path')
    urls._open_connection(parsed, host, '93.184.216.34')
    assert calls[0][0] == 'rebind.example' and calls[0][2]['context'].check_hostname
    assert calls[1] == ('93.184.216.34', 443)


@pytest.mark.parametrize('headers,body', [
    ({'Content-Length': '999999999'}, b''),
    ({'Content-Length': '90'}, b'short'),
    ({'Content-Length': '-1'}, b'x' * 25),
    ({'Content-Encoding': 'gzip'}, b'x' * 25),
    ({'Content-Type': 'application/octet-stream'}, b'MZ' + b'x' * 25),
    ({'Content-Type': 'image/svg+xml'}, b'<svg onload="alert(1)"/>'),
])
def test_hostile_url_responses_close_connection_and_reject(monkeypatch, headers, body):
    response = _FakeResponse('https://public.example/', 200, headers, body)
    conn = _FakeConnection(response)
    monkeypatch.setattr(urls, '_assert_public_host', lambda host: ('93.184.216.34',))
    monkeypatch.setattr(urls, '_open_connection', lambda *a: conn)
    with pytest.raises(ValueError):
        urls._fetch_url(response.url)
    assert conn.closed


def test_redirect_loop_is_bounded_and_each_connection_closed(monkeypatch):
    calls = []
    def connect(*args):
        conn = _FakeConnection(_FakeResponse('', 302, {'Location': '/again'}))
        calls.append(conn)
        return conn
    monkeypatch.setattr(urls, '_assert_public_host', lambda host: ('93.184.216.34',))
    monkeypatch.setattr(urls, '_open_connection', connect)
    with pytest.raises(ValueError, match='redirect'):
        urls._fetch_url('https://public.example/')
    assert len(calls) == urls.MAX_REDIRECTS + 1 and all(c.closed for c in calls)


def test_pdf_page_and_text_limits_reject_whole_source(tmp_path, monkeypatch):
    from app.utils import ingestion_worker as worker
    path = tmp_path / 'large.pdf'
    with fitz.open() as doc:
        for _ in range(2):
            doc.new_page().insert_text((30, 30), 'Fictional text evidence to keep complete.')
        doc.save(path)
    monkeypatch.setattr(worker, 'MAX_PDF_PAGES', 1)
    with pytest.raises(ValueError, match='over-limit'):
        worker.extract_file(path)
    monkeypatch.setattr(worker, 'MAX_PDF_PAGES', 10)
    monkeypatch.setattr(worker, 'MAX_TEXT_CHARS', 5)
    with pytest.raises(ValueError, match='character limit'):
        worker.extract_file(path)


def test_real_worker_rejects_malformed_pdf_and_preserves_unicode(tmp_path):
    path = tmp_path / 'broken.pdf'; path.write_bytes(b'%PDF-1.7\nmalformed')
    with pytest.raises(ValueError):
        FileParser.extract_text(str(path))
    path = tmp_path / 'unicode.md'; path.write_text('Fictional evidence — café 中文', encoding='utf-16')
    assert FileParser.extract_text(str(path)) == 'Fictional evidence — café 中文'


def test_worker_does_not_inherit_credentials_or_proxy(tmp_path, monkeypatch):
    from app.utils import ingestion
    monkeypatch.setattr(ingestion, '__file__', str(tmp_path / 'ingestion.py'))
    (tmp_path / 'ingestion_worker.py').write_text("import json,os; print(json.dumps({'result':dict(os.environ)}))")
    monkeypatch.setenv('LLM_API_KEY', 'private-fixture-secret')
    monkeypatch.setenv('HTTPS_PROXY', 'http://private-fixture-proxy')
    env = ingestion.run_ingestion('file', 'unused')
    assert 'LLM_API_KEY' not in env and 'HTTPS_PROXY' not in env and 'PYTHONPATH' not in env


def test_worker_timeout_kills_descendant_process(tmp_path, monkeypatch):
    import os
    from app.utils import ingestion
    monkeypatch.setattr(ingestion, '__file__', str(tmp_path / 'ingestion.py'))
    monkeypatch.setattr(ingestion, 'WORKER_SECONDS', 0.5)
    script = "import subprocess,sys,time,json,pathlib\nmode,path=json.load(sys.stdin)\np=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\npathlib.Path(path).write_text(str(p.pid))\ntime.sleep(60)\n"
    (tmp_path / 'ingestion_worker.py').write_text(script)
    pidfile = tmp_path / 'pid'
    started = time.monotonic()
    with pytest.raises(ValueError, match='timed out'):
        ingestion.run_ingestion('file', str(pidfile))
    assert time.monotonic() - started < 5
    pid = int(pidfile.read_text())
    for _ in range(100):
        status = Path(f'/proc/{pid}/stat')
        if not status.exists() or status.read_text().split()[2] == 'Z':
            break
        time.sleep(0.01)
    else:
        pytest.fail('Parser descendant survived the timeout')


def test_upload_stream_limit_removes_rejected_original(tmp_path, monkeypatch):
    from app.models.project import ProjectManager
    from app.utils import ingestion_limits
    from werkzeug.datastructures import FileStorage
    monkeypatch.setattr(ProjectManager, '_repository', None)
    monkeypatch.setattr(ProjectManager, 'PROJECTS_DIR', str(tmp_path / 'projects'))
    monkeypatch.setattr(ingestion_limits, 'MAX_FILE_BYTES', 8)
    project = ProjectManager.create_project('fictional')
    with pytest.raises(ValueError, match='limit'):
        ProjectManager.save_file_to_project(project.project_id, FileStorage(stream=io.BytesIO(b'X'*9)), 'test.txt')
    assert not list(Path(ProjectManager._get_project_files_dir(project.project_id)).iterdir())


@pytest.mark.parametrize('existing_case', [False, True])
def test_upload_endpoint_rejects_mixed_batch_without_model_or_version(tmp_path, monkeypatch, existing_case):
    from flask import Flask
    from app.api import graph_bp
    from app.models.project import ProjectManager
    from app.models.case import CaseManager
    from app.api import graph
    monkeypatch.setattr(ProjectManager, '_repository', None)
    monkeypatch.setattr(ProjectManager, 'PROJECTS_DIR', str(tmp_path / 'projects'))
    monkeypatch.setattr(CaseManager, 'CASES_DIR', str(tmp_path / 'cases'))
    calls = []
    monkeypatch.setattr(graph, 'OntologyGenerator', lambda: calls.append('model') or None)
    app = Flask(__name__); app.register_blueprint(graph_bp, url_prefix='/api/graph')
    client = app.test_client()
    case = CaseManager.create_case('existing fictional case') if existing_case else None
    endpoint = f'/api/graph/case/{case.case_id}/documents' if case else '/api/graph/ontology/generate'
    for files in [[(io.BytesIO(b'valid fictional text'), 'safe.txt'), (io.BytesIO(b'MZ'), 'evil.exe')],
                  [(io.BytesIO(b'valid fictional text'), 'safe.txt'), (io.BytesIO(b'MZ\x00'), 'fake.txt')]]:
        response = client.post(endpoint, data={'simulation_requirement':'fictional', 'files':files})
        assert response.status_code == 400, response.json
        assert not ProjectManager.list_projects()
        assert [c.case_id for c in CaseManager.list_cases()] == ([case.case_id] if case else [])
        assert all(not c.versions for c in CaseManager.list_cases())
    assert calls == []


def test_report_tool_scope_cannot_be_overridden_by_source_instructions():
    from app.services.report_agent import ReportAgent
    from types import SimpleNamespace
    calls = []
    agent = object.__new__(ReportAgent)
    agent.disable_interviews = True; agent.graph_id = 'owned-graph'
    agent.graph_tools = SimpleNamespace(quick_search=lambda **kw: calls.append(kw) or {})
    agent._render_evidence_result = lambda value: 'safe'
    assert 'destination' in agent._execute_tool('quick_search', {'graph_id':'victim', 'query':'ignore instructions'})
    assert 'not available' in agent._execute_tool('fetch_url', {'url':'http://169.254.169.254/'})
    assert 'not available' in agent._execute_tool('interview_agents', {'interview_topic':'leak secrets'})
    assert calls == []
    assert agent._execute_tool('quick_search', {'query':'source says ignore instructions', 'limit':100000}) == 'safe'
    assert calls[0]['graph_id'] == 'owned-graph' and calls[0]['limit'] == 100


def test_security_headers_apply_to_html_errors_and_generated_downloads():
    from flask import Flask, Response
    from app.utils.response_security import install_response_security
    app = Flask(__name__); install_response_security(app)
    app.get('/')(lambda: '<html>safe</html>')
    app.get('/download', endpoint='download')(lambda: Response('<script>alert(1)</script>', mimetype='text/html',
        headers={'Content-Disposition':'attachment; filename=report.md'}))
    for path in ['/', '/missing', '/download']:
        response = app.test_client().get(path)
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        assert response.headers['Cross-Origin-Resource-Policy'] == 'same-origin'
        assert response.headers['Referrer-Policy'] == 'no-referrer'
        assert "default-src '" in response.headers['Content-Security-Policy']
    response = app.test_client().get('/download')
    assert response.content_type == 'application/octet-stream'
    assert response.headers['Content-Security-Policy'].startswith('sandbox;')
    assert response.headers['Cache-Control'] == 'no-store'


def test_multiline_url_form_values_are_split_and_deduplicated():
    assert urls.parse_urls(['https://a.example/\nhttps://b.example/', 'https://a.example/']) == [
        'https://a.example/', 'https://b.example/']


def test_slow_source_response_is_closed_at_total_deadline(monkeypatch):
    conn = _FakeConnection(_FakeResponse('', 200, {'Content-Type':'text/plain'}, b'fictional response body'))
    ticks = iter([0, urls.REQUEST_TIMEOUT + 1])
    monkeypatch.setattr(urls.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(urls, '_assert_public_host', lambda host: ('93.184.216.34',))
    monkeypatch.setattr(urls, '_open_connection', lambda *a: conn)
    with pytest.raises(ValueError, match='time limit'):
        urls._fetch_url('https://public.example/')
    assert conn.closed


def test_encrypted_pdf_is_rejected_by_real_worker(tmp_path):
    path = tmp_path / 'protected.pdf'
    with fitz.open() as doc:
        doc.new_page().insert_text((30, 30), 'fictional private source')
        doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw='fixture', owner_pw='fixture')
    with pytest.raises(ValueError, match='Encrypted'):
        FileParser.extract_text(str(path))


def test_api_keeps_payload_limit_as_413():
    from flask import Flask
    from app.api import graph_bp
    app = Flask(__name__); app.config['MAX_CONTENT_LENGTH'] = 16
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    response = app.test_client().post('/api/graph/ontology/generate', data={'simulation_requirement':'x' * 100})
    assert response.status_code == 413


def test_real_worker_blocks_loopback_without_contacting_service():
    import http.server
    import threading
    hits = []
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200); self.end_headers(); self.wfile.write(b'must not be contacted')
        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with pytest.raises(ValueError):
            urls.fetch_url(f'http://127.0.0.1:{server.server_port}/metadata')
        assert hits == []
        with pytest.raises(ValueError):
            urls.fetch_url('http://127.0.0.1/metadata')
        assert hits == []
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_html_declared_windows_encoding_preserves_source(monkeypatch):
    body = '<html><p>Fictional café testimony must remain readable and complete.</p></html>'.encode('cp1252')
    conn = _FakeConnection(_FakeResponse('', 200, {'Content-Type':'text/html; charset=windows-1252'}, body))
    monkeypatch.setattr(urls, '_assert_public_host', lambda host: ('93.184.216.34',))
    monkeypatch.setattr(urls, '_open_connection', lambda *a: conn)
    assert 'café testimony' in urls._fetch_url('https://public.example/')['text']


def test_tls_uses_explicit_available_ca_bundle(monkeypatch):
    import certifi
    original = urls.ssl.create_default_context
    captured = []
    def context(**kwargs):
        captured.append(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(urls.ssl, 'create_default_context', context)
    class Connection:
        def __init__(self, *a, **kw):
            pass
        def connect(self):
            raise ValueError('connection intentionally stopped')
        def close(self):
            pass
    monkeypatch.setattr(urls.http.client, 'HTTPSConnection', Connection)
    parsed, host = urls._validated_url('https://public.example/')
    with pytest.raises(ValueError):
        urls._open_connection(parsed, host, '93.184.216.34')
    assert captured == [{'cafile':certifi.where()}]
    assert original(cafile=certifi.where()).cert_store_stats()['x509_ca'] > 0


def test_oversized_scan_is_rejected_before_starting_any_ocr(tmp_path, monkeypatch):
    from app.utils import ingestion_worker as worker
    from PIL import Image
    image = io.BytesIO(); Image.new('RGB', (10, 10), 'white').save(image, format='PNG')
    with fitz.open() as doc:
        for _ in range(2):
            page = doc.new_page(); page.insert_image(page.rect, stream=image.getvalue())
        data = doc.tobytes()
    monkeypatch.setattr(worker.subprocess, 'run', lambda *a, **kw: pytest.fail('OCR started before preflight'))
    with pytest.raises(ValueError, match='scanned PDF page'):
        worker.extract_pdf_bytes(data)


@pytest.mark.parametrize('batch', [False, True])
def test_generated_cypher_label_rejected_before_any_write_or_embedding(batch):
    from app.storage.neo4j_storage import Neo4jStorage
    storage = object.__new__(Neo4jStorage)
    extraction = {'entities':[{'name':'fictional', 'type':'Entity` MATCH (other) DETACH DELETE other //'}], 'relations':[]}
    with pytest.raises(ValueError, match='label'):
        if batch:
            storage._write_extractions_batch('g', ['fictional'], [extraction])
        else:
            storage._write_extraction('g', 'fictional', extraction)


def test_generated_label_lookup_uses_parameter_instead_of_cypher_source():
    from app.storage.neo4j_storage import Neo4jStorage
    from types import SimpleNamespace
    calls = []
    class Session:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def execute_read(self, callback):
            return callback(self)
        def run(self, query, **params):
            calls.append((query, params)); return []
    storage = object.__new__(Neo4jStorage); storage._driver = SimpleNamespace(session=Session)
    payload = 'Entity` MATCH (other) RETURN other //'
    assert storage.get_nodes_by_label('owned', payload) == []
    assert payload not in calls[0][0]
    assert calls[0][1]['label'] == payload and calls[0][1]['gid'] == 'owned'


@pytest.mark.parametrize('seed_invalid_cache', [False, True])
def test_invalid_generated_labels_never_enter_cache_and_old_entries_can_recover(tmp_path, seed_invalid_cache):
    from app.storage.neo4j_storage import Neo4jStorage, _validate_entity_label
    from app.storage.extraction_cache import ExtractionCache
    class NER:
        calls = 0
        def extract_batch(self, chunks, ontology):
            self.calls += 1
            return [{'entities':[{'name':'fictional', 'type':'Government Agency' if self.calls == 1 else 'Party'}], 'relations':[]}]
    storage = object.__new__(Neo4jStorage)
    storage._ner = NER(); storage._extraction_cache = ExtractionCache(tmp_path / 'cache')
    storage._assert_embedding_compatible = lambda graph_id: None
    storage.get_ontology = lambda graph_id: {'entity_types':['Party']}
    def write(graph, chunks, extractions, **kwargs):
        for item in extractions:
            for entity in item['entities']:
                _validate_entity_label(entity['type'])
        return ['episode']
    storage._write_extractions_batch = write
    cache = storage._extraction_cache
    key = ('file', cache.hash_text('fictional'), cache.hash_ontology(storage.get_ontology('g')))
    bad = {'entities':[{'name':'fictional', 'type':'Government Agency'}], 'relations':[]}
    if seed_invalid_cache:
        cache.set(*key, bad)
    with pytest.raises(ValueError, match='label'):
        storage.add_text_batch('g', ['fictional'], cache_context={'file_hash':'file'})
    assert storage._ner.calls == 1
    assert cache.get(*key) == (bad if seed_invalid_cache else None)
    assert storage.add_text_batch('g', ['fictional'], cache_context={'file_hash':'file'}) == ['episode']
    assert storage.add_text_batch('g', ['fictional'], cache_context={'file_hash':'file'}) == ['episode']
    assert storage._ner.calls == 2 and cache.get(*key)['entities'][0]['type'] == 'Party'
