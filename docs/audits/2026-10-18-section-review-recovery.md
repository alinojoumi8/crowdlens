# Full-section summary review and audit recovery

Implemented on 2026-10-18 after the bounded MiniMax acceptance run exposed an unmapped summary passage and a provider audit timeout.

## Full-section review

When the selected section does not appear exactly once in the summary, a new proposal requires the operator to choose the exact summary passage that may change. The passage must be nonempty, unique in the current summary and at most 2,000 characters. Invalid or missing selections are refused before model work starts.

The selection is frozen into the proposal digest and revalidated at acceptance. It authorizes an edit boundary only. Source completeness, claim grounding, paragraph review and summary assessment still have to pass. A failed factual audit cannot be overridden by selecting text. Raw section content is used for automatic matching, excluding the heading added for display.

Acceptance creates a separate revision. The original report, unselected summary text, other sections and forecast remain unchanged. Inherited material remains unverified, and the revision remains `needs_review`.

## Explicit audit recovery

An eligible failed audit exposes **Retry saved audit** when its retained inputs can be verified. The endpoint is `POST /api/report/<report_id>/evidence-proposals/<proposal_id>/retry-audit`, with `request_key` and the current `recovery_digest`.

Recovery copies the frozen checkpoint into a new proposal and runs only the unfinished audit. It preserves the failed proposal and revalidates the parent, sources, draft, ledger, summary boundary and model. Corrupt checkpoints and changed inputs fail closed. Legacy timeout records are supported when their retained diagnostics and all other checkpoint inputs remain valid.

Previously completed audit responses are replayed in order, including the original response before any structural correction. A later correction cannot erase an earlier adverse judgment. GET, reload and reopening never start model work. Retrying a request after a network error uses the same idempotency key; a definite checkpoint refusal clears it. A direct link to another proposal cannot reuse a cached retry belonging to the previous proposal.

Recovery uses the existing workflow allowance, request ceiling and Stop controls. Unknown delivery or usage remains counted. No allowance is renewed automatically, and retrying may incur another provider charge. This recovery path applies to the draft audit; it does not restart staged source-review batches.

## Verification

- `UV_PYTHON=3.11 pnpm check` under Node 22 passed: 1,064 backend tests, 12 frontend Node tests, 103 Vue component tests, and the production build.
- `docker compose config --quiet` passed. Lint and type-check scripts are not configured.
- Regressions reproduce invalid/ambiguous selection, stale or corrupt checkpoints, audit timeout, deadline expiry after a structural correction, refusal cleanup contention, changed model, request-key recovery, navigation and stopped allowances.
- Browser verification used the actual built Vue frontend and Flask API with a synthetic provider. It exercised selection, a forced audit timeout, checkpoint refusal and refresh, retry, save, reopen and Markdown download. The parent, forecast and unselected section stayed unchanged. The downloaded Markdown matched the saved revision. Mobile width was 390 pixels with no horizontal overflow.
- All five CodeRabbit findings (one major, four minor) were reproduced and fixed. The final review of all 14 changed code and test files completed with zero findings. This includes preserving adverse audit judgments and keeping retry identity tied to the displayed proposal. Detailed review output is retained in the local acceptance evidence; this documentation received a focused diff review.

No MiniMax calls were made for this implementation. Synthetic browser results verify workflow behavior, not provider quality or factual correctness. Hosted CI and live MiniMax acceptance of these changes remain unrun.

## Next acceptance step

With a new explicit time allowance and the existing 60-request total ceiling, retry the retained MiniMax audit and create a full-section proposal with an explicit summary selection. Verify the resulting findings, save only an eligible revision, then reopen and download it. Preserve any adverse findings and unknown usage. Remote integration and hosted CI remain separate delivery steps.
