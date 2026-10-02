"""Cold SQLite/artifact backup rehearsal using new synthetic data only.

Each seed/read occurs in its own process. The writer exits before a complete
directory copy. This proves the documented quiesced local copy path, not a hot,
cross-store snapshot, power-loss durability or a Neo4j backup.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND), str(BACKEND / "tests")]


def hashes(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def synthetic_process(root, seed):
    def no_network(*args, **kwargs):
        raise RuntimeError("Network disabled in synthetic backup rehearsal")
    socket.socket.connect = no_network
    from app.config import Config
    Config.UPLOAD_FOLDER = str(root)
    Config.EMBEDDING_AUTO_PULL = False
    from app.storage.control_db import ControlDatabase
    from app.services.report_agent import ReportManager, ReportStatus
    from app.services.proposal_store import ProposalStore, ProposalError
    from app.services.report_revisions import ReportRevisionService
    from evidence_draft_samples import sample_report
    from test_evidence_drafting import run, SourceStorage
    ReportManager.REPORTS_DIR = ReportManager.FALLBACK_REPORTS_DIR = str(root / "reports")
    database = ControlDatabase(root / "control.db")
    if seed:
        database.put_project({"project_id": "synthetic_backup_project", "status": "graph_completed"})
        database.put_case({"case_id": "synthetic_backup_case", "label": "Synthetic backup fixture"})
        database.put_task({"task_id": "synthetic_backup_task", "status": "completed"})
        database.put_simulation_run({"simulation_id": "synthetic_backup_run", "status": "completed"})
        root.joinpath("documents").mkdir()
        root.joinpath("documents/source.txt").write_text("Synthetic hearing notice.\n")
        ReportManager.save_report(sample_report())
        original = hashes(root / "reports/report_root")
        record, llm = run(root / "reports")
        service = ReportRevisionService(ProposalStore(root / "reports"), storage=SourceStorage())
        revision = service.accept("report_root", record["proposal_id"], record["proposal_digest"])
        assert hashes(root / "reports/report_root") == original
        receipt = {"proposal_id": record["proposal_id"], "digest": record["proposal_digest"],
                   "revision_id": revision.report_id, "parent_hashes": original,
                   "substitutions": ["scripted drafting model", "in-memory synthetic source chunks"],
                   "scripted_model_calls": len(llm.calls), "real_model_calls": 0}
        root.joinpath("synthetic.json").write_text(json.dumps(receipt, indent=2))
        with sqlite3.connect(root / "control.db") as connection:
            assert connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
        print(json.dumps(receipt))
        return
    receipt = json.loads(root.joinpath("synthetic.json").read_text())
    assert database.get_project("synthetic_backup_project")["status"] == "graph_completed"
    assert database.get_case("synthetic_backup_case")["label"] == "Synthetic backup fixture"
    assert database.get_task("synthetic_backup_task")["status"] == "completed"
    assert database.get_simulation_run("synthetic_backup_run")["status"] == "completed"
    assert database.migration_state()["schema"]["version"] == 2
    with sqlite3.connect(root / "control.db") as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    revision = ReportManager.get_report(receipt["revision_id"])
    assert revision.status == ReportStatus.NEEDS_REVIEW and revision.revision
    assert hashes(root / "reports/report_root") == receipt["parent_hashes"]
    # Recovery of an already published revision needs neither source storage nor inference.
    store = ProposalStore(root / "reports")
    recovered = ReportRevisionService(store, storage=None).accept("report_root", receipt["proposal_id"], receipt["digest"])
    assert recovered.report_id == revision.report_id
    try:
        ReportManager.save_report(revision)
    except ProposalError as exc:
        assert "immutable_revision" in str(exc)
    else:
        raise AssertionError("Restored immutable revision was writable")
    assert hashes(root / "reports/report_root") == receipt["parent_hashes"]
    print(json.dumps({"restored_revision": revision.report_id, "status": "needs_review",
                      "idempotent_acceptance": True, "immutable": True, "database_integrity": "ok"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", required=True, action="store_true")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--child", choices=("seed", "read"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        parser.error("Use a disposable directory under the system temporary directory")
    if args.child:
        if output.name not in {"synthetic-live", "restored"} or not (output.parent / ".ecc-backup-owner").is_file():
            parser.error("Internal child processes require a rehearsal-owned directory")
        synthetic_process(output, args.child == "seed")
        return 0
    if output.exists():
        parser.error("Use a new output directory; existing data is never overwritten")
    output.mkdir()
    (output / ".ecc-backup-owner").write_text("Disposable synthetic backup rehearsal\n")
    live, backup, restored = [output / name for name in ("synthetic-live", "backup", "restored")]
    live.mkdir()
    subprocess.run([sys.executable, __file__, "--synthetic", "--output-dir", str(live), "--child", "seed"], check=True)
    before = hashes(live)
    shutil.copytree(live, backup)
    shutil.copytree(backup, restored)
    assert hashes(backup) == before == hashes(restored)
    assert any(".evidence-proposals/" in name for name in before)
    assert any(".evidence-locks/" in name for name in before)
    subprocess.run([sys.executable, __file__, "--synthetic", "--output-dir", str(restored), "--child", "read"], check=True)
    assert hashes(live) == before == hashes(backup)
    result = {"status": "passed", "scope": "quiesced synthetic SQLite and complete artifact-root copy",
              "writer_exited_before_backup": True, "restored_in_fresh_process": True,
              "source_unchanged": True, "copied_file_count": len(before), "file_hashes": before,
              "includes_hidden_proposals_and_locks": True, "neo4j_backup": "not covered",
              "hot_backup": "not covered", "power_loss_durability": "not covered"}
    output.joinpath("result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "file_hashes"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
