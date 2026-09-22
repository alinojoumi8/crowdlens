# Evidence-first reports verification — 2026-09-21

Implementation base: `b8d7a823970babd2757cd95e3ddce384acaf001e`. Worktree branch: `codex/evidence-first-reports`. The revised design and implementation plan were committed before implementation. The desktop accepted the requested GPT-6 Astra / low reasoning continuation setting.

## Automated checks before independent review

- Backend baseline: 251 tests passed using Python 3.11.
- Full project check: 330 backend tests, 12 frontend unit tests, 12 component tests, and production Vite build passed.
- Credential-neutral copy: `/tmp/mirofish-evidence-clean-es9zs75c/repo`, no root/backend `.env`, provider credentials unset, a fresh Python 3.11 environment with the frozen lock: 330 passed in 16.66 seconds.
- Python 3.13 could not build the existing pinned tiktoken dependency; checks explicitly use `UV_PYTHON=3.11`. No dependency upgrade is included.
- Proposal API tests wait for observed completion and join worker threads. An earlier one-second test wait failed on a slower filesystem despite later successful worker completion; no production deadline was relaxed.

Focused regressions cover malformed model fields, premise cycles and unknown premises, invented sources, quote/window hashes, summary spans, idempotency, two-worker capacity, process-death recovery, transport retry overrides, case/version retrieval, ledger-before-prose ordering, complete audit coverage, immutable publication, stale sources/parents, crash-after-rename recovery, tombstones, root-only lookup, legacy revision mutation guards, escaped excerpts, late navigation responses, duplicate acceptance, and polling teardown.

## Observed browser and filesystem behavior

The disposable harness ran at loopback port 40017 with artifact root `/tmp/mirofish-evidence-smoke-20260921`. It served the real built frontend and report blueprint; source storage and model responses were synthetic, and real provider HTTP calls were disabled.

1. Opened `report_synthetic` and selected **Draft with sources** for Hearing.
2. Observed original Thursday wording, proposed attributed Friday wording, and separately displayed summary edits preserving “Other issues remain open.”
3. Expanded attribution and source provenance. The full and window SHA-256 values matched `701245271bacf452d6419c8567dd04d08185a6837d6cd1d60fb82c9243b464f8`, with offsets 0–56.
4. Saved revision `report_204797d98be44b58b3fe0c815dc9058f`, reloaded its URL, and observed Needs review, persisted claim ledger, parent/original/proposal links, and disabled section rerun controls. The unrelated-contract section and unavailable forecast remained inherited.
5. Followed **Parent report** and observed the original Thursday summary and section still present.
6. Requested the unrelated-contract section. It reached blocked/no-original-evidence with Save disabled; **Keep original** persisted rejected state.
7. Created a fresh Hearing proposal, changed only the harness source corpus, and attempted acceptance. The API rejected it as stale; the UI displayed the source-change explanation and disabled saving after status refresh. A regression then added immediate disablement on that 409 response.
8. `/__synthetic/evidence` wrote `browser-evidence.json`: parent hashes unchanged, exactly two reports (parent plus accepted revision), and proposal states accepted/rejected/stale. Stale acceptance created no extra report.

## Quality boundary

The offline evaluator ran six synthetic paired fixtures. It reported zero independently reviewed pairs and null proposed accuracy, correctly excluding synthetic/unlabeled judgments from quality denominators. These checks establish workflow mechanics, not accuracy or efficacy on real cases. No private inputs or paid/live model evaluation were used, and no Jev promotion/configuration was changed.

## Independent review and corrections

One fresh reviewer examined the frozen range `b8d7a82..018c87c` against the plan and design. The verdict at that head was request changes: no critical findings, six important findings, and one minor finding. The final patch addresses all seven; no second independent review is claimed.

| Finding | Correction and regression evidence |
| --- | --- |
| Low-level writers bypassed immutable revisions | Outline, section, progress, assembly, and supplied-ID generation now reject immutable revisions before writes. Tombstoned IDs are also guarded. Four low-level writer regressions and a generation regression passed. |
| Leaf-file symlinks escaped artifact containment | Complete file paths, including legacy paths and recovery manifests, are validated. A metadata symlink regression reproduced the old read and now rejects it. |
| Interrupted acceptance stranded the UI | Reloaded `accepting` proposals offer an explicit same-digest retry. Pre-publication rejection is allowed only while holding both leases and confirming no committed target. API tests cover failures before and after publication; component and browser checks cover recovery after reload. |
| Cancellation/deadlines discarded observed usage | Phase checkpoints and state-independent telemetry persistence retain completed and late-response usage/timing without reviving proposals. Watchdog/rejection regressions retain both observed calls; late Jev usage is recorded before fencing. |
| Lexical evidence was cut from model windows | Matching term spans anchor windows even for nonliteral, case-insensitive queries. Window boundaries preserve intersecting literal quotes; clipping/candidate limits are disclosed. Late-source and second-quote regressions passed. |
| Late GET responses undid terminal UI actions | Acceptance/rejection invalidate older status reads before starting. Regressions cover a delayed ready response arriving after each successful mutation. |
| Deletion conflicts returned HTTP 500 | The existing endpoint now translates typed proposal errors. An occupied report returns 409 with a stable error and no traceback. |

The failing regressions were observed before their corresponding fixes. API acceptance tests explicitly await worker cleanup, since observing a ready record may precede release of its operation lease. This retains the production concurrency protection.

Final harness-log inspection exposed a related pre-existing storage race: simultaneous writability checks used the same process-ID probe filename. One request could delete another's probe, falsely report the configured root unwritable, and route that operation to fallback storage. A two-thread barrier regression with distinct primary/fallback roots reproduced the split. Exclusive temporary probe files now prevent the collision. The report persistence and quality suites passed all 27 tests after this correction; final project and clean-copy results below include it.

## Final verification

- Focused backend verification: 56 passed.
- `UV_PYTHON=3.11 npm run check`: **346 backend tests**, **12 frontend unit tests**, **16 component tests**, and production Vite build passed (3.14 seconds). Log: `/tmp/evidence-final-project-check.log`.
- Fresh credential-neutral copy: `/tmp/mirofish-evidence-final-clean-i_tikmvh/repo`; root/backend `.env` absent, credential environment keys unset, new Python 3.11 environment, frozen dependency lock. **346 passed in 20.93 seconds**, exit 0. Log: `/tmp/evidence-final-clean-check.log`.
- Final browser recovery: a separate temporary harness at port 44875 injected one interruption immediately after atomic publication. Reload showed **Save needs recovery** and **Retry saving revision**. Retrying opened `report_919c91ac825a43dc8082c41cc678f24d`, still Needs review, with immutable controls. The filesystem evidence at `/tmp/mirofish-evidence-recovery-final/browser-evidence.json` confirms unchanged parent hashes, one accepted proposal, exactly one child revision, and only the original three synthetic model calls.
- `git diff --check` passed. The feature remains in its local branch/worktree; no merge, push, deployment, private-input evaluation, or Jev promotion was performed.

All actionable correctness findings from the independent review have targeted corrections and passing regressions. Independent quality on real cases remains unmeasured as described above.
