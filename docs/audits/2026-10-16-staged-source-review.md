# Staged review of large stored source sets

Large source sets can now proceed beyond the single drafting packet. The draft
still uses bounded retrieval and retains its existing claim, source, conditional
excerpt, summary and audit checks. Before acceptance, every original stored
passage must additionally pass a staged check against the proposed section and
selected summary for omissions, contradictions and unresolved context.

Policy `evidence-draft-v16-staged-source-review` applies only to this large-source
path. Existing small-source and historical policy behavior remains unchanged.
Independent document inventory is still required. The 2,000-passage / 8,000,000
character corpus ceiling remains enforced; staged review does not silently admit
truncated or missing source material.

Each batch contains at most 30 windows and 60,000 source characters. Originals
longer than 12,000 characters use overlapping windows with a 400-character
overlap. Hashes and exact intervals bind every receipt to its frozen source and
the proposed text. Overlap does not establish semantic completeness: unresolved
boundary context must remain unverified.

A successfully audited draft waits in `review_pending`. **Review next source
batch** explicitly admits one step under the existing workflow allowance and
three-minute step deadline. Reloads and reads never start model work. Progress
survives reloads; duplicate continuation requests cannot start a second step.
Usage accumulates across steps, and continuation does not renew request, time or
spending limits. Failed or interrupted workers retain their receipts but cannot
accept or automatically retry; a new proposal is required after such failure.

Each window needs exactly one valid model judgment. Missing, duplicated, foreign,
adverse or unverified judgments block the proposal. Acceptance recomputes the
complete interval coverage and checks every successful batch against saved
diagnostics, current sources, parent identity and the frozen proposed text.
Changing sources, the parent or the model prevents continuation. Originals are
preserved; successful acceptance creates a separate revision requiring review.

## Validation

- Full `UV_PYTHON=3.11 pnpm check` passed under Node 22.13.1: 1,043 backend
  tests, 12 frontend unit tests, 96 component tests and the production build.
  Lint and typecheck scripts are not configured.
- After fixing the CodeRabbit retry finding and retaining earlier warnings, 61 affected backend tests passed,
  including API continuation, quota exhaustion and unchanged checkpoints when
  the source service is temporarily unavailable.
- Built-app browser checks used a disposable local server, fictional sources
  and deterministic model responses. Pending proposals could not save; progress
  survived reload; explicit steps reached full coverage; acceptance created and
  reopened a separate revision while preserving the original. Desktop and
  375-pixel mobile inspection passed without horizontal overflow. One browser
  assertion expected a post-save link; the app correctly navigated immediately
  to the new revision, and direct state/reopen checks confirmed success.
  Screenshots use fictional fixtures: [pending mobile review](evidence/2026-10-16-staged-source-review/pending-mobile.png)
  and [completed desktop review](evidence/2026-10-16-staged-source-review/complete-desktop.png).
- Private, local document validation used a 429-page, approximately 30 MB PDF.
  Production extraction, including local OCR, produced 493,521 characters and
  442 page-scoped passages. All 15 batches were processed through the saved-step
  service with deterministic review substitutes. Complete interval coverage
  passed; missing-window and missing-receipt cases failed closed. The PDF hash
  was unchanged, no production stores were used, and no network/provider calls
  occurred. The input, extracted text, scripts and detailed receipts remain
  outside the repository.

These tests verify accounting, persistence and acceptance boundaries, not legal
accuracy, extraction fidelity, model quality or factual completeness. No real
model reviewed the private PDF. A provider-backed assessment requires a separate
authorized allowance. This audit does not claim deployment to the running app.
