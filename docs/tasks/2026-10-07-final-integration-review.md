# Final integration review — 2026-10-07

Scope: PR #3 against canonical CrowdLens main. The user authorized final code review, necessary repairs and merge once unresolved issues were addressed. The source-review approval is separate from this code review.

The coordinator reviewed request admission and transport accounting, task leases and recovery, ensemble ownership, source scope/claim validation, revision acceptance/export, UI recovery and upload authorization, and build/privacy boundaries. Earlier independent milestone reviews remain supporting history; this final pass is coordinator review, not a new independent reviewer certification. Graph discovery was used, with actual source/diffs read where indexed bounds were stale.

## Findings and repairs

- Accepted evidence revisions preserved structured forecast metadata but rebuilt the Markdown from the outline alone, omitting the frozen forecast table from downloads. Revision assembly now prepends the existing deterministic forecast display when metadata exists, without changing probabilities or the parent. A persisted acceptance/export/idempotency regression failed before the repair and passes afterward.
- Ensemble admission omitted the runtime root required by recovery. Failed attempts could leave pending repair and block manual retries. Admission now records the actual run-state root. A failed API-admitted attempt with a real state file now reconciles to stopped and permits a manual retry; the regression failed before repair.
- Ensemble and single-run admission used different resource keys for the same mutable simulation runtime. Ensemble admission now also reserves the shared simulation-runtime key, so an active single run rejects ensemble admission before dispatch. The API regression failed before repair.

All three findings are resolved. Focused revision/ensemble checks pass 31 tests. The full `UV_PYTHON=3.11 npm run check` passes 737 backend, 12 Node and 61 component tests (810 total), plus production build. No paid generation or private-source transmission was needed for these repairs; no test fixture expectations were weakened. Existing saved reports were not rewritten by these code fixes.

## Merge gate

Re-run cloud backend/frontend/container CI on the repaired PR head, then merge using an expected-head check. Preserve unrelated dirty main-checkout work. Keep the running browser report on its existing URL and restart only the patched backend. Report approval does not retroactively rewrite stored machine-review labels.
