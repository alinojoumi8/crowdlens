"""Exercise real HTTP/SQLite/Neo4j with scripted drafting and no inference.

Requires a new empty disposable Neo4j on a nondefault loopback port using the
synthetic password below. The caller owns creation and cleanup of that service.
"""
import argparse
import hashlib
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
sys.path[:0] = [str(BACKEND), str(BACKEND / "tests")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", required=True, action="store_true")
    parser.add_argument("--neo4j-uri", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    uri = urllib.parse.urlparse(args.neo4j_uri)
    if uri.scheme != "bolt" or uri.hostname not in {"127.0.0.1", "localhost"} or not uri.port or uri.port == 7687:
        parser.error("Use a new disposable Neo4j on a nondefault loopback port")
    output = args.output_dir.resolve()
    if output.exists() or not output.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        parser.error("Use a new output directory beneath the system temporary directory")
    output.mkdir()
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(args.neo4j_uri, auth=("neo4j", "crowdlens-synthetic-m2-password"))
    with driver.session() as session:
        if session.run("MATCH (n) RETURN count(n) AS count").single()["count"]:
            parser.error("Disposable Neo4j must be empty")
    # Provider HTTP is forbidden even on loopback; only harness HTTP is admitted.
    import requests
    import httpx
    original_request, original_send = requests.Session.request, httpx.Client.send
    def safe_url(url):
        parsed = urllib.parse.urlparse(str(url))
        if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.path.startswith(("/v1/", "/api/chat", "/api/generate", "/api/embed")):
            raise RuntimeError("Provider HTTP forbidden in release service verification")
    def request(self, method, url, **kwargs):
        safe_url(url)
        return original_request(self, method, url, **kwargs)
    def send(self, request, **kwargs):
        safe_url(request.url)
        return original_send(self, request, **kwargs)
    requests.Session.request, httpx.Client.send = request, send
    from app.config import Config
    Config.UPLOAD_FOLDER = str(output / "uploads")
    Config.EMBEDDING_AUTO_PULL = False
    for key in ("JEV_EVIDENCE_MODE", "JEV_INTERVIEW_MODE", "JEV_RERANK_MODE"):
        setattr(Config, key, "off")
    from app.models.project import ProjectManager
    from app.models.case import CaseManager
    from app.models.task import TaskManager
    from app.services.report_agent import ReportManager
    from app.services.simulation_manager import SimulationManager
    from app.services.proposal_store import ProposalStore
    from app.services.task_execution import TaskRuntime, OwnershipLost
    from app.storage.control_db import ControlDatabase
    from app.storage.neo4j_storage import Neo4jStorage
    from app.services.source_tracing import SourceIndex
    from app.utils.build_identity import runtime_identity
    from evidence_draft_samples import SCOPE, TEXT, sample_report
    from test_evidence_drafting import FakeLLM
    ProjectManager.PROJECTS_DIR = str(output / "projects")
    CaseManager.CASES_DIR = str(output / "cases")
    SimulationManager.SIMULATION_DATA_DIR = str(output / "simulations")
    ReportManager.REPORTS_DIR = ReportManager.FALLBACK_REPORTS_DIR = str(output / "reports")
    database = ControlDatabase(output / "control.db")
    for manager in (ProjectManager, CaseManager, TaskManager):
        manager.configure_repository(database)
    storage = Neo4jStorage.__new__(Neo4jStorage)
    storage._driver = driver
    rows = [
        {**SCOPE, "uuid": "one", "document_id": "doc", "data": TEXT, "page": 1, "origin": "source_document"},
        {**SCOPE, "uuid": "foreign", "case_version_id": "other_version", "document_id": "other_doc", "data": TEXT, "origin": "source_document"},
        {**SCOPE, "uuid": "generated", "document_id": "generated_doc", "data": TEXT, "origin": "agent_memory"},
    ]
    with driver.session() as session:
        for row in rows:
            session.run("CREATE (e:Episode) SET e = $row", row=row).consume()
        session.run("CREATE (:Graph {graph_id: 'release_fence'})").consume()
    assert {row["episode_id"] for row in SourceIndex(storage.get_source_chunks(**SCOPE), SCOPE).sources} == {"one"}
    # Real graph publication rejects a replaced attempt with the production fence.
    clock = [100.0]
    runtime = TaskRuntime(database, clock=lambda: clock[0])
    resource = [{"key": "graph:release_fence"}]
    old = runtime.admit({"task_id": "release_old", "status": "processing"}, resource)
    with old.bind():
        storage.set_ontology("release_fence", {"generation": 1})
    clock[0] = 131.0
    runtime.reconcile()
    current = runtime.admit({"task_id": "release_current", "status": "processing"}, resource)
    with current.bind():
        storage.set_ontology("release_fence", {"generation": 2})
    try:
        with old.bind():
            storage.set_ontology("release_fence", {"generation": 99})
    except OwnershipLost:
        pass
    else:
        raise AssertionError("Stale attempt published to Neo4j")
    assert storage.get_ontology("release_fence") == {"generation": 2}
    runtime.update(current, {"status": "completed"})
    runtime.close()
    ReportManager.save_report(sample_report())
    parent = Path(ReportManager.REPORTS_DIR) / "report_root"
    def parent_hashes():
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in parent.iterdir() if p.is_file()}
    before = parent_hashes()
    from flask import Flask
    from app.api import report_bp
    from werkzeug.serving import make_server
    app = Flask(__name__)
    app.register_blueprint(report_bp, url_prefix="/api/report")
    store = ProposalStore(ReportManager.REPORTS_DIR)
    model_calls = []
    def factory(identifier):
        llm = FakeLLM(store, identifier)
        model_calls.append(llm.calls)
        return llm
    app.extensions.update(neo4j_storage=storage, evidence_proposal_store=store,
                          evidence_llm_factory=factory, evidence_embedder_factory=lambda: None)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:" + str(server.server_port)
    def call(path, payload=None):
        req = urllib.request.Request(base + path, data=None if payload is None else json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            return response.code, json.load(response)
    try:
        path = "/api/report/report_root/evidence-proposals"
        status, created = call(path, {"section_index": 1, "request_key": "synthetic-ecc-release"})
        assert status == 202
        identifier = created["data"]["proposal_id"]
        for _ in range(200):
            _, response = call(path + "/" + identifier)
            if response["data"]["state"] not in {"queued", "running"}:
                break
            time.sleep(.025)
        record = response["data"]
        assert record["state"] == "ready"
        assert call(path + "/" + identifier + "/accept", {"proposal_digest": "stale"})[0] == 409
        payload = {"proposal_digest": record["proposal_digest"]}
        status, accepted = call(path + "/" + identifier + "/accept", payload)
        assert status == 200
        revision = accepted["data"]
        rid = revision["report_id"]
        assert call(path + "/" + identifier + "/accept", payload)[1]["data"]["report_id"] == rid
        assert call("/api/report/" + rid + "/section/1/regenerate", {})[0] == 409
        assert call("/api/report/" + rid + "/resume", {})[0] == 409
        assert call("/api/report/" + rid)[1]["data"]["status"] == "needs_review"
        assert revision["status"] == "needs_review" and parent_hashes() == before
        assert revision["outline"]["sections"][1] == sample_report().to_dict()["outline"]["sections"][1]
        result = {"status": "passed", "source": runtime_identity(), "neo4j_uri": args.neo4j_uri,
                  "http_url": base, "proposal_id": identifier, "revision_id": rid,
                  "scope_and_origin_isolation": True, "stale_neo4j_write_rejected": True,
                  "neo4j_preserved_generation": 2, "parent_hashes": before, "parent_unchanged": True,
                  "acceptance_retry_same_revision": True, "reopened_status": "needs_review",
                  "scripted_model_calls": sum(map(len, model_calls)), "real_model_calls": 0,
                  "substitutions": ["scripted drafting model", "semantic embeddings disabled"],
                  "full_upload_graph_simulation_workflow": "not run"}
        output.joinpath("result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    finally:
        server.shutdown()
        server.server_close()
        driver.close()
        requests.Session.request, httpx.Client.send = original_request, original_send


if __name__ == "__main__":
    main()
