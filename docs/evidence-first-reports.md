# Evidence-first report revisions

Open a saved completed or needs-review report and select **Draft with sources** in a section. The report must retain its graph, case, and case-version scope and have original document chunks in that version. The workflow drafts one section and related summary spans, leaving other sections unchanged.

Review the original and proposed section, summary changes, claim ledger, original excerpts, attribution, and search limits. **Save as new revision** creates a separate immutable report. **Keep original** rejects the proposal while retaining its audit record. The saved revision links to its parent, original report, and accepted proposal. A revision can be the starting point for another proposal.

All accepted revisions remain `needs_review`. Source links and model judgments do not certify factual correctness. Forecasts and unselected sections are inherited; acceptance does not run a simulation or record a fresh case prediction. Legacy section rerun/resume operations reject immutable revisions. Full generation continues to create root reports, and ordinary simulation lookup selects the newest matching root only.

## Dependencies and bounds

The workflow uses the existing configured drafting LLM and original Neo4j source chunks. Existing Jev configuration is respected; off makes no Jev calls and shadow checks remain advisory. No promotion settings change. Optional semantic retrieval uses local Ollama only, disables model pulling and automatic retries, and reports missing coverage. Remote embedding requests are skipped.

Each proposal is limited to 2,000 admitted chunks / 8 million characters, six retrieval queries, 30 source windows / 60,000 characters, 30 claims, three selected citations per source claim, and 200 new local document embeddings. Three drafting-model calls cover planning, prose/summary drafting, and audit. A 180-second deadline and state checks fence late results. Submitted remote work may finish after local expiry; its worker slot remains held until the call exits. One proposal may run per report and two workers may run per report artifact root across processes.

Raw source snapshots and proposals are stored under the existing private report root in `.evidence-proposals`. Leases live separately in `.evidence-locks`; staging and deletion tombstones have separate hidden directories. Keep these directories with report backups. Startup marks abandoned queued/running work interrupted without restarting inference. Do not remove lock files while any backend is running.

Private `diagnostics.json` snapshots retain the actual completion text before JSON
cleanup/parsing, the parsed response when available, and exact audit/paragraph
validation findings. They do not contain a full HTTP response envelope. Each
completion is capped at 256,000 characters with a full-content SHA-256 and an
explicit truncation flag. Parsed JSON is retained within the same character limit;
oversized parsed output is explicitly omitted and blocked. Atomic writes use private file permissions;
the public proposal contains a diagnostics digest rather than the raw responses.
Responses arriving after cancellation can be retained privately without making a
proposal ready or weakening ownership, deadline, Stop or acceptance fences.

Drafts must keep every paragraph's kind consistent with all its linked claims.
Audits must supply the exact coverage arrays, booleans and finding fields required
by the existing schema. Malformed or incomplete model output remains blocked;
review errors now identify the affected paragraph or audit field.

New root reports save a bounded original-source and simulation-action packet under
`source_grounding` using `report-grounding-v1`. Original excerpts, generated graph
paraphrases, initial/scheduled inputs and actual model actions remain distinct.
Quotation checks require an exact excerpt and exact bracketed source/action ID;
generated input posts cannot pass as model-action quotations. The saved forecast
is frozen before prose generation and reused for the headline table, panel,
resume and regeneration. Numerical percentages outside that table require matching
original-source evidence. These mechanical checks do not establish semantic
correctness, omission coverage or forecast calibration. Legacy reports retain
their historical status and are not retroactively certified.

Fresh generation checks the planned summary and each section against that same
provenance/percentage guard. A blocking passage gets at most one ordinary counted
model correction with the exact findings and frozen context. Before/after text
and findings remain in `agent_log.jsonl`; an invalid or empty correction still
blocks, and ownership/Stop fences reject a late response before adoption. The
final assembled report is validated again. Existing summaries are not automatically
corrected during Resume, and late correction text rejected by Stop is not appended
to the report log. This improves a mechanical generation boundary; it does not
certify paraphrase entailment, omissions, or the heuristic forecast.

A creation retry must reuse its request key. Acceptance uses the displayed immutable proposal digest. Parent/source changes make an unpublished proposal stale; source outages leave it retryable. After an interrupted save, **Retry saving revision** uses the same digest and works after reloading. If publication succeeded before the interruption, retry recovers that revision without parent/source availability. **Keep original** can abandon an interrupted save only when no revision was published; a published revision must first be recovered. Deleted revisions return 410 and are not recreated. Existing reports need no data migration.

Cancelled or expired proposals retain observed usage and phase timings, including responses that arrive after cancellation, without becoming ready again. Retrieval windows follow literal quotations or matching search terms, and the review panel discloses clipped windows and capped candidate coverage.

## Verification and offline evaluation

Run `UV_PYTHON=3.11 npm run check` from the repository root. The explicit runtime matches the installed dependency lock; Python 3.13 cannot build its pinned tiktoken release.

The synthetic browser harness serves the real built frontend and report APIs, blocks real provider requests, and requires a new empty directory under the system temporary directory:

```bash
npm --prefix frontend run build
cd backend
UV_PYTHON=3.11 uv run --frozen python scripts/smoke_evidence_drafts.py --synthetic --output-dir /tmp/evidence-report-demo
```

It prints a loopback URL and uses Ctrl-C to stop. The hearing section demonstrates a successful revision; the unrelated-contract section demonstrates a blocked retrieval. A harness-only `POST /__synthetic/change-source` changes the synthetic corpus for stale-acceptance testing. `GET /__synthetic/evidence` writes filesystem verification into the chosen temporary directory. Neither route exists in production.

The offline evaluator accepts paired JSONL rows with separately supplied labels:

```bash
cd backend
UV_PYTHON=3.11 uv run --frozen python scripts/evaluate_evidence_drafts.py \
  --input tests/fixtures/evidence_drafts/paired.jsonl --output /tmp/evidence-evaluation.json
```

Rows need `case_id`, `split`, `reviewed`, `label_source`, `baseline`, and `proposed`. Each side supplies claim labels, retrieved/relevant source IDs, omissions, and optional measured review time, latency, and observed usage. Independent review sources are `human`, `expert`, or `independent_review`; per-claim model labels are excluded. The caller remains responsible for the authenticity of supplied labels. Zero denominators yield null rates. Optional `--prices` supplies model rates per million input/output tokens; absent prices mean unknown cost.

Committed fixtures are synthetic and unreviewed. They demonstrate metric mechanics, not quality improvements. A real quality evaluation requires separately approved inputs, independent labels, measured review time, and held-out cases.

## Focused date and number corrections

Open **Correct a date or number** beneath the relevant report section. Enter the
literal current wording, the corrected wording, and a quotation copied from the
original source. Only digit changes are allowed; surrounding wording, attribution,
conditions, summary, and forecasts are preserved. The server replaces every exact
match in that section (at most 20) and displays the occurrence count and comparison.

The quotation must resolve to one document in the report's frozen source scope.
A bounded model check reviews all changed references against the matching stored
chunk; unsupported, uncertain, missing, or malformed checks block saving. This is
an AI judgment about a narrow correction, not verification of inherited prose or
the case outcome. Adjacent chunks may contain additional context. Saving creates a
separate **Needs review** revision and rechecks unchanged parent and source hashes.
Retries reuse the frozen request; **New proposal** clears it without starting a call.

Capped preparation now selects across explicit graph entity types rather than
truncating the first nodes. Legal mode prioritizes labelled plaintiffs and defendants
when the cap and filters permit. **Participant coverage** shows selected type counts
and warns when either side is missing. Labels are not verified roles, and type
coverage does not establish balanced activity or viewpoints. Existing simulations
and their forecasts are not retroactively changed.

## Report validation coverage

The repeated-fact check compares substantive sentences across sections. Reusing a
document citation or a PDF page locator does not count as repeating a fact.
Repeated assertions still count when their document citations differ.
Filename-only PDF addresses, italicized filenames, and original-page mappings in
square or round brackets are also treated as locators. Substantive parentheticals
are retained; this normalization applies only to repetition checking.

Original-source availability and procedural-role coverage are separate statuses.
The cover check requires an explicit **MOTION RECORD OF THE** party label and
recognized relief on a scoped source cover. The notice check recognizes a printed
**NOTICE OF MOTION** or **NOTICE OF CROSS-MOTION** heading followed in the same
page-one chunk by **The [party role] [optional uppercase names] will make a motion**.
Notice anchors preserve the document, page, source hash, and explicit role. Each
document has its own mover; paired motions do not establish one global moving or
opposing party, and a notice mover does not establish requested relief or dates.
When graph chunks lack page metadata, complete `[PDF page 1]` through
`[PDF page 2]` boundaries in frozen original text can supply the opening. The
check retains chunk hashes and page offsets and reads only page one. Missing end
markers or chunk order alone do not establish a complete opening.

Notice validation checks narrow affirmative labels such as **the defendants’
notice** in a single assertion preceding one cited document, with only one party
role mentioned. Multiple-assertion or multiple-role comparisons, uncited labels,
quotations, conditional statements, prior motions,
and arbitrary paraphrases remain outside this check's coverage. Captions alone
are never role evidence. Conflicting declarations, unrecognized notice forms,
mixed cover/notice packets, and incomplete retrieval still require review.
`procedural_source_unavailable` means limited coverage rather than a finding of
misattribution. A detected conflict requires review, and a high score cannot
waive missing coverage. Passing these narrow checks does not certify attribution
throughout the report.

Existing reports retain their saved scores, status, frozen source context, and
text. Rechecking an older report does not silently replace its provenance or
certify the case facts. These checks are deterministic safeguards, not general
legal fact verification or calibrated forecasting.
