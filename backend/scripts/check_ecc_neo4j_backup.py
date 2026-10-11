"""Rehearse cold Neo4j dump/load with new synthetic Docker volumes only.

The image must already be cached and supplied by immutable image ID. No images
are pulled, existing services are used, models run, or ports publicly bound.
This does not prove an online snapshot or consistency with concurrently written
application artifacts. All newly created containers and volumes are removed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", required=True, action="store_true")
    parser.add_argument("--image", required=True, help="Cached sha256 image ID")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument('--coordinated', action='store_true', help='Include synthetic application artifacts, review database and a verified manifest')
    parser.add_argument('--app-image', help='Immutable application image identity for the restore manifest')
    parser.add_argument('--revision', help='Application source revision for the restore manifest')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() or not output.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        parser.error("Use a new output directory beneath the system temporary directory")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image):
        parser.error("Supply the full immutable ID of an already cached Neo4j image")
    output.mkdir()
    application = None
    if args.coordinated:
        from cold_backup_bundle import create_bundle, restore_artifacts, verify_bundle, inventory
        if not args.app_image or not args.revision:
            parser.error('--coordinated requires --app-image and --revision')
        (output / '.ecc-backup-owner').write_text('Disposable coordinated synthetic rehearsal')
        live = output / 'synthetic-live'; live.mkdir()
        child_script = str(Path(__file__).with_name('check_ecc_backup.py'))
        subprocess.run([sys.executable, child_script, '--synthetic', '--output-dir', str(live), '--child', 'seed'], check=True)
        application = json.loads((live / 'synthetic.json').read_text())
        app_before = inventory(live)
    prefix = "crowdlens-ecc-release-backup-" + uuid.uuid4().hex[:12]
    volumes = [prefix + suffix for suffix in ("-source", "-archive", "-restore")]
    containers = []
    created_volumes = []
    receipt = {"image": args.image, "commands": [], "scope": "cold synthetic Neo4j dump/load",
               "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "volumes": volumes, "containers": containers, "real_model_calls": 0}

    def save():
        (output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def run(label, argv, check=True, timeout=180):
        started = time.monotonic()
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        log = output / (label + ".log")
        log.write_text(result.stdout + result.stderr)
        receipt["commands"].append({"label": label, "argv": argv, "exit_code": result.returncode,
                                    "seconds": round(time.monotonic() - started, 3), "log": str(log),
                                    "sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
        save()
        if check and result.returncode:
            raise RuntimeError(f"{label} failed; see {log}")
        return result.stdout.strip()

    def start_service(name, volume):
        containers.append(name)
        run(name + "-start", ["docker", "run", "--detach", "--pull", "never", "--name", name,
            "--memory", "2g", "--cpus", "2", "--publish", "127.0.0.1::7687",
            "--mount", f"type=volume,source={volume},target=/data", "--tmpfs", "/logs:rw,size=128m",
            "--env", "NEO4J_AUTH=neo4j/crowdlens-synthetic-backup-password",
            "--env", "NEO4J_server_memory_heap_initial__size=256m",
            "--env", "NEO4J_server_memory_heap_max__size=512m",
            "--env", "NEO4J_server_memory_pagecache_size=256m", args.image])
        port = run(name + "-port", ["docker", "port", name, "7687/tcp"]).split(":")[-1]
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://127.0.0.1:" + port,
            auth=("neo4j", "crowdlens-synthetic-backup-password"), connection_timeout=2)
        deadline = time.monotonic() + 60
        while True:
            try:
                with driver.session() as session:
                    session.run("MATCH (n) RETURN count(n)").single()
                break
            except Exception:
                if time.monotonic() >= deadline:
                    driver.close()
                    raise
                time.sleep(1)
        return driver

    def snapshot(driver):
        with driver.session() as session:
            nodes = [dict(row) for row in session.run(
                "MATCH (n) RETURN labels(n) AS labels, properties(n) AS properties ORDER BY n.fixture_id")]
            edges = [dict(row) for row in session.run(
                "MATCH (a)-[r]->(b) RETURN a.fixture_id AS start, type(r) AS type, properties(r) AS properties, "
                "b.fixture_id AS end ORDER BY start, end")]
        return {"nodes": nodes, "edges": edges}

    try:
        identity = run("image-identity", ["docker", "image", "inspect", "--format", "{{.Id}}", args.image])
        assert identity == args.image
        if application:
            import runpy
            app_id = run('app-image-identity', ['docker','image','inspect','--format','{{.Id}}',args.app_image])
            assert app_id == args.app_image
            identity_fn = runpy.run_path(str(Path(__file__).resolve().parents[1]/'app/utils/build_identity.py'))['source_identity']
            expected = identity_fn(Path(__file__).resolve().parents[2],args.revision)
            actual = json.loads(run('app-source-identity', ['docker','run','--rm','--pull','never','--network','none',
                '--entrypoint','python',args.app_image,'-c',
                "import runpy,json; print(json.dumps(runpy.run_path('/app/backend/app/utils/build_identity.py')['runtime_identity']()))"]))
            assert actual == expected, 'Application image source/revision differs from the rehearsal checkout'
            receipt['app_source_identity'] = actual
        for volume in volumes:
            run(volume + "-create", ["docker", "volume", "create", volume])
            created_volumes.append(volume)
        source_name, restore_name = prefix + "-source-service", prefix + "-restored-service"
        driver = start_service(source_name, volumes[0])
        try:
            with driver.session() as session:
                assert session.run("MATCH (n) RETURN count(n) AS count").single()["count"] == 0
                session.run("CREATE (g:Graph {fixture_id:'graph',graph_id:'ecc_backup_graph'}), "
                    "(e:Episode {fixture_id:'source',graph_id:'ecc_backup_graph',case_id:'synthetic_case',"
                    "case_version_id:'v1',document_id:'synthetic_doc',origin:'source_document',"
                    "data:'Synthetic hearing notice'}), (g)-[:HAS_SOURCE {fixture:true}]->(e)").consume()
            if application:
                source = application['retained_source']
                with driver.session() as session:
                    session.run('CREATE (s:Episode {fixture_id:$id, graph_id:$graph_id, case_id:$case_id, '
                                'case_version_id:$case_version_id, document_id:$document_id, origin:$origin, '
                                'data:$text, source_hash:$source_hash}), '
                                '(a:BackupArtifact {fixture_id:"artifact", report_id:"report_root", revision_id:$revision, '
                                'proposal_digest:$digest, review_packet_sha256:$packet}), (a)-[:RETAINS_SOURCE]->(s)',
                                id=source['evidence_id'], graph_id=source['graph_id'], case_id=source['case_id'],
                                case_version_id=source['case_version_id'], document_id=source['document_id'],
                                origin=source['origin'], text=source['window'], source_hash=source['source_hash'],
                                revision=application['revision_id'], digest=application['digest'], packet=application['review_packet_sha256']).consume()
            before = snapshot(driver)
        finally:
            driver.close()
        (output / "synthetic-graph.json").write_text(json.dumps(before, indent=2) + "\n")
        run("stop-before-dump", ["docker", "stop", "--time", "30", source_name], timeout=45)
        dump_name = prefix + "-dump"
        containers.append(dump_name)
        run("cold-dump", ["docker", "run", "--pull", "never", "--name", dump_name,
            "--network", "none", "--memory", "2g", "--cpus", "2", "--user", "0:0",
            "--mount", f"type=volume,source={volumes[0]},target=/data",
            "--mount", f"type=volume,source={volumes[1]},target=/backups",
            "--entrypoint", "neo4j-admin", args.image, "database", "dump", "neo4j", "--to-path=/backups"])
        run("copy-archive", ["docker", "cp", dump_name + ":/backups/neo4j.dump", str(output / "neo4j.dump")])
        receipt["dump_sha256"] = hashlib.sha256((output / "neo4j.dump").read_bytes()).hexdigest()
        archive_mount = f'type=volume,source={volumes[1]},target=/backups,readonly'
        if application:
            bundle = output / 'coordinated-bundle'
            manifest = create_bundle({'uploads':live}, output/'neo4j.dump', bundle,
                revision=args.revision, app_image=args.app_image, neo4j_image=args.image,
                quiescence={'application_writers_stopped':True, 'neo4j_stopped_during_dump':True,
                            'exclusive_graph_ownership':True, 'observed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                            'note':'Synthetic application seed process exited; this tool stopped its exclusively owned Neo4j container before dumping.'})
            stage = output / 'artifact-restore'
            restore_artifacts(bundle, stage)
            assert inventory(live) == app_before == inventory(stage/'stores/uploads')
            shutil.copytree(stage/'stores/uploads', output/'restored')
            subprocess.run([sys.executable,child_script,'--synthetic','--output-dir',str(output/'restored'),'--child','read'], check=True)
            archive_mount = f'type=bind,source={stage},target=/backups,readonly'
        load_name = prefix + "-load"
        containers.append(load_name)
        run("cold-load", ["docker", "run", "--pull", "never", "--name", load_name,
            "--network", "none", "--memory", "2g", "--cpus", "2", "--user", "0:0",
            "--mount", f"type=volume,source={volumes[2]},target=/data",
            "--mount", archive_mount,
            "--entrypoint", "neo4j-admin", args.image, "database", "load", "neo4j", "--from-path=/backups"])
        restored = start_service(restore_name, volumes[2])
        try:
            after = snapshot(restored)
        finally:
            restored.close()
        assert after == before
        if application:
            linked = next(row['properties'] for row in after['nodes'] if row['properties'].get('fixture_id') == 'artifact')
            assert linked['revision_id'] == application['revision_id']
            assert linked['proposal_digest'] == application['digest']
            assert linked['review_packet_sha256'] == application['review_packet_sha256']
            assert inventory(live) == app_before
            live.rename(output/'archived-original')
            shutil.copytree(stage/'stores/uploads', live)
            subprocess.run([sys.executable,child_script,'--synthetic','--output-dir',str(live),'--child','recover'], check=True)
            assert inventory(output/'archived-original') == app_before
            verify_bundle(bundle)
            receipt.update(coordinated_backup='passed',bundle_id=manifest['bundle_id'],
                artifact_files=len(manifest['files']),sqlite_databases=len(manifest['sqlite_integrity_checked']),
                immutable_parent_and_revision_hashes_preserved=True,review_packet_and_labels_preserved=True,
                graph_to_artifact_links_preserved=True,same_root_expired_worker_recovery='passed',
                original_snapshot_unchanged=True,app_revision=args.revision,app_image=args.app_image)
        receipt.update(status="passed", restored_graph_matches=True, nodes=len(after["nodes"]),
                       relationships=len(after["edges"]), stopped_before_dump=True,
                       graph_sha256=hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest())
    except Exception as exc:
        receipt.update(status="failed", error=str(exc))
    finally:
        for name in containers:
            run(name + "-logs", ["docker", "logs", name], check=False)
            run(name + "-remove", ["docker", "rm", "--force", name], check=False)
        for volume in created_volumes:
            run(volume + "-remove", ["docker", "volume", "rm", volume], check=False)
        receipt["cleanup_passed"] = all(row["exit_code"] == 0 for row in receipt["commands"] if row["label"].endswith("-remove"))
        save()
    print(json.dumps({key: value for key, value in receipt.items() if key != "commands"}, indent=2))
    return 0 if receipt.get("status") == "passed" and receipt["cleanup_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
