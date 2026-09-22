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

Independent whole-change review and resulting corrections are recorded below when completed.
