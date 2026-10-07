# Root report request retries

Date: 2026-10-02. Follow-up to the original Milestone 2 M2 retry hypothesis.
Application fix: `50e18a3a9731eda75f18ae920504faca46d63756`.

The frozen evaluation fault tests reproduced **duplicate admission**, not completed
artifact duplication. A lost response followed by an identical request, and two
concurrent identical requests, each produced two SQLite task rows, two different
root report IDs and two dispatches. Both HTTP responses were 200. Dispatch was
captured without executing generation; there were no model calls.

The fixtures and expected assertions were committed before the run in `d815c6d`
(integrated as `7b4a99a`). The coordinator independently reproduced both failures:

```bash
UV_PYTHON=3.11 uv run --project backend --frozen pytest \
  backend/tests/test_evidence_quality_faults.py -q -o junit_family=legacy \
  --junitxml=/tmp/crowdlens-ecc-coordinator-root-before.xml
```

Result: two failures, one passing transport-characterization test. The latter
uses simulated elapsed time and no network or sleeps.

## Repair contract

`POST /api/report/generate` accepts an optional `request_key`: 1–128 ASCII letters,
digits, underscore, dot, colon or hyphen. Task metadata retains the key and a
fingerprint of normalized generation inputs. Replay returns the original task
and report IDs, including after completion, failure or a new backend runtime.
Reusing a key with different inputs returns 409. Invalid keys return 400 before
admission. Reconciliation occurs before replay, so expired work is honestly failed.

Admission rechecks the key under the existing cross-process task publication lock
after readiness preflight. A separate resource binding admits only one active
root-generation request per simulation, including requests with different keys
or `force_regenerate`. The frontend preserves one key across automatic transport
retries; a new explicit generation invocation creates a new key. A failed request
is not restarted merely by replaying its key. Manual retry uses a new key.

Completed-root reuse for existing callers remains available. Idempotency records
live with the retained control-plane task rows; deleting those rows ends their
replay history. This change does not make arbitrary request types idempotent or
add an aggregate report-generation budget.

## Verification

After the application repair, the two frozen fault contracts pass unchanged.
The combined focused run returned **52 passed**:

```bash
UV_PYTHON=3.11 uv run --project backend --frozen pytest \
  backend/tests/test_evidence_quality_faults.py \
  backend/tests/test_report_admission.py backend/tests/test_task_ownership.py \
  backend/tests/test_milestone2_boundaries.py -q -o junit_family=legacy \
  --junitxml=/tmp/crowdlens-ecc-coordinator-root-after.xml
```

Added tests cover conflicting/invalid keys, competing different keys, terminal
replay through a fresh runtime, expiry and an explicit new-key retry. The frozen
concurrency tests use real Flask routes and SQLite with threads; H1's separate
process/lock regressions remain part of this run. A subsequent real two-backend-
process admission test also passes: both HTTP requests return the same task, with
one dispatch and one persisted row. All ten admission-specific tests passed in
that focused run (`d021799`). No real model quality, full
simulation or deployment result follows from these tests.

## Aggregate-budget finding remains open

The controlled transport probe observed five 300-second attempt timeouts and
2/4/8/16-second backoffs: **1,530 simulated seconds** for one Anthropic-compatible
logical call. This verifies the retry mechanism, not elapsed production latency.
Per-loop/per-transport limits do not establish a whole-report call, cost or
absolute deadline cap. The proposal-specific budget is a separate contract.

A future root-budget change needs an explicit policy across drafting, tool/claim
auxiliary calls, retries and late-result publication, with fail-first transport
and lifecycle tests. No new quality or performance threshold was invented from
this small synthetic observation. This remains an operational release caveat.
