# H1 integration review and corrective evidence

Date: 2026-10-02. Scope: local source, synthetic data, no deployment change.
This addendum preserves and extends the [original H1 evidence](2026-10-02-h1-task-recovery.md).
Final candidate verification is reported separately in the Milestones 3–5 handoff.

A fresh independent AI reviewer examined the combined implementation and reproduced
two missed call-site boundaries. This is code review, not human factual adjudication.
Both defects were reproduced by the coordinator before changing application code.

| Finding | Before | Repair and regression |
| --- | --- | --- |
| P2: stale preparation files override active/failed task state | At application commit `05c86a6`, status polling returned `ready` for both live and expired re-preparation attempts; it could directly promote the state file. Manual retry reused old files. Six failing API assertions, one completed-preparation control passed. | `b5bbfac`: durable current preparation ownership takes precedence; polling no longer promotes state, new preparation clears the old readiness flag, expired work permits a new manual attempt. Seven new cases pass; 41 ownership/admission/preparation cases pass. |
| P1: expired ensemble cleanup can delete a replacement run | At application commit `b5bbfac`, a controlled handoff during shutdown lets the old worker delete the replacement's real `run_state.json` and SQLite row; stale dispatch/shutdown were also possible. Three failing cases, one valid-owner control passed. | `c800a3d`: check ownership while serializing actual cleanup, dispatch, close and stop operations with replacement admission; propagate ownership loss instead of treating it as a recoverable sample error. Four new cases pass; 38 related ensemble/ownership/preparation cases pass. |

The before runs added only their new regression test files to the named application
commits. Those unchanged assertions are committed in the repair commits. The after
focused runs used the same assertions with the repairs. The complete backend run
on clean combined commit `bc1bf6c` passed **448 tests** in 9.89 seconds. Its 18
warnings concern pytest JUnit property formatting; the dedicated evaluator uses
the compatible legacy JUnit format. No application assertion was skipped or weakened.

Commands from `backend/`:

```bash
.venv/bin/python -m pytest tests/test_prepare_recovery_api.py -q
.venv/bin/python -m pytest tests/test_ensemble_ownership.py -q
.venv/bin/python -m pytest tests/test_prepare_recovery_api.py tests/test_task_ownership.py tests/test_report_admission.py -q
.venv/bin/python -m pytest tests/test_ensemble_ownership.py tests/test_ensemble_runner.py tests/test_task_ownership.py tests/test_prepare_recovery_api.py -q
.venv/bin/python -m pytest tests -q
```

[Preserved receipts and hashes](evidence/2026-10-02-h1-integration-review/sha256.json)
include both reviewer reproductions and all five JUnit receipts. The ensemble
handoff tests use a controlled lease clock and substituted process-control calls;
cleanup, filesystem and SQLite are real. They make no claim that an OASIS child
or generation model ran. Earlier real-process H1 checks remain separate evidence.

Process-control operations must hold the ownership gate until the admitted operation
finishes; close uses its existing 20-second IPC timeout. A slow operation can delay
heartbeat/recovery and cause subsequent work to lose ownership. This is a safety
boundary, not a hard real-time recovery guarantee. Already-issued external work
is not retroactively cancelled; mixed old writers, exact-round continuation and
lossless agent memory remain outside the verified ownership contract.
