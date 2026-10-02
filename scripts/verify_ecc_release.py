#!/usr/bin/env python3
"""Verify a named commit in a new checkout with fresh installed environments.

This runner does not build/start Docker services or execute generation models.
Run those separately against the recorded checkout and append their receipts.
Dependency download caches may be reused; installed environments are never copied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, help="Full frozen commit SHA")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--tool-bin", action="append", default=[], type=Path,
                        help="Prepend isolated Node 22 and uv 0.9.26 bin directories")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    temporary = Path(tempfile.gettempdir()).resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", args.candidate):
        parser.error("candidate must be a full commit SHA")
    if output.exists() or output.parent != temporary or not output.name.startswith("crowdlens-ecc-release-"):
        parser.error("output must be a new /tmp/crowdlens-ecc-release-* directory")
    output.mkdir()
    logs = output / "logs"
    logs.mkdir()
    checkout = output / "source"
    env = {key: os.environ[key] for key in ("HOME", "USER", "LANG", "SSL_CERT_FILE", "SSL_CERT_DIR")
           if key in os.environ}
    env.update({
        "PATH": os.pathsep.join([str(p.resolve()) for p in args.tool_bin] + [os.environ.get("PATH", "")]),
        "UV_PYTHON": "3.11", "UV_FROZEN": "1", "UV_LINK_MODE": "copy",
        "LLM_API_KEY": "synthetic-local-only", "LLM_DEFAULT_PROVIDER": "ollama",
        "LLM_BASE_URL": "http://127.0.0.1:9/v1", "LLM_MODEL_NAME": "synthetic-no-generation",
        "OPENAI_API_BASE_URL": "http://127.0.0.1:9/v1",
        "EMBEDDING_BASE_URL": "http://127.0.0.1:9", "EMBEDDING_AUTO_PULL": "False",
        "NEO4J_URI": "bolt://127.0.0.1:9", "NEO4J_PASSWORD": "synthetic-release-only",
        "JEV_EVIDENCE_MODE": "off", "JEV_INTERVIEW_MODE": "off", "JEV_RERANK_MODE": "off",
        "MARKET_DATA_PROVIDER": "none", "FLASK_DEBUG": "False", "CI": "true",
        "CROWDLENS_BUILD_REVISION": args.candidate,
    })
    receipt = {"candidate": args.candidate, "source_repository": str(source),
               "checkout": str(checkout), "commands": [], "gaps": [],
               "environment_policy": "credential-neutral; local disabled provider endpoints; fresh installs",
               "runner_sha256": digest(Path(__file__)), "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    def save():
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def run(label, command, cwd=checkout, timeout=900):
        log = logs / (label + ".log")
        start = time.monotonic()
        with log.open("w") as stream:
            try:
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # npm/uv may have descendants: stop the isolated command group.
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                code = 124
                stream.write("\nVerification command timed out.\n")
            except OSError as exc:
                code = 127
                stream.write(str(exc) + "\n")
        receipt["commands"].append({"label": label, "argv": command, "cwd": str(cwd),
                                    "exit_code": code, "seconds": round(time.monotonic() - start, 3),
                                    "log": str(log), "sha256": digest(log)})
        save()
        print(f"{label}: exit={code} log={log}", flush=True)
        return code

    try:
        for label, command in (("node-version", ["node", "--version"]),
                               ("npm-version", ["npm", "--version"]),
                               ("uv-version", ["uv", "--version"])):
            if run(label, command, cwd=source):
                raise RuntimeError("Required runtime unavailable")
        if not (logs / "node-version.log").read_text().startswith("v22."):
            raise RuntimeError("Use the CI Node 22 major")
        if not (logs / "uv-version.log").read_text().startswith("uv 0.9.26"):
            raise RuntimeError("Use CI-pinned uv 0.9.26")
        if run("clone", ["git", "clone", "--no-hardlinks", "--no-checkout", str(source), str(checkout)], cwd=source):
            raise RuntimeError("Fresh clone failed")
        if run("checkout", ["git", "checkout", "--detach", args.candidate]):
            raise RuntimeError("Candidate checkout failed")
        run("initial-git-state", ["git", "status", "--porcelain=v1", "--untracked-files=all"])
        if (logs / "initial-git-state.log").read_text().strip():
            raise RuntimeError("New checkout is not clean")
        receipt["tree"] = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=checkout, text=True).strip()
        lockfiles = ["package-lock.json", "frontend/package-lock.json", "backend/uv.lock"]
        receipt["locks_before"] = {name: digest(checkout / name) for name in lockfiles}
        for label, command, cwd in (
            ("install-root", ["npm", "ci"], checkout),
            ("install-frontend", ["npm", "ci", "--prefix", "frontend"], checkout),
            ("install-backend", ["uv", "sync", "--frozen", "--dev"], checkout / "backend"),
        ):
            if run(label, command, cwd=cwd, timeout=1800):
                raise RuntimeError("Frozen dependency installation failed")
        python = str(checkout / "backend/.venv/bin/python")
        run("python-version", [python, "--version"])
        run("installed-python", ["uv", "pip", "freeze", "--python", python])
        run("installed-root", ["npm", "ls", "--all", "--json"])
        run("installed-frontend", ["npm", "ls", "--prefix", "frontend", "--all", "--json"])
        run("check", ["npm", "run", "check"], timeout=1200)
        run("audit-root", ["npm", "audit", "--audit-level=moderate", "--json"])
        run("audit-frontend", ["npm", "audit", "--prefix", "frontend", "--audit-level=moderate", "--json"])
        run("h1-process-recovery", [python, "backend/scripts/probe_milestone2_task_restart.py"], timeout=75)
        run("backup-restore", [python, "backend/scripts/check_ecc_backup.py", "--synthetic",
                               "--output-dir", str(output / "backup")])
        evaluation = checkout / "backend/scripts/evaluate_evidence_quality.py"
        if evaluation.is_file():
            # The evaluator deliberately requires a fresh direct /tmp child.
            evaluation_output = temporary / ("crowdlens-ecc-eval-" + args.candidate[:12] + "-" + output.name)
            receipt["evaluation_output"] = str(evaluation_output)
            run("evaluations", [python, str(evaluation), "--output-dir", str(evaluation_output), "--repeats", "3"])
        else:
            receipt["gaps"].append("Milestone 3 evaluator absent from candidate")
        compose_env = checkout / ".env"
        compose_env.write_text("NEO4J_PASSWORD=synthetic-release-only\nLLM_API_KEY=synthetic-local-only\n"
                               "LLM_BASE_URL=http://127.0.0.1:9/v1\nEMBEDDING_AUTO_PULL=False\n")
        try:
            run("compose-config", ["docker", "compose", "--env-file", str(compose_env), "config", "--quiet"])
            run("compose-rendered", ["docker", "compose", "--env-file", str(compose_env), "config", "--format", "json"])
            receipt["synthetic_compose_env_sha256"] = digest(compose_env)
        finally:
            compose_env.unlink()
        run("runtime-identity", [python, "-c", "import json,sys;sys.path.insert(0,'backend');"
                                 "from app.utils.build_identity import runtime_identity;print(json.dumps(runtime_identity()))"])
        run("diff-check", ["git", "diff", "--check"])
        run("final-git-state", ["git", "status", "--porcelain=v1", "--untracked-files=all"])
        run("ignored-runtime-inputs", ["git", "status", "--short", "--ignored"])
        receipt["locks_after"] = {name: digest(checkout / name) for name in lockfiles}
        receipt["frozen_inputs_unchanged"] = receipt["locks_before"] == receipt["locks_after"]
        receipt["tracked_checkout_clean"] = not (logs / "final-git-state.log").read_text().strip()
        if not receipt["frozen_inputs_unchanged"] or not receipt["tracked_checkout_clean"]:
            raise RuntimeError("Verification changed the candidate's tracked or untracked inputs")
        receipt["gaps"].extend([
            "Browser suite, real HTTP/Neo4j and isolated exact-candidate image startup need separate receipts",
            "No configured lint/type-check/coverage command; coverage percentage unmeasured",
            "Exact-candidate remote CI pending authorized push/remote execution",
            "Real generation workflow and independently human-reviewed quality not established by this runner",
        ])
    except Exception as exc:
        receipt["error"] = str(exc)
    receipt["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    receipt["local_commands_passed"] = not receipt.get("error") and all(c["exit_code"] == 0 for c in receipt["commands"])
    save()
    return 0 if receipt["local_commands_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
