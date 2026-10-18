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

No MiniMax calls were made during implementation. Synthetic browser results verify workflow behavior, not provider quality or factual correctness. Hosted CI remains unrun; the subsequent live acceptance is recorded below.

## Live MiniMax acceptance

On 2026-10-18 the user authorized another 1,800 seconds with the same 60-request total ceiling. The existing fictional Cedarbrook report was used. The run began with 36 requests consumed and stopped after 133.52 seconds at 39 total, with zero in flight. All three new requests returned HTTP 200 with usage receipts. The one earlier unknown-usage attempt remains counted; no new unknown-usage attempts occurred.

- **Timeout recovery:** one new audit request completed from the saved draft. The failed predecessor and its drafting diagnostics stayed unchanged. Reposting the same retry request returned the same proposal without another provider call. The recovered audit correctly blocked saving because the old summary was unmapped and its simulation/forecast claims were unverified against the original source.
- **Full-section review:** the current one-sentence summary was selected explicitly in the UI. Drafting and audit used two requests. Source coverage was complete, the summary audit returned consistent, and no blocking findings remained. The proposal was saved through the UI as a separate immutable revision, reopened and downloaded.
- **Preservation:** the original report, structured forecast and unselected sections remained unchanged. All 5,766 pre-existing artifact files were unchanged; the workflow/task database changed as expected. Its original 36 request records were preserved. The revision remains `needs_review` and visibly labels inherited material.
- **Download and UI:** the browser download matched both the API download and persisted Markdown, SHA-256 `20016215947565d1d1c48a7a9f1e363db09fa5cd7f588fe77ec1b1d5f01d9127`. Desktop and 390-pixel mobile views were checked; mobile had no horizontal overflow.

These results validate the live workflow and its refusal behavior, not factual certification or a general model-quality benchmark. A separate quality gap remains: the replacement summary is the entire 1,478-character source-page excerpt, rather than a concise summary.

## Next work

Produce concise, source-linked revised summaries while preserving the existing edit boundaries and factual gates. Then correct the allowance banner's unknown-usage count. Remote integration and hosted CI remain separate delivery steps.
