# Control/recovery evidence index

Final tested code: `34ad6d27e298f33317e443f0123143fa5e865eab`.
Runtime fingerprint: `fea6ca781b9a175fe9face0055dc195bf7f685551e5af5a5f2b42a5342450006`.
The [audit](../../2026-10-03-control-recovery.md) and
[accounting report](../../2026-10-03-bike-lane-request-accounting.md) explain
results and limitations. Raw failure receipts are preserved without relabelling
them as successful.

## Final receipts

- [candidate-identity.json](candidate-identity.json): tested commit/tree/source
  fingerprint, tracked source state and fingerprint exclusions.
- [check-delivery-candidate.txt](check-delivery-candidate.txt): 496 backend,
  12 Node, 37 Vitest tests and production build.
- [evaluations-result.json](evaluations-result.json) and
  [evaluations-final.txt](evaluations-final.txt): 168 IDs × three repeats, 504
  passes; model quality and reviewer metrics null, four human packets pending.
- [h1-final.txt](h1-final.txt): actual exited-owner two-process recovery.
- [backup-result.json](backup-result.json) and [backup-final.txt](backup-final.txt):
  quiesced synthetic DB/artifact restore with scope exclusions.
- [browser-workflow/results.json](browser-workflow/results.json): 12 checks and
  24 snapshots; injected failures, substitutions and lab-only performance samples.
- [browser-regressions/results.json](browser-regressions/results.json): 10 checks
  on an isolated fixture backend, dialog accessibility at three widths.
- [visible/identity.json](visible/identity.json), [visible/receipt.json](visible/receipt.json)
  and the three visible screenshots: fixture substitutions, real proposal
  acceptance/reopen and unchanged parent hashes. Zero real provider calls.
- [npm-audit-root.json](npm-audit-root.json),
  [npm-audit-frontend.json](npm-audit-frontend.json),
  [python-dependency-check-uv.txt](python-dependency-check-uv.txt),
  [compose-validation-isolated.json](compose-validation-isolated.json): dependency
  advisory/config parsing checks, not Python/container CVE or new-image evidence.
- [independent-review.md](independent-review.md): final successor source review,
  four independently passing regressions and exact limits of that review.
- [main-preservation.json](main-preservation.json),
  [historical-preservation.json](historical-preservation.json),
  [recovery-copy.json](recovery-copy.json): original main overlays/frozen artifacts
  unchanged and prepared copy identity. No paid recovery performed.
- [owned-preview-cleanup.json](owned-preview-cleanup.json): only owned synthetic
  previews stopped; visible port 18750 retained. Growing server logs were moved
  intact to the external review directory, not committed as frozen receipts.

## Fail-first reproductions

Valid product assertions and implementation-boundary tests are retained in:

- `before-regressions.txt`: seven failures covering worker settings, four
  timezone/state combinations, Stop drain and monitor overwriting Stopped.
- `before-unsupported-settings.txt`: five invalid supported-field values.
- `before-browser-controls.txt`, `before-prepare-and-case-ui-valid.txt`,
  `before-prepared-control-values.txt`, `before-resume-polling-valid.txt`,
  `before-stopped-page-header.txt`: terminal polling, unsafe prepare/start on
  reopen, visible numeric overrides, effective rounds and explicit Resume/header.
- `before-control-edges.txt`, `before-run-state-fence.txt`,
  `before-shared-run-state-cache.txt`, `before-publication-drain.txt`: partial
  usage/completion, archived evidence, failed-owner repair, stale publication,
  same-attempt cache refresh and cleanup/drain boundaries.
- `before-unscoped.txt`, `before-authorization-race.txt`: unscoped production
  admission and delayed authorization for changed input.
- `before-terminal-progress.txt`, `before-recovery-depth.txt`,
  `before-read-only-resource-binding.txt`,
  `before-recovery-related-binding-valid.txt`,
  `before-generation-retry-valid.txt`: honest failed/queued recovery state,
  depth propagation, read/recovery binding and duplicate-generation prevention.
- `before-allowance.txt`: collection failure because the proposed ledger module
  did not exist. This records a missing implementation contract; it is not an
  executed concurrency assertion or a historical runtime traceback.

Final counterparts run in the complete suites, including
`backend/tests/test_control_recovery.py`, `test_control_edges.py`,
`test_execution_api.py`, `test_workflow_execution.py`, and frontend component
tests. Earlier passing logs are intermediate evidence, not final-SHA results.

## Historical evidence and setup corrections

`historical-report-progress-error.json` is the frozen original HTTP error.
`historical-progress-log-excerpt.txt` retains relevant historical log lines but
does not contain a production stack. `historical-progress-reproduced-traceback.txt`
is the explicitly labelled invocation of historical code on frozen progress.
`historical-container-mounts.json` records non-secret mounts/image inspection.
`historical-request-accounting.json` contains stage reconstruction;
`historical-relay-requests.jsonl` preserves allowlisted raw usage/timing receipts.

The following failed driver/setup attempts are retained but are **not counted
as confirmed product regressions**: unsupported CLI `--run` in
`before-prepare-and-case-ui.txt`; missing outline/button fixture in
`before-resume-poll-delay.txt`; first incorrectly exported/typed retry fixture in
`before-generation-retry.txt`; first recovery fake without GraphTools in
`before-recovery-related-binding.txt`; early incomplete fake timestamps/attributes
and harness syntax/configuration errors in intermediate logs. The correctly
configured `*-valid.txt` files supersede their assertion evidence, without deleting
the earlier failures.

`python-dependency-check.txt` records unavailable `python -m pip`; the supported
`uv pip check` passed later. `compose-validation.txt` records the missing `.env`
setup failure; both configurations subsequently parsed against a disposable
synthetic environment. Browser intermediate failures include genuine contrast
and source defects subsequently repaired, plus mutable-fixture interference;
the final separate-backend browser receipts distinguish the accepted result.
The historical/intermediate `check-*.txt`, `build-*.txt` and browser logs retain
their own source identities/counts and do not verify the final candidate.

No failed command, injected HTTP error, scripted model output or quality heuristic
is treated as real-provider success. Native visible screenshots contain JPEG
bytes; their extensions were corrected without editing pixels. The initial
extension-check failure is retained in `documentation-checks-before-image-extension.json`
and is not an application failure. [Documentation checks](documentation-checks.json)
validate links, structured receipts, image formats, candidate/bundle identities
and original hashes. The [manifest](manifest.json) records the final stable files;
the later documentation commit is reported separately from tested application
identity.
