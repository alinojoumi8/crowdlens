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
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() or not output.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        parser.error("Use a new output directory beneath the system temporary directory")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image):
        parser.error("Supply the full immutable ID of an already cached Neo4j image")
    output.mkdir()
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
        load_name = prefix + "-load"
        containers.append(load_name)
        run("cold-load", ["docker", "run", "--pull", "never", "--name", load_name,
            "--network", "none", "--memory", "2g", "--cpus", "2", "--user", "0:0",
            "--mount", f"type=volume,source={volumes[2]},target=/data",
            "--mount", f"type=volume,source={volumes[1]},target=/backups,readonly",
            "--entrypoint", "neo4j-admin", args.image, "database", "load", "neo4j", "--from-path=/backups"])
        restored = start_service(restore_name, volumes[2])
        try:
            after = snapshot(restored)
        finally:
            restored.close()
        assert after == before
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
