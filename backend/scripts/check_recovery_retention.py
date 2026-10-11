"""Verify outages, retry identity and scoped deletion in an owned Neo4j only.

Uses a cached immutable image, a new volume and a nondefault loopback port.
Embeddings and text extraction are scripted; no provider HTTP is permitted.
Stops and restarts only the container this script creates, then removes it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import uuid

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', required=True, action='store_true')
    parser.add_argument('--image', required=True)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() or not output.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        parser.error('Use a new directory beneath the system temporary directory')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', args.image):
        parser.error('Use an immutable cached Neo4j image ID')
    output.mkdir()
    import requests
    import httpx
    def no_http(*args, **kwargs):
        raise AssertionError('Provider HTTP is forbidden in this rehearsal')
    requests.Session.request = httpx.Client.send = httpx.AsyncClient.send = no_http
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable
    from app.storage.neo4j_storage import Neo4jStorage
    from app.services.graph_memory_updater import AgentActivity, GraphMemoryUpdater
    from app.utils.build_identity import runtime_identity
    name = 'crowdlens-recovery-' + uuid.uuid4().hex[:12]
    volume = name + '-data'
    created = []
    driver = None
    receipt = {'status': 'running', 'image': args.image, 'source': runtime_identity(),
               'provider_calls': 0, 'substitutes': ['embedding vectors', 'text extraction'],
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'commands': [], 'containers': [name], 'volumes': [volume],
               'timing_scope': 'Driver transaction retry disabled, 1s connect/2s acquisition, storage backoff 0.05s; not production timing evidence'}
    def save():
        (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def run(label, argv, check=True, timeout=90):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        (output / (label + '.log')).write_text(result.stdout + result.stderr)
        receipt['commands'].append({'label': label, 'exit_code': result.returncode, 'argv': argv})
        save()
        if check and result.returncode:
            raise RuntimeError(label + ' failed; see owned output log')
        return result.stdout.strip()
    def ready():
        deadline = time.monotonic() + 60
        while True:
            try:
                driver.verify_connectivity()
                return
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.5)
    def graph_snapshot(graph):
        with driver.session() as session:
            nodes = [dict(row) for row in session.run('MATCH (n {graph_id:$id}) RETURN labels(n) AS labels, properties(n) AS props ORDER BY n.fixture_id, n.uuid', id=graph)]
            edges = [dict(row) for row in session.run('MATCH (a {graph_id:$id})-[r]->(b {graph_id:$id}) RETURN a.fixture_id AS a, b.fixture_id AS b, type(r) AS type, properties(r) AS props ORDER BY a,b,type', id=graph)]
        return {'nodes': nodes, 'edges': edges}
    def memory_count():
        with driver.session() as session:
            return session.run('MATCH (m:AgentMemory {graph_id:"graph_selected"}) RETURN count(m) AS count').single()['count']
    try:
        assert run('image', ['docker', 'image', 'inspect', '--format', '{{.Id}}', args.image]) == args.image
        run('create-volume', ['docker', 'volume', 'create', volume]); created.append('volume')
        with socket.socket() as port_socket:
            port_socket.bind(('127.0.0.1', 0))
            port = port_socket.getsockname()[1]
        created.append('container')
        run('start', ['docker', 'run', '--detach', '--pull', 'never', '--name', name,
            '--memory', '2g', '--cpus', '2', '--publish', f'127.0.0.1:{port}:7687',
            '--mount', f'type=volume,source={volume},target=/data', '--tmpfs', '/logs:rw,size=128m',
            '--env', 'NEO4J_AUTH=neo4j/crowdlens-synthetic-recovery-password',
            '--env', 'NEO4J_server_memory_heap_initial__size=256m',
            '--env', 'NEO4J_server_memory_heap_max__size=512m',
            '--env', 'NEO4J_server_memory_pagecache_size=256m', args.image])
        driver = GraphDatabase.driver(f'bolt://127.0.0.1:{port}',
            auth=('neo4j', 'crowdlens-synthetic-recovery-password'),
            connection_timeout=1, connection_acquisition_timeout=2, max_transaction_retry_time=0)
        ready()
        with driver.session() as session:
            assert session.run('MATCH (n) RETURN count(n) AS count').single()['count'] == 0
            for graph in ('graph_selected', 'graph_unrelated'):
                session.run('CREATE (g:Graph {graph_id:$id,fixture_id:$id}), '
                    '(s:Episode {graph_id:$id,fixture_id:$source,case_id:$case,data:"Fictional original source"}), '
                    '(g)-[:HAS_SOURCE {fixture:true}]->(s)',
                    id=graph, source=graph+'_source', case=graph+'_case').consume()
        foreign = graph_snapshot('graph_unrelated')
        storage = Neo4jStorage.__new__(Neo4jStorage)
        storage._driver = driver
        storage._embedding = SimpleNamespace(embed_batch=lambda texts: [[0.1, 0.2] for _ in texts])
        storage.RETRY_DELAY_BASE = .05
        action = AgentActivity('twitter', 1, 'Fictional speaker', 'CREATE_POST',
            {'content': 'Retained fictional action'}, 1, '2026-10-11T00:00:00')
        # Simulate loss of the acknowledgement after the real transaction commits.
        class AmbiguousSession:
            def __init__(self, session): self.session = session
            def __enter__(self): self.session.__enter__(); return self
            def __exit__(self, *args): return self.session.__exit__(*args)
            def execute_write(self, callback):
                result = self.session.execute_write(callback)
                if not acknowledged[0]:
                    acknowledged[0] = True
                    raise ServiceUnavailable('Synthetic lost commit acknowledgement')
                return result
        acknowledged = [False]
        storage._driver = SimpleNamespace(session=lambda: AmbiguousSession(driver.session()))
        ids = storage.add_agent_memories('graph_selected', [action.to_memory_record()])
        storage._driver = driver
        assert len(ids) == memory_count() == 1
        # A later extraction outage must not duplicate the earlier memory write.
        text_attempts = []
        def extraction(graph, text):
            text_attempts.append(graph)
            if len(text_attempts) < 3:
                raise ServiceUnavailable('Synthetic extraction-stage outage')
        storage.add_text = extraction
        updater = GraphMemoryUpdater('graph_selected', storage); updater.RETRY_DELAY = 0
        updater._send_batch_activities([action], 'twitter')
        assert len(text_attempts) == 3 and memory_count() == 2
        assert updater.get_stats()['items_sent'] == 1
        artifacts = output / 'retained-artifacts'; artifacts.mkdir()
        (artifacts / 'actions.jsonl').write_text(json.dumps(action.to_memory_record()) + '\n')
        (artifacts / 'section_1.md').write_text('Partial report remains available for review.\n')
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts.iterdir()}
        before = graph_snapshot('graph_selected')
        run('outage', ['docker', 'stop', '--time', '30', name], timeout=45)
        failed = GraphMemoryUpdater('graph_selected', storage); failed.RETRY_DELAY = 0
        failed._send_batch_activities([action], 'twitter')
        assert failed.get_stats()['failed_count'] == 1 and failed.get_stats()['items_sent'] == 0
        assert len(text_attempts) == 3, 'No extraction after a failed graph memory write'
        run('restart', ['docker', 'start', name])
        ready()  # Reuses the existing driver and storage object.
        assert graph_snapshot('graph_selected') == before
        storage.set_ontology('graph_selected', {'after_reconnect': True})
        assert storage.get_ontology('graph_selected') == {'after_reconnect': True}
        assert graph_snapshot('graph_unrelated') == foreign
        storage.delete_graph("' }) DETACH DELETE n //")
        assert graph_snapshot('graph_unrelated') == foreign
        storage.delete_graph('graph_selected')
        assert graph_snapshot('graph_selected') == {'nodes': [], 'edges': []}
        assert graph_snapshot('graph_unrelated') == foreign
        assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts.iterdir()}
        receipt.update(status='passed', reconnect_with_same_driver=True, commit_ack_loss_memories=1,
            later_stage_retries=3, later_stage_memories_added=1, exhausted_batch_stats=failed.get_stats(),
            unrelated_graph_preserved=True, scoped_graph_deleted=True, partial_artifact_hashes=hashes,
            graph_before_outage=before, unrelated_graph=foreign)
    except Exception as exc:
        receipt.update(status='failed', error=str(exc))
    finally:
        if driver is not None: driver.close()
        if 'container' in created:
            run('service-logs', ['docker', 'logs', name], check=False)
            run('remove-container', ['docker', 'rm', '--force', name], check=False)
        if 'volume' in created:
            run('remove-volume', ['docker', 'volume', 'rm', volume], check=False)
        receipt['cleanup_passed'] = all(item['exit_code'] == 0 for item in receipt['commands'] if item['label'].startswith('remove-'))
        save()
    print(json.dumps({key: value for key, value in receipt.items() if key not in {'commands', 'graph_before_outage', 'unrelated_graph'}}, indent=2))
    return 0 if receipt['status'] == 'passed' and receipt['cleanup_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
