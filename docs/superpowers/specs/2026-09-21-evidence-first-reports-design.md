# Evidence-first report drafting and review

Status: revised after review; implementation authorized by the user's instruction to finish the plan, then implement with GPT-6 Astra at low reasoning. Implementation has not started in this document's revision.

## Agreed outcome

The user approved evidence-first report generation with a review-and-correct workflow. The first release covers one selected section of an existing report and the related statements in its report summary. A reviewer can inspect original evidence, compare proposed changes, and save an accepted proposal as a separate report revision. The original report remains accessible.

Success means more accurate, attributable statements and less review work, measured against the current pipeline. A larger count of model-labeled supported claims is not sufficient evidence of improvement. Source support establishes what a document says; it does not establish the truth of an allegation.

MiniMax remains the drafting model through the existing LLM client. Jev modes and promotion policy do not change. The workflow must function with Jev off, and shadow results remain advisory. No private-case live evaluation or additional external embedding provider is introduced by this design.

## Current implementation and constraints

- `backend/app/services/report_agent.py`: `ReportSection` stores evidence cards and post-draft claims/checks. `ReportAgent._check_report_claims` reconstructs associations from completed prose. `regenerate_section` currently rewrites the existing report. `ReportManager.save_report` writes multiple files directly, so it cannot be reused as an atomic revision publication boundary without staging.
- `backend/app/services/source_tracing.py`: `SourceIndex` admits only original chunks with matching graph, case, and case version, bounded to 2,000 chunks / 8 million characters. It currently ranks lexical matches and selects four candidate chunks per claim.
- `backend/app/storage/neo4j_storage.py`: `get_source_chunks` already provides scoped original episodes and a truncation sentinel. Existing node/edge search is not a substitute for original-document evidence.
- `backend/app/services/evidence_verifier.py`: exact quote/provenance checks and semantic judgments already exist. Candidate associations and chosen citations must remain distinguishable.
- `frontend/src/components/Step4Report.vue` and `ClaimEvidence.vue`: report sections and summary already expose expandable source checks. `ReportView.vue` already follows report IDs in the route.
- `backend/app/models/task.py`: existing task persistence and progress APIs can support bounded asynchronous proposal generation.

These boundaries were inspected on `codex/jev-decision-services` at commit `737cf03`. The source-tracing and interview audit documents describe prior pilots, not new validation performed for this design.

## Approach decision

Three approaches were considered:

1. Improve retrieval after drafting only. This is smaller, but leaves the proposed facts unconstrained until after prose exists.
2. Add an opt-in evidence-first section proposal and revision workflow. This is selected: it exercises the entire intended flow while keeping its output directly comparable to the existing report.
3. Replace generation for every report and section immediately. This has a larger regression surface and makes it harder to attribute quality changes.

The first implementation adds the selected workflow to existing saved, terminal reports with an explicit graph/case/version scope. It does not change the default full-report generation route, run new simulations, merge entities, modify forecast probabilities, or revise unselected sections. Those are independent future decisions.

## User flow

1. Open a completed or needs-review report and select **Draft with sources** on a section.
2. The server snapshots the report and its original source corpus, then creates a background proposal task. The UI shows retrieval, claim planning, drafting, and validation progress. Polling only reads persisted state.
3. Review the proposed section beside the original. Inspect its claim ledger, exact excerpts, source locations, attribution, retrieval limits, and warnings. Review related summary changes separately in the same proposal.
4. Accept the section and summary changes as one unit with **Save as new revision**, or reject the proposal with **Keep original**. V1 does not allow partial acceptance or arbitrary inline editing that could detach prose from the ledger.
5. Saving opens a new report URL with links to the parent report and the proposal. Reloading either report preserves its content and review state. Rejecting a proposal does not delete its audit record.

An incomplete proposal or one with invalid identifiers, mismatched hashes, malformed citations, or unlinked factual prose cannot be accepted. A structurally valid draft can still have unresolved semantic judgments; it remains visibly needs-review after acceptance. Human acceptance records a wording decision, not a factual certification.

## Evidence retrieval

Load and freeze the admitted original source corpus with the existing strict scope and size limits. Derive a corpus digest from scope, the truncation flag, source IDs, full original-text hashes, and available locator metadata. Missing scope or no original evidence produces an actionable unavailable result without drafting.

Build up to six bounded retrieval queries from the section title, description, existing named entities, and explicit quotations. The previous prose is a question and comparison input, never evidence. Combine:

- Exact phrase/quotation matches and lexical ranking over the complete admitted corpus.
- Semantic similarity using existing compatible original-episode vectors where available; otherwise optional local Ollama embeddings with auto-pull disabled and bounded work. Do not send the new source corpus to a remote embedding service automatically.
- Neighboring chunks from the same document and case version when reliable chunk ordering exists. Missing ordering must not be replaced by guessed adjacency.

Use reciprocal-rank fusion for lexical/semantic lists with deterministic ID tie-breaking; retain exact quotation hits as explicit candidates. Record component scores, retrieval method, missing-vector coverage, and truncation. If semantic retrieval is unavailable, continue lexically and display the limitation. Relevant contradictory material remains in the candidate pool; no support-only filtering.

Initial operational bounds: 30 candidate chunks including neighbors, at most 60,000 characters in the drafting evidence packet, 30 planned claims, three selected citations per claim, and at most 200 new local document embeddings per proposal. Exact matching uses the admitted original text even if a displayed context window is smaller. Each window retains its full-chunk hash, window hash, and character offsets; quote presence is checked against the actual cited window. Budget exhaustion is recorded, never presented as an exhaustive search.

## Persisted claim ledger and drafting contract

Persist the plan before requesting section prose. The server assigns IDs; model output may only refer to IDs actually supplied to it. Ledger entries contain:

| Field | Meaning |
| --- | --- |
| `claim_id`, `schema_version` | Stable ID within an immutable proposal and schema version |
| `text`, `kind` | Proposed statement; `source_statement`, `attributed_allegation`, `analysis`, or `simulation_observation` |
| `attribution` | Named speaker/author/party when the statement requires attribution |
| `citation_ids`, `premise_claim_ids` | Selected original citations or the declared premises for analysis |
| `quote` | Optional exact source quotation; no implicit normalization |
| `scope` | Graph, case, and case version derived by the server |
| `checks` | Separate deterministic findings, optional model judgments, and unresolved reasons |

Source references retain document/episode identity, original text/hash, available page/paragraph/chunk location, window offsets, and retrieval provenance. Location fields that do not exist stay unknown. Candidate IDs are stored separately from selected citations.

Source statements and attributed allegations require original citations with successful deterministic provenance checks. Simulation observations require an existing recorded simulation artifact and are excluded from source-fact verification; V1 does not generate new simulation observations. Analysis must link to nonempty ledger premises and be explicitly labeled as analysis. Reject unknown IDs, self-reference, and cycles. Every premise path must terminate at a source claim with valid provenance or a referenced recorded simulation artifact. Propagate unresolved, contradicted, and conflicting premise states to dependent analysis; an analysis label cannot upgrade evidence quality. Model-selected types and attribution still require review; schema validity cannot prove their correctness.

The prose response is structured as ordered paragraphs containing text, kind, and ledger IDs. Rendering assigns citation markers from validated IDs. Missing/unknown IDs, invalid quotations, unsupported factual additions detected by the post-draft association pass, and uncovered prose are retained as findings and prevent acceptance until a fresh proposal resolves them. Do not silently delete a failed claim or attach a nearby citation to conceal the failure. Model auditing can miss claims; the UI must not claim exhaustive verification.

An inability to find evidence is rendered as a limited statement about the searched corpus, not a claim that no evidence exists. The claim ledger records the gap. Valid citations can still be semantically insufficient, contradicted, or conflicting; expose those outcomes and keep the report needs-review.

## Summary handling

The report summary describes the whole report, so rebuilding it solely from one section would discard unrelated findings. Generate bounded replacement spans only for summary statements affected by the selected section. Each edit carries the exact original span and offsets, replacement text, and ledger references. The server verifies nonoverlap and exact span matches, applies edits deterministically, and keeps unrelated summary text byte-for-byte.

If no summary span is affected, preserve the summary and record `summary_unchanged`. If a safe edit cannot be expressed, return a review-blocked proposal rather than replacing the whole summary. Existing checks for changed text are invalidated. Unchanged summary checks remain inherited evidence about the parent snapshot, not newly verified findings.

## Proposal, revision, and persistence model

Add `report_revisions.py` for proposal/revision storage and transitions, `evidence_drafting.py` for orchestration and structured drafting, and a focused original-source retrieval module. Keep the large report agent focused on compatibility serialization and shared validation. Reuse existing source checks without changing global evidence thresholds or aggregation policy.

Proposal states: `queued`, `running`, `ready`, `blocked`, `failed`, `accepted`, `rejected`, `stale`. Each proposal stores the parent report ID and content digest, selected section index, scope, source digest, frozen before/after content, ledger, checks, model/policy identity, usage, phase timings, limitations, and the accepted revision ID when present. Raw excerpts stay with private report artifacts, not generic logs or tracked evaluation fixtures.

Store proposals under the existing report artifact root in a dedicated proposal subtree; report listing must exclude that subtree. Validate every report/proposal identifier and resolve paths beneath the configured root. A server-generated proposal ID determines a unique target revision ID, allowing recovery and repeat acceptance without duplicate reports.

For acceptance, validate the proposal identity and expected proposal digest, then reconcile an already-published matching revision before reading the current parent or source corpus. This recovery also works when the parent has since changed or been deleted, or the source store is unavailable. Only a proposal with no committed revision proceeds to parent/source freshness checks. A matching accepted revision returns the same report ID on every retry; a user-deleted revision returns HTTP 410 and is never silently recreated. A conflicting target identity/digest returns 409.

Legacy regeneration, resume, deletion, proposal work, and acceptance share a cross-process per-report operation lease, stored outside report folders so deletion cannot replace the lock inode. Long model operations may hold an operation lease, but not the short publication locks. After acquiring the operation lease, reload the parent; acquire the proposal publication lock next. No provider call runs while holding a publication lock. For an unpublished proposal, a changed or missing parent/source returns a stale result; an unavailable source store leaves the proposal ready with a retryable error and cannot approve the snapshot. Source validation records its checked-at timestamp; this is not a cross-store transaction or a claim that the source corpus can never change afterward.

Write the complete new report into a unique staging directory on the same filesystem, including metadata, outline, sections, markdown, ledger, and provenance. Flush files and publish via an atomic directory rename into its deterministic unused report ID. Then atomically mark the proposal accepted. If the process stops between publication and the acceptance update, retry recognizes the matching proposal ID and digest in the revision and returns that report. A conflicting existing target is an error, never overwritten. Incomplete staging directories are excluded from listing and cleaned conservatively.

The new report records `parent_report_id`, `root_report_id`, `proposal_id`, accepted timestamp, content digest, and the partial scope of this revision. It copies unselected section content unchanged. Regenerate markdown without running global rewriting passes over inherited sections. Preserve forecasts and their provenance, label them inherited, and do not record a fresh case prediction snapshot or imply a new simulation ran.

All V1 accepted revisions remain `needs_review` and their content, ledger, forecasts, and acceptance metadata are immutable. Reject legacy section regeneration and resume on revision IDs with HTTP 409 before provider calls; enforce this in service entry points as well as APIs. The UI offers a new evidence proposal on a revision and disables in-place mutation controls. Shared quality-status logic cannot promote a revision to completed. Existing deterministic validation remains active. Do not re-run inference for inherited sections on acceptance. Proposal rejection is idempotent; rejection after publication is a conflict and must first reconcile crash recovery. Deletion remains an explicit user action, writes a tombstone, and does not cascade-delete children.

Default simulation lookup selects the newest non-revision root report, ordered by `(created_at, report_id)` descending, independently of filesystem enumeration order. Generation reuse additionally filters the requested report mode/depth. Revisions are selected only by their explicit report ID or revision navigation. If all root reports are deleted, default lookup returns no root even if child revisions survive. Lists may include revisions with visible parent/root metadata, but must exclude proposal, lock, tombstone, and staging directories.

## API and UI integration

Use the existing report blueprint and response envelope. Add:

| Method and route, under `/api/report` | Contract |
| --- | --- |
| `POST /<report_id>/evidence-proposals` | Validated one-based `section_index` plus idempotency key; server derives scope; return proposal/task IDs with HTTP 202 |
| `GET /<report_id>/evidence-proposals/<proposal_id>` | Read persisted status, progress, before/after, ledger, checks, and revision link; no inference |
| `POST /<report_id>/evidence-proposals/<proposal_id>/accept` | Expected immutable proposal digest; return the same new report ID on repeated acceptance |
| `POST /<report_id>/evidence-proposals/<proposal_id>/reject` | Idempotently retain the original and record rejection |
| `GET /<report_id>/revisions` | Parent/root/revision navigation derived from persisted metadata |

Creation deduplicates retries by parent report, request key, and request content; reusing a key with different content returns 409. Validate request sizes, terminal parent status, source availability, and section bounds before inference. Return 400 for invalid input, 404 for absent/mismatched IDs, 409 for stale or incompatible transitions, and a stable unavailable error for missing dependencies. New endpoints do not return tracebacks or provider payloads.

Use one active proposal per report and an application-wide concurrency cap of two. Enforce admission with process-shared filesystem leases under the artifact root, not TaskManager's process-local cache. Reserve the report operation lease and one of two worker slot leases before publishing a queued proposal and transfer their ownership to its worker. If no slot is free, return a retryable 503 without queueing unowned work. Persisted proposal files are authoritative for polling; TaskManager records are progress mirrors only. Startup reconciliation checks queued and running proposals against their operation leases and marks abandoned work failed with reason `interrupted`. A second backend process must not interrupt a worker holding a live lease. No read request restarts inference.

Set a monotonic 180-second deadline from admitted work. Extend the existing LLM client with request-local timeout, zero-retry, and usage-capture controls for this workflow; preserve legacy defaults for other callers. Disable both OpenAI SDK retries and Anthropic transport retries for proposal calls, and pass the remaining budget to every generation, embedding, and optional evidence-verification call. Bound ledger/draft responses as well as input packets. A watchdog marks an over-deadline proposal failed; late responses cannot change it to ready or publish output. Local cancellation cannot guarantee cancellation of an already-submitted remote request; retain concurrency reservations until the actual worker exits. Acceptance is local publication with source revalidation and makes no generation call.

Add a focused `EvidenceDraftReview.vue` component, composed from `Step4Report.vue`, and API functions in `frontend/src/api/report.js`. Reuse escaped text rendering and `SafeMarkdown`. Provide keyboard-operable expanders, loading/error states, separate section/summary comparisons, explicit acceptance blockers, and parent/revision links. A request started for one report cannot populate another report after route navigation; use request identity guards and stop polling on unmount.

## Validation and delivery criteria

Implementation tests should exercise meaningful boundaries:

- Sources from another case/version, simulation dialogue used as source evidence, invented citations, mismatched source/window hashes, absent quotations, attributed allegations, and conflicting sources.
- Exact-name/quotation retrieval, semantic-only matches with injected vectors, unavailable embeddings, neighboring context, deterministic ranking, and every retrieval budget flag.
- A ledger saved before prose generation; no accepted paragraph with unknown ledger references; self-references, cycles, empty premises, and ungrounded analysis fail deterministically; unresolved premise status propagates. Malformed model output and uncovered text remain blocked; irrelevant summary text and unselected sections remain unchanged.
- Parent/source changes before publication, concurrent legacy mutation, double acceptance, accept/reject races, and a crash after publication followed by a changed/deleted parent or unavailable source store. Recovery returns the committed result; deletion of that result returns 410. Test path traversal and recovery of abandoned queued as well as running work without interrupting another live worker. Reloaded parent bytes remain unchanged by proposal creation and acceptance.
- Old reports deserialize without new fields; legacy regeneration on ordinary root reports remains compatible, but accepted revisions reject mutation. Their status and inherited forecasts stay unchanged. Test default root selection in reversed directory orders, mode/depth filtering, and deleted roots with surviving children. Jev off makes no Jev calls, shadow mode cannot promote a draft or change production decision settings, and a zero-action report gains no forecast probability.
- Transport 429/5xx/timeouts trigger no proposal retries; remaining-deadline values reach every provider; late results cannot revive failed proposals; usage records omit credentials and raw provider errors. Other LLM callers keep their existing retry behavior.
- Component/API coverage for proposal progress, escaped hostile excerpts, original/proposed comparisons, blocked/stale states, repeated acceptance, revision navigation, and route-change races.

Run focused backend and frontend tests while implementing, then `npm run check`. Verify a synthetic end-to-end browser flow from a saved report through proposal, acceptance, reload, and parent comparison. Run a credential-neutral backend suite so local provider settings cannot conceal missing-key regressions.

Create an offline evaluation harness for paired baseline/proposed sections with independently supplied labels. Report citation/quote validity, source retrieval recall, false-supported claims, critical factual errors, attribution errors, important omissions, and unresolved coverage. Include denominators and keep unlabeled examples separate. Record provider requests/tokens and phase/end-to-end latency; report monetary cost only with an explicit price schedule. Human review time requires actual timed review, not an estimate from token usage.

Synthetic fixtures prove mechanics, not domain accuracy. A private or paid live pilot remains a separate explicit run using approved inputs, with development and held-out cases separated. Release notes distinguish implemented workflow, automated checks, browser evidence, and any still-pending independent quality assessment. The existing Jev promotion gates remain unchanged.

## Implementation sequence after design review

1. Proposal schemas, immutable snapshots, persistence, and concurrency/recovery tests.
2. Scoped source retrieval, persisted claim planning, bounded drafting, and summary-span edits.
3. Validation and atomic report revision publication with backward-compatible serialization.
4. Report API, task reconciliation, and the review component in the existing viewer.
5. Offline paired evaluation, complete project checks, and the synthetic browser workflow.

This document specifies the architecture and acceptance criteria. The implementation plan is `docs/superpowers/plans/2026-09-21-evidence-first-reports.md`. The user explicitly directed automatic transition from the completed plan to implementation; no additional plan approval checkpoint is required.
