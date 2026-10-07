"""Disposable HTTP/Neo4j integration and a bounded local-only ingestion attempt."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND/'tests'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', required=True, action='store_true')
    parser.add_argument('--neo4j-uri', required=True)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    if urllib.parse.urlparse(args.neo4j_uri).hostname not in {'127.0.0.1', 'localhost'}:
        parser.error('Use a disposable loopback Neo4j instance, never the existing database.')
    output = args.output_dir.resolve()
    if not output.is_relative_to(Path(tempfile.gettempdir()).resolve()) or output.exists():
        parser.error('Use a new directory beneath the system temporary directory.')
    output.mkdir()
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(args.neo4j_uri, auth=('neo4j', 'crowdlens-synthetic-m2-password'))
    # Refuse a database containing anything, even other synthetic artifacts.
    with driver.session() as session:
        if session.run('MATCH (n) RETURN count(n) AS count').single()['count']:
            parser.error('Neo4j must be new and empty.')
    from app.config import Config
    from app.models.project import ProjectManager
    from app.models.case import CaseManager
    from app.models.task import TaskManager
    from app.services.report_agent import ReportManager
    from app.services.simulation_manager import SimulationManager
    from app.services.proposal_store import ProposalStore
    from app.storage.control_db import ControlDatabase
    from app.storage.neo4j_storage import Neo4jStorage
    from app.services.source_tracing import SourceIndex
    from evidence_draft_samples import SCOPE, TEXT, sample_report
    from test_evidence_drafting import FakeLLM
    Config.UPLOAD_FOLDER = str(output/'uploads')
    Config.LLM_API_KEY = 'synthetic-local-only'
    Config.LLM_DEFAULT_PROVIDER = 'ollama'
    Config.LLM_BASE_URL = 'http://127.0.0.1:11434/v1'
    Config.LLM_MODEL_NAME = 'qwen2.5:3b'
    for key in ['JEV_EVIDENCE_MODE', 'JEV_INTERVIEW_MODE', 'JEV_RERANK_MODE']:
        setattr(Config, key, 'off')
    ProjectManager.PROJECTS_DIR = str(output/'projects')
    CaseManager.CASES_DIR = str(output/'cases')
    SimulationManager.SIMULATION_DATA_DIR = str(output/'simulations')
    ReportManager.REPORTS_DIR = ReportManager.FALLBACK_REPORTS_DIR = str(output/'reports')
    db = ControlDatabase(output/'control.db')
    for manager in [ProjectManager, CaseManager, TaskManager]: manager.configure_repository(db)
    # Protect against unintended hosted inference or arbitrary ingestion requests.
    import requests
    import httpx
    original_requests, original_send = requests.Session.request, httpx.Client.send
    inference_requests = []
    def local_requests(self, method, url, **kw):
        if urllib.parse.urlparse(url).hostname not in {'127.0.0.1','localhost'}:
            raise RuntimeError('Non-loopback HTTP is forbidden in the synthetic audit')
        if urllib.parse.urlparse(url).path in {"/api/chat", "/v1/chat/completions"}:
            if inference_requests:
                raise RuntimeError("Synthetic audit inference request cap reached")
            inference_requests.append(urllib.parse.urlparse(url).path)
            kw["timeout"] = 6
        return original_requests(self, method, url, **kw)
    def local_send(self, request, **kw):
        if request.url.host not in {'127.0.0.1','localhost'}:
            raise RuntimeError('Hosted inference is forbidden in the synthetic audit')
        if request.url.path in {'/api/chat', '/v1/chat/completions'}:
            if inference_requests:
                raise RuntimeError('Synthetic audit inference request cap reached')
            inference_requests.append(request.url.path)
            request.extensions['timeout'] = {name: 6 for name in ['connect', 'read', 'write', 'pool']}
        return original_send(self, request, **kw)
    requests.Session.request, httpx.Client.send = local_requests, local_send
    storage = Neo4jStorage.__new__(Neo4jStorage); storage._driver = driver
    rows = [{**SCOPE, 'uuid':'one','document_id':'doc','data':TEXT,'page':1,'origin':'source_document'},
            {**SCOPE,'uuid':'foreign','case_version_id':'foreign_version','document_id':'foreign_doc','data':'Synthetic unrelated material','page':1},
            {**SCOPE,'uuid':'generated','document_id':'generated_doc','data':'Synthetic memory assertion','page':1,'origin':'agent_memory'}]
    with driver.session() as session:
        for row in rows: session.run('CREATE (e:Episode) SET e = $row', row=row).consume()
    assert {s['episode_id'] for s in SourceIndex(storage.get_source_chunks(**SCOPE),SCOPE).sources} == {'one'}
    ReportManager.save_report(sample_report())
    parent = Path(ReportManager.REPORTS_DIR)/'report_root'
    digest = lambda: {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in parent.iterdir() if p.is_file()}
    before = digest()
    from flask import Flask
    from app.api import report_bp, graph_bp
    from werkzeug.serving import make_server
    app = Flask(__name__)
    app.register_blueprint(report_bp,url_prefix='/api/report')
    app.register_blueprint(graph_bp,url_prefix='/api/graph')
    store = ProposalStore(ReportManager.REPORTS_DIR)
    app.extensions.update(neo4j_storage=storage,evidence_proposal_store=store,
        evidence_llm_factory=lambda identifier:FakeLLM(store,identifier),evidence_embedder_factory=lambda:None)
    server = make_server('127.0.0.1',0,app,threaded=True)
    thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base = 'http://127.0.0.1:'+str(server.server_port)
    def call(path,data=None):
        req=urllib.request.Request(base+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=10) as response: return response.status,json.load(response)
        except urllib.error.HTTPError as response: return response.code,json.load(response)
    try:
        url='/api/report/report_root/evidence-proposals'
        status,created=call(url,{'section_index':1,'request_key':'synthetic-m2'})
        assert status == 202
        identifier=created['data']['proposal_id']
        for _ in range(200):
            _,response=call(url+'/'+identifier)
            if response['data']['state'] not in {'queued','running'}:break
            time.sleep(.025)
        record=response['data']; assert record['state']=='ready'
        assert call(url+'/'+identifier+'/accept',{'proposal_digest':'stale'})[0]==409
        payload={'proposal_digest':record['proposal_digest']}
        status,accepted=call(url+'/'+identifier+'/accept',payload);assert status==200
        revision=accepted['data']; rid=revision['report_id']
        assert call(url+'/'+identifier+'/accept',payload)[1]['data']['report_id']==rid
        assert call('/api/report/'+rid+'/section/1/regenerate',{})[0]==409
        assert call('/api/report/'+rid+'/resume',{})[0]==409
        assert revision['status']=='needs_review' and digest()==before
        assert revision['outline']['sections'][1]==sample_report().to_dict()['outline']['sections'][1]
        result={'integration':{'status':'passed','graph_service':'disposable Neo4j 5.18','neo4j_uri':args.neo4j_uri,
            'http_port':server.server_port,'database':'disposable SQLite WAL','substitutions':['deterministic drafting LLM','semantic embedding disabled'],
            'report_id':'report_root','proposal_id':identifier,'revision_id':rid,'creation_requests':1,'acceptance_requests':3,
            'parent_unchanged':True,'unselected_section_unchanged':True,'revision_status':revision['status'],'wrong_version_and_generated_source_excluded':True}}
        # One actual local ingestion request. Missing generation models must remain blockers.
        Config.LLM_MODEL_NAME = 'qwen2.5:3b'
        import logging
        logging.getLogger('openai').setLevel(logging.ERROR)
        with app.test_client() as client:
            ingestion=client.post('/api/graph/ontology/generate',data={
                'files':(io.BytesIO(b'Alex states that the synthetic hearing was postponed until Friday.'),'synthetic.txt'),
                'simulation_requirement':'Explore the synthetic hearing record.','project_name':'Synthetic milestone2'},content_type='multipart/form-data')
        ingestion_data = ingestion.get_json() or {}
        failure = ingestion_data.get('error', '')
        missing_model = '404' in failure and 'model' in failure.lower()
        result['full_workflow']={'status':'blocked' if ingestion.status_code!=200 else 'incomplete',
            'attempted_stage':'upload/ontology','http_status':ingestion.status_code,'model':Config.LLM_MODEL_NAME,
            'provider':'loopback Ollama','hosted_calls':0,'inference_requests':len(inference_requests),
            'request_timeout_seconds':6,'request_cap':1,'missing_model_response_confirmed':missing_model,'project_ids':[p.project_id for p in ProjectManager.list_projects()],
            'reason':'Required local generation model unavailable; no model was pulled and no provider substituted.' if missing_model else ('Ingestion failed before completion; unavailable local model also blocks further stages.' if ingestion.status_code!=200 else 'Only ingestion ran; later stages have not been verified.'),
            'failure_class': (ingestion_data.get('traceback','').splitlines()[-1].split(':')[0] if ingestion_data.get('traceback') else None)}
        from app.utils.build_identity import runtime_identity
        result['source']=runtime_identity()
        (output/'result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
    finally:
        server.shutdown();server.server_close();driver.close()


if __name__=='__main__': main()
