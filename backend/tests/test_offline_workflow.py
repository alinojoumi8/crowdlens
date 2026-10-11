"""Real HTTP/persistence wiring with declared generation and graph substitutes."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import fitz
import pytest
import requests

TEXT = 'Alex states that the hearing was postponed until Friday.'
BACKEND = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('suffix', ['txt', 'pdf'])
def test_upload_to_revision_export_with_counted_scripted_stages(tmp_path, suffix):
    output = tmp_path / 'harness'
    log = tmp_path / 'server.log'
    with log.open('w') as stream:
        process = subprocess.Popen([sys.executable, str(BACKEND / 'scripts/smoke_ecc_browser.py'),
            '--synthetic', '--workflow', '--api-only', '--output-dir', str(output)],
            cwd=BACKEND.parent, stdout=stream, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 20
        base = None
        while time.monotonic() < deadline and process.poll() is None:
            for line in log.read_text().splitlines():
                if line.startswith('{"url":'):
                    base = json.loads(line)['url']
            if base: break
            time.sleep(.05)
        assert base, log.read_text()
        def post(path, data):
            response = requests.post(base+path, json=data, timeout=10)
            assert response.ok, (path, response.status_code, response.text, log.read_text())
            return response.json()['data']
        def get(path):
            response = requests.get(base+path, timeout=10)
            assert response.ok, (path, response.status_code, response.text)
            return response.json()['data']
        def poll(read, done):
            end = time.monotonic() + 10
            while time.monotonic() < end:
                value = read()
                if done(value): return value
                time.sleep(.05)
            pytest.fail(f'Workflow phase timed out: {value}\n{log.read_text()}')
        if suffix == 'pdf':
            with fitz.open() as pdf:
                pdf.new_page().insert_text((36, 36), TEXT)
                content = pdf.tobytes()
        else:
            content = TEXT.encode()
        filename = 'fictional-record.' + suffix
        requirement = 'Explore the fictional hearing record.'
        packet = dict(files=[dict(name=filename, sha256=hashlib.sha256(content).hexdigest())], requirement=requirement, urls=[])
        config = get('/api/execution/configuration')
        wid = post('/api/execution/authorize', {**config, 'request_key':'offline-'+suffix,
            'input_description':'Fictional offline integration', 'input_fingerprint':hashlib.sha256(json.dumps(packet,separators=(',',':')).encode()).hexdigest(),
            'max_requests':30, 'max_seconds':60, 'confirmed':True,
            'spend':dict(currency='USD', budget_usd='1', reserve_usd='0.1', input_usd_per_million='1', output_usd_per_million='2', price_reference='Fictional rates v1')})['workflow_id']
        response = requests.post(base+'/api/graph/ontology/generate',
            files={'files':(filename, content)}, data={'simulation_requirement':requirement,'workflow_id':wid}, timeout=10)
        assert response.ok, response.text
        project_id = response.json()['data']['project_id']
        post('/api/graph/build', {'project_id':project_id})
        project = poll(lambda:get('/api/graph/project/'+project_id), lambda p:p['status'] in ('graph_completed','failed'))
        assert project['status'] == 'graph_completed'
        stored_uploads = [p for p in (output/'projects'/project_id).rglob('*') if p.is_file() and p.suffix=='.'+suffix]
        assert any(p.read_bytes()==content for p in stored_uploads)
        simulation_id = post('/api/simulation/create', {'project_id':project_id})['simulation_id']
        assert get('/api/simulation/'+simulation_id+'/run-status')['runner_status']=='idle'
        post('/api/simulation/prepare', {'simulation_id':simulation_id, 'prediction_settings':{'report_mode':'legal_case','report_depth':'fast','memory_mode':'off','platform':'twitter'}})
        assert get('/api/simulation/'+simulation_id+'/config')['config']['report_mode']=='legal_case'
        post('/api/simulation/start', {'simulation_id':simulation_id})
        assert get('/api/simulation/'+simulation_id+'/run-status')['runner_status'] == 'completed'
        report_id = post('/api/report/generate', {'simulation_id':simulation_id, 'report_mode':'legal_case', 'report_depth':'fast','request_key':'root-'+suffix})['report_id']
        report = poll(lambda:get('/api/report/'+report_id), lambda r:r['status']=='needs_review')
        parent = output/'reports'/report_id
        hashes = lambda: {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in parent.iterdir() if p.is_file()}
        before = hashes()
        path = '/api/report/'+report_id+'/evidence-proposals'
        proposal_id = post(path, {'section_index':1,'request_key':'proposal-'+suffix})['proposal_id']
        proposal = poll(lambda:get(path+'/'+proposal_id), lambda p:p['state'] not in ('queued','running'))
        assert proposal['state']=='ready', (proposal, log.read_text())
        revision = post(path+'/'+proposal_id+'/accept', {'proposal_digest':proposal['proposal_digest']})
        assert revision['status']=='needs_review'
        assert post(path+'/'+proposal_id+'/accept', {'proposal_digest':proposal['proposal_digest']})['report_id']==revision['report_id']
        assert get('/api/report/'+revision['report_id'])['outline']==revision['outline']
        assert hashes()==before
        report_download = requests.get(base+'/api/report/'+revision['report_id']+'/download',timeout=10)
        assert report_download.ok and b'Friday' in report_download.content
        exported = requests.get(base+path+'/'+proposal_id+'/human-reviews/export',timeout=10)
        assert exported.ok
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            assert archive.testzip() is None
            assert any(name.endswith('.jsonl') for name in archive.namelist())
        status = get('/api/execution/'+wid)
        assert {'ontology','graph','preparation','simulation','report','proposal'} <= set(status['usage_by_stage'])
        assert status['spend']['reserved_micro_usd']==0
        assert status['spend']['estimated_micro_usd']==0  # Scripted receipts, not free real generation.
        assert status['admitted']>=6
        assert requests.get(base+'/__synthetic/evidence',timeout=10).json()['provider_calls']==0
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)
