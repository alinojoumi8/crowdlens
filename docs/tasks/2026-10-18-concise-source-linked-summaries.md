# Concise, source-linked revised summaries

New full-section proposals ask for a short, claim-linked summary instead of copying complete ledger claims. The replacement passages have a combined 600-character ceiling and must be nonempty single-paragraph prose. The prompt requests one to three sentences; the deterministic boundary is characters, not sentence parsing. Full conditional source extracts remain intact in the ledger and section, and every summary edit still requires the existing source-first audit.

The new format is digest-bound and immutable once finished. Acceptance and audit-only recovery recheck its limit; retained legacy proposals preserve their original contract. Frozen supporting sources are resolved from ledger citations and analysis premises. Saved reports expose filename/page links that open and focus the corresponding excerpt. Markdown downloads include summary references and escaped frozen excerpts. Untouched linked passages retain their references across later revisions, with positions shifted after preceding edits. Edited passages receive new references.

## Verification

- Reproduced the former page-length-summary behavior with failing regressions before implementation.
- `UV_PYTHON=3.11 pnpm check`, using Node 22: 1,073 backend tests, 12 frontend Node tests, 106 component tests, and production build passed (1,191 tests total).
- A synthetic 1,457-character guarded source page produces a 55-character summary while retaining the full page in the section and passing through the source audit. This is a fixture contract check, not evidence of live model quality.
- Rechecked the concise limit at acceptance; audit-only retries preserve the new format. Source-chain validation, Markdown escaping, inherited link offsets, reload, focus and safe source rendering are covered.
- Desktop (1440×1050) and mobile (390×844) browser checks passed. The source link opened and focused its frozen excerpt; mobile had no horizontal overflow. Saved revision download matched the persisted Markdown byte for byte.
- Synthetic browser fixture has no graph-quality endpoint and no initial progress artifact; those unrelated requests returned 404. The source-link, save, reopen and download operations succeeded.
- No configured lint or typecheck scripts. Hosted CI was not run.
- CodeRabbit initially found one major issue: links were lost when later revisions left a linked passage unchanged. Fixed with position-aware inheritance and regression coverage. Follow-up CodeRabbit review completed on all 13 code/test files with zero findings.

## Provider and retained data

No MiniMax requests were made or authorized by this change. The live workflow remains stopped at 39/60 total requests, zero in flight, with one historical unknown-usage receipt. Existing immutable reports are not rewritten; the concise format applies to new proposals.

Private validation evidence: `/home/ali/.local/state/crowdlens/concise-summaries-20261018/`.

## Next

Correct the workflow allowance banner so historical unknown usage is displayed separately from in-flight requests. Then finish the canonical-repository review and hosted CI/integration. A live MiniMax check of the new summary prompt requires a newly authorized allowance; it has not been run.
