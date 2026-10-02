# Milestone 4 browser QA — 2026-10-02

Owner: specialist B. Skill: ECC 2.2.3 `browser-qa`. Scope: isolated current-source preview, synthetic records only, focused frontend repairs and executable browser evidence. The coordinator owns integration and the overall release assessment.

**Bounded functional result: PASS. Historical visual regression: INCONCLUSIVE. Full real-service/model workflow: NOT RUN.** These screenshots establish a new baseline; no historical screenshot baseline existed. Seeded simulation/report states do not prove upstream extraction, simulation or report generation ran.

## Source and environment

- Starting source: H1 code `33d87c82c5f3ecb3435ba86a5160a44f79635443`; documentation overlay `fbedf59752fbc3387e4aa164c2f6f5869d4744de`.
- Frontend/harness implementation: `fb66abc9861d177e8c94caeb4c9e39ba90d120f1`. Test fixture corrections: `9a8701f`, `6c766ba`; sandbox correction/attestation: `5ca4390`. Modal palette/coverage corrections: `60888bf`, `0a3911b`, `dfc1fb`. **Final standalone tested source: `dfc1fb6571f90c7a706b2d4436201d2aef916752`.**
- Worktree: `/home/ali/.codex/worktrees/crowdlens-ecc-browser/mirofish-local`, branch `codex/crowdlens-ecc-browser`. Original checkout and older deployment were not used for these runs.
- Browser: existing Google Chrome `154.0.8037.92`, headless Linux, default device scale factor. Viewports: 375×1000, 768×1000, 1440×1000; full-page captures plus source-card viewport captures.
- Runner: Node `24.21.0`, Python `3.11.15`; independent frozen frontend install and independent backend `.venv`. Browser tooling installed separately beneath `/tmp`, pinned `playwright-core@1.55.1` and `axe-core@4.10.3`. No package manifest or lockfile changes.
- Preview built with `npm --prefix frontend run build`, served by the dedicated loopback harness. The final sandboxed standalone workflow used `127.0.0.1:18757`, with fresh artifacts at `/tmp/crowdlens-ecc-browser-reviewed-workflow`; browser evidence at `/tmp/crowdlens-ecc-browser-reviewed-workflow-ui`. Recovery used a separate fresh harness on `127.0.0.1:18756` and `/tmp/crowdlens-ecc-browser-reviewed-recovery-ui`.
- [Exact identity receipt](2026-10-02-milestone4-browser-qa/receipts/identity-workflow-dfc1fb.json) records the source commit, runtime source digest and SHA-256 of every built frontend asset. Runtime source digest: `2290e6d1a4144971c9bdc7c9e1826bee94e717000ddefc58ceae7c5e50219d09`.

## Execution boundaries

| Layer | What actually ran | Substitute or limitation |
| --- | --- | --- |
| Browser | Built Vue UI, actual routes, native form controls, keyboard events, HTTP | External font requests fulfilled with empty CSS; no external browser traffic |
| Upload | Real multipart upload endpoint, file processing, project/case persistence and task records | Deterministic ontology generator and graph builder/storage; no model, embedding or Neo4j extraction |
| Scenario/simulation | Real frontend preparation/progress/navigation | Synthetic profile, configuration and completed run endpoints; no OASIS simulation |
| Root report | Actual report loading/rendering and progress APIs | Seeded original report; one generate response intercepted to navigate to it; no root model generation |
| Evidence proposal | Real proposal API, retrieval boundary, store, validation, acceptance and revision publication | Synthetic original-source storage and deterministic three-phase drafting model; semantic embedder unavailable |
| Recovery | A real separate owner process creates a durable task then exits; production lease expiration, API recovery, project failure, UI retry and new task | Retry's graph builder is synthetic. API polling and the background monitor both run; this is not independent proof of timer-only recovery |
| Report interruption | Actual built report controls | Report/progress response fields intercepted to represent an interrupted root; no provider resume call |

Harness outbound `requests`/`httpx` traffic is disabled, provider keys are synthetic, and Jev modes are off. All data, SQLite files, reports and tasks live under fresh `/tmp/crowdlens-ecc-browser-*` directories. It never binds publicly, downloads models, changes services or volumes, or uses private fixtures.

Chromium sandbox proof is recorded in both final receipts: actual launch arguments omit `--no-sandbox`; `chrome://sandbox` reports namespace isolation, PID/network namespaces, Seccomp-BPF and TSYNC enabled, and “adequately sandboxed”. Earlier investigative runs used an unnecessary sandbox override; coordinator review caught it. `5ca4390` removes the override and explicitly sets `chromiumSandbox: true` because Playwright otherwise disables it by default. Final baseline screenshots and pass counts below come from the subsequent sandboxed runs.

## Scenario results

[Workflow receipt](2026-10-02-milestone4-browser-qa/receipts/workflow-dfc1fb.json): **10/10 checks passed**, 18 responsive/a11y snapshots. [Persistence receipt](2026-10-02-milestone4-browser-qa/receipts/persistence-workflow-dfc1fb.json) includes reports, proposals, tasks and unchanged parent digests.

| Scenario | Result and evidence |
| --- | --- |
| Empty/valid upload | Empty form cannot submit. Keyboard Enter opens the named native file chooser; adding the synthetic text and prompt enables submission. |
| Upload → graph readiness | Real upload produces a saved filename and `graph_completed` project/task through explicitly substituted ontology/graph services. UI continues to environment setup. |
| Scenario → simulation | Seeded persona/configuration render; preparation and simulation navigation work; completed synthetic rounds are shown. |
| Simulation → report | Start report control navigates through the intercepted root response to the explicitly seeded report. Visible warning says no simulation has run. |
| Proposal/source review | Actual proposal endpoint returns a reviewable draft; source excerpt, attribution, model-check warning and provenance hashes remain visible. Keyboard Enter expands claim and source details. |
| Stale source | Changing the original fixture source yields real acceptance HTTP 409, “Sources changed”, and disabled Save. Keeping the original is available. |
| Unsupported section | Drafting the unrelated contracts section yields “Changes required”/“Blocks saving”; Save is disabled. |
| Duplicate save and lost response | Two immediate clicks dispatch one acceptance request. The harness lets the real acceptance publish, then loses only its browser response. Manual retry reopens the same child ID. There is exactly one child. |
| Revision reopen | Reloaded child is immutable and `needs_review`, shows its saved claim ledger and source warning, preserves the unselected section, and navigates to the original/home/Cases. Original file hashes are unchanged. |
| Loading/error/empty | Held history response displays loading; intercepted 503 displays an explicit error; Retry with empty 200 displays the explicit empty state. |

[Recovery receipt](2026-10-02-milestone4-browser-qa/receipts/recovery-dfc1fb.json): **10/10 checks passed**. A real exited owner expired after its production lease, the durable task became `failed` with `ownership_lease_expired`, the UI exposed a visible error and Retry graph build, and that retry completed under a different task ID. The interrupted-root presentation fixture exposes enabled resume controls. The suite also verifies native source choosing, field names, history focus trapping/return, hidden-panel exclusion and explicit unknown metrics. It recorded three expected axe preload warnings, zero HTTP errors and zero uncaught page errors.

The original report's missing quality/graph values and elapsed time display **Unknown**. Graph status unknown says readiness has not been established. A saved child's populated internal quality score is an application heuristic, not factual accuracy, attribution certification or forecast quality. No benchmark-quality claim is inferred from this run.

## Reproduced defects and focused repairs

[Initial browser failures](2026-10-02-milestone4-browser-qa/receipts/browser-fail-first.json): seven failed checks, one successful backend recovery check. [Before screenshot](2026-10-02-milestone4-browser-qa/baseline/before-report-375.png).

| Reproduction | Repair | Regression evidence |
| --- | --- | --- |
| At 375px the report's minimum-width panels put Save/Keep original and report controls offscreen; header controls overlapped the home label | Responsive panel stacking, wrapping header/controls, constrained content widths | Browser geometry checks and inspected screenshots at all three widths |
| Hidden graph panel remained in the keyboard focus surface | Hidden workbench/graph panels use `inert` and do not display | Browser hidden-panel assertion |
| Upload chooser was a click-only container; textareas lacked explicit accessible names | Native named source-file button and labels | Keyboard file chooser test; labelled-control checks |
| History card/dialog had no keyboard trigger, dialog semantics, focus trap or focus return | Enter/Space triggers, named modal, initial close-button focus, Tab trap, Escape and trigger restoration | Browser keyboard dialog test |
| History failure silently resembled an empty database | Separate loading/error/retry/empty states | Two fail-first component tests and browser response-state tests |
| Real recovered graph failure was present in API but had no visible error/manual retry | Visible alert, persisted failure detail and guarded Retry graph build; stop stale graph polling | Actual separate-owner expiry and UI manual retry to a different task |
| Missing metrics displayed blank `/100`, zero elapsed time and misleading graph readiness text | Explicit Unknown values and unknown-readiness message | Missing-metric browser assertions |
| Interrupted root did not expose Resume controls | Allow interrupted non-immutable roots to show existing resume controls | Internally consistent intercepted interrupted-state browser assertion |
| Full scenario screenshots exposed clipped simulation controls/timeline, and axe found low contrast | Small-screen control wrapping and auto height, timeline space, focused text-palette corrections; log regions and graph checkbox named | Repeat screenshots, geometry assertions and axe scans |
| Open history dialog had low-contrast file tag, divider/step labels, completed badge and timestamp; independent review then found footer/Close that axe omitted | Seven small modal text-palette corrections across the file tag, divider, step label, badge, timestamp, hint and Close styles | Three-width modal screenshots/axe plus explicit solid-background text contrast checks; independent source/screenshot clearance |
| Root generation transport retries had no persistent request identity | Allocate one request key before retry; preserve a caller key and input object; new manual call gets a new key | Fail-first two-case Vitest regression, then passing component suite. Backend deduplication is coordinator-owned |

The interrupted-state test itself required two corrections: set both `status` and `effective_status` coherently, and match the rendered uppercase label. These were test-fixture defects, not further application failures. A later 1500ms file-chooser observation timed out once; its observation window was increased to 5000ms with the same keyboard action/assertions. The final sandboxed repeat passed.

## Additional modal review and scanner limits

The earlier 18 stage snapshots were clean; they did **not** include an open history modal. A later modal scan reproduced six low-contrast nodes at 375px ([initial modal receipt](2026-10-02-milestone4-browser-qa/receipts/modal-axe-fail-first.json)). Expanded 768px/1440px scans caught the badge and timestamp ([receipt](2026-10-02-milestone4-browser-qa/receipts/modal-tablet-desktop-fail-first.json)). Those fixes produced clean axe violations at `0a3911b`; its workflow/recovery receipts are retained as **superseded standalone evidence**, not final clearance.

Independent review then identified the visible footer hint and Close glyph, both 2.5388:1 on white, despite axe reporting zero violations. A supplementary fail-first check measured every visible completed-fixture modal text node and found those two failures at all three widths ([text receipt](2026-10-02-milestone4-browser-qa/receipts/modal-text-fail-first.json)). The final `dfc1fb` receipt retains axe's incomplete entries rather than dropping them. Its supplementary check measures text color against composited solid backgrounds, omitting decorative icons that repeat adjacent labels. It covers **23 text nodes at each width**, all passing their normal/large-text thresholds; the footer and Close now measure **5.3799:1**. This narrow fixture check is not a general CSS or accessibility auditor.

The independent reviewer inspected final source and all three after screenshots and cleared this bounded modal correction before the replacement freeze. In-progress/not-started history badge variants, other file-type badges, and other dialogs were not exercised; no broader palette/WCAG claim is made.

## Visual and accessibility evidence

New baseline screenshots: [home 375](2026-10-02-milestone4-browser-qa/baseline/home-375.png), [home 768](2026-10-02-milestone4-browser-qa/baseline/home-768.png), [graph 1440](2026-10-02-milestone4-browser-qa/baseline/graph-ready-1440.png), [scenario 375](2026-10-02-milestone4-browser-qa/baseline/scenario-ready-375.png), [simulation 375](2026-10-02-milestone4-browser-qa/baseline/simulation-completed-375.png), [source card 375](2026-10-02-milestone4-browser-qa/baseline/source-inspection-375.png), [proposal 1440](2026-10-02-milestone4-browser-qa/baseline/proposal-review-1440.png), [saved revision 768](2026-10-02-milestone4-browser-qa/baseline/saved-revision-768.png). The baseline directory includes all six stage captures at all three widths, plus stale, unsupported, save-error and history states. Final open-dialog screenshots: [375](2026-10-02-milestone4-browser-qa/baseline/history-dialog-375.png), [768](2026-10-02-milestone4-browser-qa/baseline/history-dialog-768.png), [1440](2026-10-02-milestone4-browser-qa/baseline/history-dialog-1440.png).

Screenshots were opened and visually inspected, including source cards, wrapped buttons, header navigation, simulation text, and saved revision warnings. Final measured screenshots had no horizontal page overflow or offscreen controls. Scrollable desktop report panels intentionally require scrolling to later content. Their current scroll position is visible in the source-review capture.

Axe 4.10.3 ran WCAG 2 A/AA, 2.1 AA and 2.2 AA tag checks across all 18 stage/width snapshots and three completed-modal widths with **zero reported violations**. The modal still has one incomplete contrast rule entry at each width, retained for review and supplemented by the explicit text measurement described above. Keyboard checks cover the source chooser, history modal/focus loop/Escape return, source details, visible focus outlines and exclusion of hidden panels. These results are bounded: no screen-reader session, cross-browser/device matrix, or exhaustive keyboard review of graph-node/edge canvas actions was performed. They do not establish general WCAG conformance. Dark mode has no exercised application setting.

## Console, network and performance

The complete workflow had **zero uncaught browser page errors**, but intentionally was not a zero-console-error run. The receipt preserves 29 warning/error messages: 18 axe preload warnings during the external-font-blocked scans, one diagnostics warning, and 10 logged errors associated with deliberate/unavailable requests.

Expected non-200/transport cases:

- `/api/simulation/sim_synthetic/diagnostics`: 404 because the synthetic run has no real diagnostics route/artifact; this is a fixture limitation.
- Stale proposal acceptance: real 409 conflict.
- One successful acceptance response deliberately aborted after publication to test a safe manual retry.
- History list: deliberately injected 503 before a successful Retry.

No other API HTTP error was observed in the workflow receipt. The recovery suite records console, HTTP and uncaught errors separately.

The last-page laboratory sample was LCP 124ms, CLS 0.000118 and recorded interaction durations [32, 32, 32]ms. This small headless synthetic sample is not field Core Web Vitals and does not establish representative INP or production performance.

## Reproduction

Run from the selected checkout using independent dependencies:

```sh
npm ci --prefix frontend --ignore-scripts
(cd backend && UV_PYTHON=3.11 uv sync --frozen --no-dev)
npm install --prefix /tmp/crowdlens-ecc-browser-tools --no-save --no-package-lock --ignore-scripts playwright-core@1.55.1 axe-core@4.10.3
npm --prefix frontend test
npm --prefix frontend run build
backend/.venv/bin/python backend/scripts/smoke_ecc_browser.py --synthetic --output-dir /tmp/crowdlens-ecc-browser-workflow-fresh --port 18746
```

In another terminal, after the harness emits its URL:

```sh
ECC_BROWSER_URL=http://127.0.0.1:18746 ECC_BROWSER_OUTPUT=/tmp/crowdlens-ecc-browser-workflow-fresh-ui node frontend/tests/ecc-browser-workflow.mjs
```

Stop that harness with Ctrl-C. Start **another fresh harness/output directory** for recovery; both suites intentionally persist proposal state and must not reuse the same seeded database:

```sh
backend/.venv/bin/python backend/scripts/smoke_ecc_browser.py --synthetic --output-dir /tmp/crowdlens-ecc-browser-recovery-fresh --port 18747
ECC_BROWSER_URL=http://127.0.0.1:18747 ECC_BROWSER_OUTPUT=/tmp/crowdlens-ecc-browser-recovery-fresh-ui node frontend/tests/ecc-browser-regressions.mjs
```

The last two commands run in separate terminals. Both scripts default to tooling at `/tmp/crowdlens-ecc-browser-tools` and Chrome `/usr/bin/google-chrome`; override with `ECC_BROWSER_TOOLS`/`ECC_CHROME`. The harness supports `--port 0` and emits the chosen loopback URL. Recovery waits for the real approximately 30-second ownership lease; it does not shorten production timing.

Frontend validation: **12 Node tests and 20 Vitest component tests passed**, build passed, `git diff --check` passed. [Tests](2026-10-02-milestone4-browser-qa/receipts/frontend-tests.log), [build](2026-10-02-milestone4-browser-qa/receipts/frontend-build.log), [history fail-first receipt](2026-10-02-milestone4-browser-qa/receipts/history-fail-first.log).

## Remaining boundaries

- Real local generation/extraction/simulation/report output was unavailable and was not downloaded or replaced with hosted inference. No model-output quality conclusion follows from these deterministic scripts.
- Real Neo4j, network/provider failures, auth, multi-user deployment, screen-reader behavior, graph canvas keyboard access and exhaustive navigation beyond the requested review workflow remain outside this browser receipt.
- A new screenshot baseline exists; historical visual-regression success cannot be claimed.
- The earlier combined candidate `3d8ba0e` was superseded by the modal corrections. Final replacement freeze: **`242b8999044e33c8c3217df857c06401f3efbba3`**, tree `39753400064fe764b98152c2c0204005f874a9c1`. Specialist C owns the independent clean-environment rerun of both sandboxed suites on that exact candidate. Its [Milestone 5 release-verification report](2026-10-02-milestone5-release-verification.md) provides the combined-SHA result/evidence. Standalone `dfc1fb` results above do not substitute for that rerun; this report does not assert the combined result before receipt.
