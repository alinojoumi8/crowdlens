# Evidence-first report drafting and review

Status: design for review; implementation has not started.

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

Source statements and attributed allegations require original citations with successful deterministic provenance checks. Simulation observations require an existing recorded simulation artifact and are excluded from source-fact verification; V1 does not generate new simulation observations. Analysis must link to ledger premises and be explicitly labeled as analysis. Model-selected types and attribution still require review; schema validity cannot prove their correctness.

The prose response is structured as ordered paragraphs containing text, kind, and ledger IDs. Rendering assigns citation markers from validated IDs. Missing/unknown IDs, invalid quotations, unsupported factual additions detected by the post-draft association pass, and uncovered prose are retained as findings and prevent acceptance until a fresh proposal resolves them. Do not silently delete a failed claim or attach a nearby citation to conceal the failure. Model auditing can miss claims; the UI must not claim exhaustive verification.

An inability to find evidence is rendered as a limited statement about the searched corpus, not a claim that no evidence exists. The claim ledger records the gap. Valid citations can still be semantically insufficient, contradicted, or conflicting; expose those outcomes and keep the report needs-review.

## Summary handling

The report summary describes the whole report, so rebuilding it solely from one section would discard unrelated findings. Generate bounded replacement spans only for summary statements affected by the selected section. Each edit carries the exact original span and offsets, replacement text, and ledger references. The server verifies nonoverlap and exact span matches, applies edits deterministically, and keeps unrelated summary text byte-for-byte.

If no summary span is affected, preserve the summary and record `summary_unchanged`. If a safe edit cannot be expressed, return a review-blocked proposal rather than replacing the whole summary. Existing checks for changed text are invalidated. Unchanged summary checks remain inherited evidence about the parent snapshot, not newly verified findings.

## Proposal, revision, and persistence model

Add `report_revisions.py` for proposal/revision storage and transitions, `evidence_drafting.py` for orchestration and structured drafting, and a focused original-source retrieval module. Keep the large report agent focused on compatibility serialization and shared validation. Reuse existing source checks without changing global evidence thresholds or aggregation policy.

Proposal states: `queued`, `running`, `ready`, `blocked`, `failed`, `accepted`, `rejected`, `stale`. Each proposal stores the parent report ID and content digest, selected section index, scope, source digest, frozen before/after content, ledger, checks, model/policy identity, usage, phase timings, limitations, and the accepted revision ID when present. Raw excerpts stay with private report artifacts, not generic logs or tracked evaluation fixtures.

Store proposals under the existing report artifact root in a dedicated proposal subtree; report listing must exclude that subtree. Validate every report/proposal identifier and resolve paths beneath the configured root. A server-generated proposal ID determines a unique target revision ID, allowing recovery and repeat acceptance without duplicate reports.

For acceptance, use a cross-process proposal lock, reload persisted proposal state, and recheck the expected parent/source digests. Legacy regeneration, resume, deletion, and the new acceptance path share a per-report mutation lock so a concurrent writer cannot invalidate the parent snapshot during publication. Acquire the report lock before the proposal lock in every path needing both. No provider call runs while holding these publication locks. A changed or missing parent/source returns a stale result and requires a new proposal; an unavailable source store cannot silently approve an old snapshot.

Write the complete new report into a unique staging directory on the same filesystem, including metadata, outline, sections, markdown, ledger, and provenance. Flush files and publish via an atomic directory rename into its deterministic unused report ID. Then atomically mark the proposal accepted. If the process stops between publication and the acceptance update, retry recognizes the matching proposal ID and digest in the revision and returns that report. A conflicting existing target is an error, never overwritten. Incomplete staging directories are excluded from listing and cleaned conservatively.

The new report records `parent_report_id`, `root_report_id`, `proposal_id`, accepted timestamp, content digest, and the partial scope of this revision. It copies unselected section content unchanged. Regenerate markdown without running global rewriting passes over inherited sections. Preserve forecasts and their provenance, label them inherited, and do not record a fresh case prediction snapshot or imply a new simulation ran.

All V1 accepted revisions remain `needs_review`. Existing deterministic validation remains active; a high heuristic score cannot clear that status. Do not re-run inference for inherited sections on acceptance. Proposal rejection is idempotent; acceptance after rejection returns a conflict. Deleting a parent does not cascade-delete already published child revisions.

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

Use one active proposal per report, an application-wide concurrency cap of two, and a 180-second proposal deadline with provider timeouts capped to the remaining budget and no automatic retry loops. Bound ledger and draft responses as well as input packets. Startup reconciliation marks abandoned running proposal tasks interrupted; a read request never silently restarts paid inference. Acceptance is local publication with source revalidation and makes no generation call.

Add a focused `EvidenceDraftReview.vue` component, composed from `Step4Report.vue`, and API functions in `frontend/src/api/report.js`. Reuse escaped text rendering and `SafeMarkdown`. Provide keyboard-operable expanders, loading/error states, separate section/summary comparisons, explicit acceptance blockers, and parent/revision links. A request started for one report cannot populate another report after route navigation; use request identity guards and stop polling on unmount.

## Validation and delivery criteria

Implementation tests should exercise meaningful boundaries:

- Sources from another case/version, simulation dialogue used as source evidence, invented citations, mismatched source/window hashes, absent quotations, attributed allegations, and conflicting sources.
- Exact-name/quotation retrieval, semantic-only matches with injected vectors, unavailable embeddings, neighboring context, deterministic ranking, and every retrieval budget flag.
- A ledger saved before prose generation; no accepted paragraph with unknown ledger references; malformed model output and uncovered text remain blocked; irrelevant summary text and unselected sections remain unchanged.
- Parent/source changes, concurrent legacy mutation, double acceptance, accept/reject races, process interruption around atomic publication, path traversal, and restart reconciliation. Reloaded parent bytes remain unchanged by proposal creation and acceptance.
- Old reports deserialize without new fields, existing generation/regeneration still behaves as before, Jev off makes no Jev calls, shadow mode cannot promote a draft or change production decision settings, and a zero-action report gains no forecast probability.
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

This document specifies the architecture and acceptance criteria. The next artifact is the concrete implementation plan after design review.
