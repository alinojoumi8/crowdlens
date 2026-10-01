# Evidence-First Report Revisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task in the current task. Steps use checkbox syntax. The user explicitly requested completion of this plan followed by implementation with GPT-6 Astra at low reasoning; continue without another approval checkpoint. Use one independent whole-change reviewer after implementation.

**Goal:** Draft one existing report section from a persisted source-linked claim ledger, review related summary edits, and accept the result as a separate immutable report revision.

**Architecture:** Original case-version-scoped chunks feed bounded retrieval, ledger planning, structured prose, and independent structural checks. Proposal JSON artifacts and Linux filesystem leases own durable proposal state; existing TaskManager entries mirror progress. Acceptance publishes a complete staged report directory atomically, while ordinary report lookup remains deterministic and excludes revisions.

**Tech Stack:** Existing Python 3.11+, Flask, dataclasses/typing, pytest, Neo4j, `requests`/OpenAI client, optional local Ollama, Vue 3, Vitest, and Node test runner. Use standard-library filesystem locking, hashing, JSON, threads, and atomic rename. No new production dependency or remote provider is required.

**Spec:** [Revised design](../specs/2026-09-21-evidence-first-reports-design.md).

**Execution status:** All nine tasks are implemented on `codex/evidence-first-reports`. The plan was finalized before implementation. See the [verification audit](../../audits/2026-09-21-evidence-first-reports.md) for the independent review, corrections, test counts, and observed browser behavior.

## Global Constraints

- MiniMax remains the drafting model through the existing LLM client. Jev modes and promotion policy do not change. The workflow must function with Jev off, and shadow results remain advisory.
- Work on the existing feature branch or an isolated checkout starting from its current committed tip. Do not reset, merge, push, or discard unrelated changes. The plan itself is not an instruction to publish or modify the live deployment.
- First release: one selected section of a saved terminal report and related summary spans. Preserve all other section text, unrelated summary text, source attribution, forecasts, and original report bytes.
- Require graph/case/case-version scope. Admit at most 2,000 original chunks / 8 million characters. Retrieve at most six queries, 30 candidate chunks including neighbors, 60,000 drafting-packet characters, 30 claims, and three citations per claim.
- At most 200 new local document embeddings per proposal, auto-pull disabled. Reuse compatible original-source vectors when present. Never silently use remote embeddings. Missing semantic coverage is visible and falls back to lexical retrieval.
- One active proposal per report; two active workers per artifact root across backend processes. A 180-second monotonic deadline fences state transitions and every provider call uses the remaining budget with no automatic retries. An already-submitted remote call is not guaranteed to stop when local work expires.
- Source support is not factual certification. Accepted revisions always remain `needs_review`; failed structural validation prevents acceptance. Jev shadow outcomes never become acceptance gates.
- No private inputs, real credentials, or provider calls in tests and evaluation fixtures. Browser verification uses synthetic data in a temporary artifact directory. A real private/paid evaluation is separate work requiring approved inputs.
- Keep generic logs free of original excerpts, model response bodies, and credentials. Persist the necessary source evidence only under the configured private report artifact root.

## Review Focus

1. An accepted revision reaches legacy regeneration/resume or quality scoring: reject mutation before inference and retain `needs_review` (Task 6).
2. Analysis references itself, a cycle, or an ungrounded chain: reject deterministically and propagate unresolved premises (Task 1).
3. A crash follows directory publication, then the parent changes/disappears or Neo4j is unavailable: recover the committed revision before freshness checks (Task 6).
4. Filesystem ordering changes or a root is deleted while revisions survive: select the newest eligible root deterministically; never silently choose a child (Task 6).
5. Transport retries, late responses, or process restarts break budgets: enforce per-request controls and state fencing; reconcile abandoned queued and running work without disturbing a live owner (Tasks 2, 3, 7).

## File responsibilities and shared contracts

| File | Responsibility |
| --- | --- |
| Create `backend/app/services/claim_ledger.py` | Ledger/provenance validation, premise DAG, paragraph rendering, summary patch checks |
| Create `backend/app/services/proposal_store.py` | Proposal JSON snapshots, scoped locks, admission leases, state transitions, idempotency, restart reconciliation |
| Create `backend/app/utils/draft_budget.py` | Monotonic deadline and request-local usage accumulator |
| Modify `backend/app/utils/llm_client.py` | Optional per-call deadline/retry/usage controls; preserve legacy defaults |
| Create `backend/app/services/source_retrieval.py` | Frozen source corpus, lexical/exact/semantic ranking, safe context windows and neighbors |
| Create `backend/app/services/evidence_drafting.py` | Bounded ledger → draft → audit orchestration; no publication |
| Create `backend/app/services/report_revisions.py` | Parent snapshots, recovery-first acceptance, immutable report publication, lineage |
| Modify `backend/app/services/report_agent.py` | Compatible revision serialization, root selection, mutation guards, revision quality floor |
| Create `backend/app/api/evidence_proposals.py` | HTTP translation, proposal worker admission, status/accept/reject/revisions endpoints |
| Modify `backend/app/api/__init__.py`, `backend/app/__init__.py` | Blueprint module import and startup reconciliation |
| Modify `backend/app/api/report.py` | Guard legacy mutators, hold operation leases, reuse root by mode/depth, deletion tombstones |
| Create `frontend/src/components/EvidenceDraftReview.vue` | Proposal progress, source ledger, section/summary comparisons, accept/reject/revision navigation |
| Modify `frontend/src/components/Step4Report.vue`, `frontend/src/api/report.js` | Existing viewer integration and API wrappers |
| Create `backend/scripts/evaluate_evidence_drafts.py` | Offline paired-quality evaluation from independently supplied labels |
| Create `backend/scripts/smoke_evidence_drafts.py` | Disposable synthetic server/harness for the browser flow |

Runtime contracts use JSON-compatible dictionaries with explicit validation. Avoid a second representation of the same report. `scope` always has nonempty `graph_id`, `case_id`, `case_version_id`. A `finding` has `code`, `blocking: bool`, and optional `claim_id`/`message`. New APIs accept only server-known report/proposal IDs; never accept scope, raw sources, output paths, or a replacement report from the browser.

Proposal records have `schema_version=1`, `proposal_id`, `parent_report_id`, `revision_report_id`, `request_key_hash`, `request_digest`, `parent_digest`, `scope`, `source_digest`, `section_index`, `state`, `phase`, `created_at`, `updated_at`, `deadline_at`, `before`, `after`, `ledger`, `sources`, `findings`, `usage`, `timing`, `limitations`, `proposal_digest`, and `accepted_report_id`. Immutable content and mutable state are hashed separately; do not include heartbeat timestamps or the current state in `proposal_digest`. Keep the frozen parent snapshot and full admitted source corpus in separate private snapshot files referenced by hash.

`before` and `after` each contain `section` and `summary` strings. Proposed paragraphs contain `text`, `kind`, and `claim_ids`. A summary edit contains `start`, `end`, `old_text`, `new_text`, and `claim_ids`; offsets are Python Unicode code points in the frozen original summary, never browser UTF-16 offsets. The UI displays server-produced strings and does not calculate edits.

## Task 1: Define and validate the claim ledger

**Files:** Create `backend/app/services/claim_ledger.py`, `backend/tests/test_claim_ledger.py`, and `backend/tests/evidence_draft_samples.py`.

**Produces:**

```python
def canonical_digest(value: object) -> str:
    import hashlib, json
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# Public signatures; implementations also enforce the constraints below.
# validate_ledger(ledger: list[dict], sources: list[dict], scope: dict) -> list[dict]
# validate_paragraphs(paragraphs: list[dict], ledger: list[dict]) -> list[dict]
# render_paragraphs(paragraphs: list[dict], ledger: list[dict]) -> str
# apply_summary_edits(original: str, edits: list[dict], ledger: list[dict]) -> str
```

Sources preserve existing SourceIndex provenance plus `window`, `window_hash`, `window_start`, and `window_end`. `source_hash` hashes the full original `excerpt`; `window_hash` hashes only `window`. Validate both and require `excerpt[window_start:window_end] == window`. For the existing verifier, adapt the validated window to `excerpt=window`, `source_hash=window_hash`, and retain the full hash as `original_source_hash`. Never pass a full-text hash as the hash of a shortened excerpt.

- [ ] Write self-contained fixtures and failing ledger tests. `evidence_draft_samples.py` defines `SCOPE`, `sample_source()`, `sample_claim()`, `sample_report()` using the existing Report dataclasses. Use these exact initial values:

```python
SCOPE = {"graph_id": "g1", "case_id": "c1", "case_version_id": "v1"}
TEXT = "Alex states that the hearing was postponed until Friday."

def sample_source():
    from app.services.evidence_verifier import text_hash
    return {**SCOPE, "evidence_id": "episode:one", "episode_id": "one",
            "document_id": "doc", "filename": "record.txt", "origin": "source_document",
            "excerpt": TEXT, "source_hash": text_hash(TEXT), "window": TEXT,
            "window_hash": text_hash(TEXT), "window_start": 0, "window_end": len(TEXT),
            "locator": {"page": 1, "chunk_index": 0, "offset_basis": "stored_chunk"}}

def sample_claim():
    return {"claim_id": "claim_01", "schema_version": 1, "kind": "attributed_allegation",
            "text": TEXT, "attribution": "Alex", "scope": SCOPE,
            "citation_ids": ["episode:one"], "premise_claim_ids": [], "quote": "", "checks": []}

def sample_report(report_id="report_root"):
    from app.services.report_agent import Report, ReportOutline, ReportSection, ReportStatus
    return Report(report_id, "sim_1", "g1", "Analyze the hearing record.", ReportStatus.NEEDS_REVIEW,
                  report_mode="legal_case", created_at="2026-09-21T12:00:00",
                  source_grounding={**SCOPE},
                  outline=ReportOutline("Hearing report", "The hearing is Thursday. Other issues remain open.",
                      [ReportSection("Hearing", content="The hearing is Thursday."),
                       ReportSection("Other issues", content="Other issues remain open.")]))

def test_analysis_cycle_cannot_be_accepted():
    from app.services.claim_ledger import validate_ledger
    from evidence_draft_samples import SCOPE
    ledger = [
        {"claim_id": "claim_01", "kind": "analysis", "text": "Analysis A",
         "premise_claim_ids": ["claim_02"], "citation_ids": [], "scope": SCOPE},
        {"claim_id": "claim_02", "kind": "analysis", "text": "Analysis B",
         "premise_claim_ids": ["claim_01"], "citation_ids": [], "scope": SCOPE},
    ]
    findings = validate_ledger(ledger, [], SCOPE)
    assert any(f["code"] == "premise_cycle" and f["blocking"] for f in findings)
```

Add cases for self-reference, empty premises, unknown IDs, duplicate IDs, deep acyclic chains, missing citation leaves, foreign case/version, missing attribution for allegations, literal quote mismatch, tampered windows, and simulation text supplied as document evidence. A valid source claim must supply citation IDs from the frozen pool; analysis has no shortcut around its premise graph.

- [ ] Run `cd backend && uv run pytest -q tests/test_claim_ledger.py`; observe failure on the new module before implementing it.
- [ ] Implement deterministic validation and a three-color DFS over premise IDs. Each analysis node must have nonempty premises; source/allegation leaves require valid citations; V1 rejects newly proposed `simulation_observation` entries. Preserve inherited simulation references only when supplied by the server with a recorded artifact hash. Propagate an unresolved premise without relabeling it supported.

```python
def apply_edits_in_reverse(original, edits):
    previous_start = len(original) + 1
    result = original
    for edit in sorted(edits, key=lambda item: item["start"], reverse=True):
        start, end = edit["start"], edit["end"]
        if type(start) is not int or type(end) is not int:
            raise ValueError("invalid_summary_offsets")
        if not 0 <= start < end <= len(original) or end > previous_start:
            raise ValueError("overlapping_or_invalid_summary_edit")
        if original[start:end] != edit["old_text"]:
            raise ValueError("stale_summary_span")
        result = result[:start] + edit["new_text"] + result[end:]
        previous_start = start
    return result
```

Use this edit algorithm inside `apply_summary_edits` after validating referenced claims and bounded replacement strings. Empty edit lists return the original. Validate every prose paragraph, including short sentences/headings containing assertions; do not use the old 40-character coverage heuristic as proof of coverage. Render source markers from validated claim/citation IDs. Escape labels and let existing SafeMarkdown render text; no raw model HTML.

- [ ] Add and run tests for nonoverlapping Unicode summary spans, mismatched offsets, unchanged summary bytes, unknown paragraph claims, kind mismatch, repeated references, and deterministic rendering. Run existing source-tracing/evidence tests as a compatibility check.
- [ ] Commit: `feat: validate source-linked claim ledgers and summary edits`.

## Task 2: Durable proposal artifacts and cross-process admission

**Files:** Create `backend/app/services/proposal_store.py` and `backend/tests/test_proposal_store.py`.

**Consumes:** Task 1 `canonical_digest`. **Produces:** `ProposalError(code: str, status: int)`, `ProposalStore(root: Path)`, `OperationLease` with `close()`, and these store methods:

```python
# operation(report_id: str) -> context manager; nonblocking, raises report_busy/409
# admit(parent_report_id: str, request_key: str, request_digest: str) -> tuple[dict, object | None]
# get(parent_report_id: str, proposal_id: str) -> dict
# update(proposal_id: str, expected_states: set[str], changes: dict) -> dict
# save_snapshot(proposal_id: str, name: str, value: object) -> str
# load_snapshot(proposal_id: str, name: str, expected_digest: str) -> object
# finish(proposal_id: str, changes: dict) -> dict
# reject(parent_report_id: str, proposal_id: str) -> dict
# reconcile() -> dict[str, int]
```

`admit` returns the existing record and `None` for a matching retry. New work receives a lease bundle holding the report operation lease and one worker slot; its creator transfers that bundle to the thread and closes it on startup failure. Store methods validate identifiers with a bounded ASCII allowlist, root confinement, and symlink checks. Snapshot names come from a fixed internal allowlist, not requests. Lease files live under `<root>/.evidence-locks/`; proposals under `<root>/.evidence-proposals/`; staging/tombstones also have hidden dedicated directories.

- [ ] Add failing persistence tests with independent store instances and child processes. The following test establishes retry deduplication without spawning a model:

```python
def test_creation_retry_returns_same_proposal(tmp_path):
    from app.services.proposal_store import ProposalStore
    store = ProposalStore(tmp_path)
    first, lease = store.admit("report_root", "request-1", "body-hash")
    try:
        second, repeated_lease = ProposalStore(tmp_path).admit("report_root", "request-1", "body-hash")
        assert second["proposal_id"] == first["proposal_id"]
        assert repeated_lease is None
    finally:
        lease.close()
```

Test key reuse with a different body (409), two occupied global slots (third admission 503), concurrent requests for the same parent (409 unless the same idempotent request), unsafe paths/symlinks, wrong parent/proposal pairing (404), and atomic JSON visibility.

- [ ] Run `cd backend && uv run pytest -q tests/test_proposal_store.py`; verify expected failures.
- [ ] Implement leases using `fcntl.flock(LOCK_EX | LOCK_NB)` plus an in-process lock registry keyed by resolved paths; close descriptors in `finally`. Do not unlink lock files. Hold a short admission lock only while checking idempotency, reserving the operation/slot leases, and writing queued state; never during snapshots, provider calls, or worker execution.

```python
def atomic_json(path, payload):
    import json, os, tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)
```

Use publication locks for compare-and-transition updates. Terminal states cannot return to running/ready. The immutable proposal digest covers scope, before/after, source/parent digests, ledger/checks, policy/model identity, and limitations. Rejection may mark queued/running work rejected; workers check state before each call and before finishing, retain leases until exit, and never revive it.

- [ ] Kill a child process after queued persistence, then after transition to running. `reconcile` must acquire the corresponding operation lease before declaring it abandoned and mark failed/interrupted without scheduling inference. An independently running child holding the lease stays running. Repeated reconciliation is idempotent. Keep source snapshots readable after rejection/failure.
- [ ] Run the store tests; commit `feat: persist evidence proposals with process-shared admission`.

## Task 3: Per-request deadline, retry, and usage controls

**Files:** Create `backend/app/utils/draft_budget.py`, `backend/tests/test_draft_budget.py`; modify `backend/app/utils/llm_client.py`, `backend/app/storage/embedding_service.py`, `backend/app/services/decision_gateway.py`, and `backend/app/services/decision_records.py` only at request-control boundaries; add focused transport tests to `backend/tests/test_draft_transports.py`.

**Produces:** `DraftBudget(seconds=180, clock=time.monotonic)` with `remaining() -> float`, `check() -> None`, `record_usage(provider, model, usage, elapsed_ms) -> None`, `snapshot() -> dict`. `DeadlineExceeded` is a typed local failure. Extend LLM `chat` and `chat_json` with keyword-only `request_timeout: float | None = None`, `request_max_retries: int | None = None`, `usage_callback=None`. Thread these through Anthropic and native Ollama paths. Preserve return types and existing default behavior. Provide equivalent optional timeout/retry controls to local embedding calls; omission keeps old behavior. The embedding service currently counts total attempts in `max_retries`, so an explicit request override of zero retries must still execute one attempt. Add optional `request_timeout` to `DecisionRunner.evaluate` and `DecisionGateway.evaluate`, forwarding it without changing cache identity; the gateway already makes one attempt. In Task 5, a proposal-local runner wrapper checks the budget and forwards the remaining timeout on each `evaluate` invocation from the existing verifier. Record cached responses as cache hits without charging their usage twice.

- [ ] Write deterministic clock and fake transport tests before edits:

```python
def test_remaining_budget_expires_without_sleep():
    import pytest
    from app.utils.draft_budget import DraftBudget, DeadlineExceeded
    now = [10.0]
    budget = DraftBudget(seconds=180, clock=lambda: now[0])
    now[0] = 189.5
    assert budget.remaining() == pytest.approx(0.5)
    now[0] = 190.0
    with pytest.raises(DeadlineExceeded):
        budget.check()
```

Intercept requests and SDK calls to prove proposal controls yield exactly one attempt for 429, 500, connection errors, and timeouts; the next call receives a smaller remaining timeout. Exercise OpenAI-compatible, Anthropic-compatible, native Ollama, embeddings, and optional Jev boundaries. Verify default legacy retry behavior remains unchanged. No test uses a real key or network.

- [ ] Run focused tests and observe failures for the absent controls.
- [ ] Use a request-scoped OpenAI client via `with_options(timeout=request_timeout, max_retries=0)` when overrides are set; never mutate a shared client's timeout. Anthropic loops resolve overrides locally and skip sleep/retry when zero. Native requests receive the override. Capture actual response model and token usage through the callback before extracting text; normalize missing counts as unknown, not zero.

```python
def remaining_timeout(budget, maximum=30.0):
    budget.check()
    return min(maximum, budget.remaining())
```

The orchestrator invokes `budget.check()` before and after each call. A watchdog and store transition fencing are required in Task 7; timeout values alone are not a hard wall-clock cancellation guarantee. Errors contain stable codes, never response bodies or credentials. Usage fields include input/output tokens, elapsed time, model, and attempt count; cost is not inferred without prices.

- [ ] Run transport and existing LLM/embedding/gateway tests once green. Commit `feat: add request-scoped drafting budgets and usage telemetry`.

## Task 4: Retrieve original evidence with explicit coverage

**Files:** Create `backend/app/services/source_retrieval.py`, `backend/tests/test_source_retrieval.py`; make a narrow extension to original-chunk retrieval only if compatible episode-vector metadata is absent from returned properties.

**Consumes:** Existing `SourceIndex`, scoped `storage.get_source_chunks`, Task 1 source/window checks, Task 3 budget. **Produces:** `freeze_sources(episodes: list[dict], scope: dict) -> dict` returning `{scope, sources, digest, limited, limitations}`; `retrieve_sources(corpus: dict, queries: list[str], *, budget, embedder=None) -> dict` returning `{sources, rankings, limitations}`. Inputs are the entire admitted corpus, never a global graph ANN result filtered after retrieval.

- [ ] Add failing tests using explicit sources and injected vectors:

```python
def test_foreign_version_never_enters_source_packet():
    from app.services.source_retrieval import freeze_sources
    scope = {"graph_id": "g", "case_id": "c", "case_version_id": "v"}
    episodes = [
        {**scope, "uuid": "one", "document_id": "doc", "data": "The hearing is Friday.", "page": 1},
        {**scope, "uuid": "two", "document_id": "doc", "data": "The hearing is Thursday.", "case_version_id": "old"},
    ]
    corpus = freeze_sources(episodes, scope)
    assert [s["episode_id"] for s in corpus["sources"]] == ["one"]
```

Test exact quotation priority, same-name different-person context, semantic-only relevant sources, negated/contradictory passages retained, absent embeddings, incompatible dimensions/model IDs, nonfinite vectors, unavailable Ollama, budgets, and neighbor scope. A retrieval miss must remain missing, never become a fabricated fallback citation.

- [ ] Run the tests and verify failures.
- [ ] Freeze sources in stable ID order, recording locator metadata and both coverage flags in the corpus digest. Use lexical scoring from SourceIndex, exact phrase boosts, and cosine similarity only for compatible finite vectors. Rank fusion uses `sum(1 / (60 + rank))` with stable evidence-ID tie-breaking. Preserve exact-hit candidates within the 30-item cap before fused candidates and neighbors; if too many exact hits exist, record their truncation count.

```python
def reciprocal_rank_fusion(rankings):
    scores = {}
    for ranking in rankings:
        for rank, evidence_id in enumerate(dict.fromkeys(ranking), start=1):
            scores[evidence_id] = scores.get(evidence_id, 0.0) + 1.0 / (60 + rank)
    return sorted(scores, key=lambda key: (-scores[key], key))
```

Keep quote-bearing windows exact; locate them in the full original text, record offsets, and include nearby context within the character cap. Never cut a requested literal quotation in half. Semantic coverage over missing vectors can use up to 200 local embeddings selected in stable ID order with lexical candidates first; report covered/admitted counts. Do not build a persistent vector index or pull a model in this release. If the configured provider is remote, skip uncached embedding work and report the limitation.

- [ ] Run retrieval, source-tracing, and provenance tests. Commit `feat: retrieve scoped original evidence for report drafts`.

## Task 5: Persist the ledger before drafting and audit the proposal

**Files:** Create `backend/app/services/evidence_drafting.py`, `backend/tests/test_evidence_drafting.py`.

**Consumes:** Tasks 1–4 and existing source semantic checks. **Produces:** `EvidenceDraftingService(storage, llm, store, *, embedder=None, evidence_runner=None)` with `generate(proposal_id: str, parent_snapshot: dict, *, budget) -> dict`. It returns final proposal content but never writes a report revision. `source_scope(parent_snapshot: dict, simulation_config: dict) -> dict` derives and cross-checks persisted graph/case/version data; inconsistency fails instead of guessing.

- [ ] Write tests using fake LLM responses and an event-recording store. `sample_report()` must provide two sections and a two-sentence summary, plus scope-bearing source metadata, so tests can verify preservation outside the selected section.

```python
def test_ledger_is_saved_before_prose_call(tmp_path):
    from app.services.proposal_store import ProposalStore
    from app.services.evidence_drafting import EvidenceDraftingService
    from app.utils.draft_budget import DraftBudget
    from evidence_draft_samples import SCOPE, TEXT, sample_claim, sample_report
    events = []
    class RecordingStore(ProposalStore):
        def save_snapshot(self, proposal_id, name, value):
            events.append(("save", name))
            return super().save_snapshot(proposal_id, name, value)
    class SourceStorage:
        def get_source_chunks(self, graph_id, case_id, case_version_id):
            return [{**SCOPE, "uuid": "one", "document_id": "doc", "data": TEXT, "page": 1}]
    class RecordingLLM:
        def chat_json(self, messages, **kwargs):
            phase = messages[0]["content"].splitlines()[0]
            events.append(("call", phase))
            if phase == "EVIDENCE_LEDGER_V1":
                return {"claims": [sample_claim()], "gaps": []}
            if phase == "EVIDENCE_DRAFT_V1":
                assert ("save", "ledger") in events
                return {"paragraphs": [{"text": TEXT, "kind": "attributed_allegation",
                                        "claim_ids": ["claim_01"]}], "summary_edits": []}
            return {"findings": [], "covered_paragraph_indices": [0],
                    "covered_summary_edit_indices": [], "summary_unchanged_consistent": True}
    store = RecordingStore(tmp_path)
    parent = sample_report().to_dict()
    proposal, lease = store.admit(parent["report_id"], "request-1", "body-hash")
    try:
        store.update(proposal["proposal_id"], {"queued"},
                     {"state": "running", "section_index": 1, "scope": SCOPE})
        service = EvidenceDraftingService(SourceStorage(), RecordingLLM(), store)
        service.generate(proposal["proposal_id"], parent, budget=DraftBudget())
        assert events.index(("save", "ledger")) < events.index(("call", "EVIDENCE_DRAFT_V1"))
    finally:
        lease.close()
```

Use the phase marker as the first system-prompt line followed by the actual bounded instructions. Keep fake clients as the only provider boundary. Add tests for empty/malformed plans, invented sources, exact quote/attribution failure, prose adding a factual assertion beyond its linked ledger entry, invalid summary spans, unchanged summary, and source budgets. The example checks ordering only; a separate test must require the Thursday-to-Friday summary inconsistency to be patched or flagged as blocked by the audit.

- [ ] Run `cd backend && uv run pytest -q tests/test_evidence_drafting.py`; observe initial failures.
- [ ] Execute phases `retrieving`, `planning`, `drafting`, `auditing` with persisted progress. Allocate allowed claim IDs `claim_01` through `claim_30` before planning. LLM planning returns only a subset of those IDs plus explicit gaps; code validates sources, sorts IDs, validates the premise graph, and saves the immutable ledger before requesting prose.

The drafting call receives the ledger and selected original windows. It returns structured paragraphs and summary edits; old section/summary text is comparison material, never evidence. Apply structural checks first. Use a separate M3 audit response schema with `findings` entries `{code, target_kind, target_index, claim_ids, detail}`, `covered_paragraph_indices`, `covered_summary_edit_indices`, and `summary_unchanged_consistent: bool`. Bound every string and require exact paragraph/edit index coverage. All paragraphs, including short assertions, and every changed summary span must be included; unknown indices or malformed output block the proposal. When the summary has no edits, a false consistency result blocks acceptance instead of preserving an acknowledged contradiction. Audit checks additions and attribution against the ledger, not whether old prose sounds plausible. A model can miss an error, so do not label the audit exhaustive. Evidence gaps are persisted as limitations and rendered as server-authored search-coverage notices outside factual paragraphs; they are not source claims with invented citation IDs.

If evidence mode is off, no Jev client or calls are created. For shadow mode, record source-support judgments through a deadline-aware runner but never put those judgments in `blocking` structural findings. With mode on, continue preserving configured global behavior, while this workflow remains needs-review and does not promote any feature. Preserve evidence gaps as limitations. No evidence/invalid ledger yields `blocked`; transport or deadline failures yield `failed`; a complete structurally valid proposal yields `ready`.

- [ ] Assert provider call bounds: one planning call, one prose/summary call, one audit call, plus bounded optional source-check batches; no automatic repair loop. Assert source snapshots, ledger, model/policy IDs, timings, and usage survive reload. Commit `feat: generate reviewable evidence-first section proposals`.

## Task 6: Publish immutable revisions and close legacy compatibility gaps

**Files:** Create `backend/app/services/report_revisions.py`, `backend/tests/test_report_revisions.py`; modify `backend/app/services/report_agent.py`, `backend/app/api/report.py`; add focused tests for root lookup and revision mutation guards.

**Consumes:** Store, ledger, frozen proposal content. **Produces:** `ReportRevisionService(store, *, storage, report_manager=ReportManager)` with `accept(parent_report_id, proposal_id, expected_digest) -> Report`, `revisions(report_id) -> list[dict]`, and `delete(report_id) -> bool`. Add `Report.revision: dict` and `ReportSection.claim_ledger: list[dict]` with empty defaults; round-trip both in to/from-dict. Revision metadata contains `immutable`, `parent_report_id`, `root_report_id`, `proposal_id`, `proposal_digest`, `content_digest`, `accepted_at`, `section_index`, `inherited_forecast`, and `source_checked_at`.

- [ ] Write failing tests for every review finding before integration:

```python
def test_default_lookup_is_independent_of_directory_order(tmp_path, monkeypatch):
    import os
    from app.services.report_agent import ReportManager
    from evidence_draft_samples import sample_report
    monkeypatch.setattr(ReportManager, "_get_reports_dir", classmethod(lambda cls: str(tmp_path)))
    root = sample_report(report_id="report_root")
    child = sample_report(report_id="report_child")
    child.revision = {"immutable": True, "parent_report_id": root.report_id, "root_report_id": root.report_id}
    reports = {root.report_id: root, child.report_id: child}
    for report_id in reports:
        (tmp_path / report_id).mkdir()
    monkeypatch.setattr(ReportManager, "get_report", classmethod(lambda cls, report_id: reports.get(report_id)))
    for order in ([root.report_id, child.report_id], [child.report_id, root.report_id]):
        monkeypatch.setattr(os, "listdir", lambda path, order=order: order)
        assert ReportManager.get_report_by_simulation(root.simulation_id).report_id == root.report_id
```

The lookup test intentionally injects reads; separate persistence tests construct children through the actual staging publisher. Test legacy API and direct service regeneration/resume on a revision fail before any provider call, quality status cannot promote it, report/forecast/ledger digests stay unchanged, and unselected source checks retain inheritance metadata. Test original reports still regenerate normally. Acquire long operation leases at service entry points, with API prechecks only, so wrappers do not accidentally reacquire a nonreentrant lock; publication locks remain short and follow the declared order.

- [ ] Run targeted tests, then implement deterministic root selection: `get_report_by_simulation(simulation_id, *, report_mode=None, report_depth=None)` filters out revisions, applies optional mode/depth, and sorts by `(created_at, report_id)` descending. Update generation reuse callers to pass requested mode/depth. Exclude all hidden internal artifact directories from every report listing/read-by-simulation path. Root deletion with surviving children returns no root.
- [ ] Implement acceptance in this order, using operation lease → proposal publication lock:

```text
validate parent/proposal association and expected immutable proposal digest
if revision tombstone exists: return 410
if deterministic target exists:
    require matching proposal ID, proposal digest, and actual content digest
    reconcile state to accepted and return it without parent/source access
require proposal state ready and no blocking findings
reload parent under its operation lease; compare frozen parent digest
load source corpus outside publication lock while keeping operation lease
compare corpus digest; transient source outage leaves proposal ready
reacquire proposal lock and recheck state/digest
stage the complete revision on the same filesystem
flush files and directories, rename to unused deterministic target, fsync parent
atomically record accepted result; return new report
```

Recovery may inspect a matching published target before acquiring a missing parent's content; the operation lease filename still exists outside the parent directory. Rejection uses the same committed-target reconciliation so it cannot reject already-published work. Mismatched target digests return 409, never overwrite. Parent deletion during generation is excluded by its operation lease. Explicit revision deletion writes a tombstone under that lease before removing artifacts, so retry cannot resurrect it.

- [ ] Write a staged report using a pure assembly function that joins title, summary, and section strings; do not call the existing global postprocessing rewrite. Persist `meta.json`, `outline.json`, all section Markdown, `full_report.md`, proposal provenance, ledger, and final progress. Force `needs_review`, preserve forecast unchanged and mark inherited, and do not call `_record_case_snapshot`.
- [ ] Inject failures immediately before rename and immediately after rename. After the latter, modify/delete the parent and make storage unavailable; retry must return the same intact revision. Before publication, those changes must reject or defer acceptance. Cover concurrent accept/reject, duplicate acceptance, target mismatch, deletion tombstones, path traversal, fsync/write failures, and parent byte preservation.
- [ ] Run revision, report-quality, case workflow, and source-check suites. Commit `feat: publish immutable evidence report revisions safely`.

## Task 7: Expose proposal APIs and reconcile workers

**Files:** Create `backend/app/api/evidence_proposals.py`, `backend/tests/test_evidence_proposal_api.py`; modify `backend/app/api/__init__.py`, `backend/app/__init__.py` and legacy `backend/app/api/report.py` guards.

**Consumes:** Store, DraftBudget, drafting and revision services. **Produces:** routes from the design, registered on existing `report_bp`. Application extensions own store/service factories for dependency injection; initialize with `ReportManager._get_reports_dir()` so existing writable fallback behavior remains coherent.

- [ ] Add API tests using a minimal Flask app, the real store in `tmp_path`, synthetic source storage, and fake drafting client. Cover absent/malformed JSON, booleans as section indices, out-of-range sections, nonterminal parent status, missing/mismatched scope, oversized request keys, unknown identifiers, request replay, and wrong-parent proposal access.

```python
def test_repeated_accept_returns_same_revision(client, ready_proposal):
    parent, proposal, digest = ready_proposal
    path = f"/api/report/{parent}/evidence-proposals/{proposal}/accept"
    first = client.post(path, json={"proposal_digest": digest})
    second = client.post(path, json={"proposal_digest": digest})
    assert first.status_code == second.status_code == 200
    assert first.json["data"]["report_id"] == second.json["data"]["report_id"]
```

Define `client` and `ready_proposal` fixtures in this test module using Tasks 1/2/6, with no real app provider startup. The ready proposal is generated through the service with injected responses, not hand-marked valid without validation.

- [ ] Run tests to observe missing routes/fixtures fail, then implement envelope translation. Create returns 202 for admitted or replayed work, status GET returns persisted proposal state, accept returns the new report object, reject returns final proposal state, revisions returns lineage. Use 400/404/409/410/503 exactly as the design specifies. Escape/internalize error text; no provider payloads or traceback responses.
- [ ] Create TaskManager progress mirrors only after admission succeeds. Worker receives the lease bundle, snapshot, and client factories; no `current_app` lookup occurs inside an unbound background thread. Use `try/finally` to release all leases, including thread-start and snapshot failures. A watchdog transitions queued/running work to failed/deadline_exceeded at the deadline; `finish` requires state still running, so late results cannot become ready. Do not release capacity while provider work is still executing.
- [ ] Add tests for startup with live/abandoned workers in separate processes; queued and running orphan recovery; process-local stale TaskManager caches not affecting status GET; global two-slot admission; worker exceptions; deadline during source-check batches; GET causing zero inference calls; rejection during generation; and transport failure followed by safe explicit new request.
- [ ] Mount reconciliation in application startup after the artifact root is resolved. It only repairs dead work and never calls providers. Run targeted API and startup tests; commit `feat: expose evidence proposal lifecycle and recovery APIs`.

## Task 8: Add the review flow to the existing report viewer

**Files:** Create `frontend/src/components/EvidenceDraftReview.vue`, `frontend/src/components/EvidenceDraftReview.component.test.js`, `frontend/src/utils/evidenceProposal.js`, `frontend/src/utils/evidenceProposal.test.js`; modify `frontend/src/components/Step4Report.vue`, `frontend/src/api/report.js`.

**API wrappers:** `createEvidenceProposal(reportId, {section_index, request_key})`, `getEvidenceProposal(reportId, proposalId)`, `acceptEvidenceProposal(reportId, proposalId, proposalDigest)`, `rejectEvidenceProposal(reportId, proposalId)`, `getReportRevisions(reportId)`. Use `service` directly; do not wrap mutations in the existing generic retry helper. Preserve one request key for a user-initiated creation retry and generate a new key only for a new proposal. Do not place private sources in browser localStorage.

**Component contract:** props `reportId: String`, `sectionIndex: Number`; emits `revision-created(reportId)` and `close`. Step4Report handles navigation using existing router patterns. It supplies a Draft with sources control for each eligible section, displays parent/root revision links, and disables legacy in-place mutation buttons for immutable revisions. The backend remains authoritative for eligibility.

- [ ] Add failing component tests, mocking API calls and using fake timers:

```javascript
it('does not render raw source HTML', async () => {
  const wrapper = mount(EvidenceDraftReview, { props: { reportId: 'report_root', sectionIndex: 1 } })
  await wrapper.get('[data-test="create-proposal"]').trigger('click')
  await flushPromises()
  expect(wrapper.find('img').exists()).toBe(false)
  expect(wrapper.text()).toContain('<img src=x onerror=alert(1)>')
})
```

Provide a mocked ready response with an exact hostile excerpt and a valid ledger; test before/proposed section and summary text, limitations, nonblocking semantic warnings, blocking structural failures, busy/unavailable states, acceptance disabled while unresolved, reject, duplicate clicks, and parent/revision navigation. Use real DOM interactions, not snapshots of implementation internals.

- [ ] Run `npm --prefix frontend run test:components -- EvidenceDraftReview` and observe initial failure.
- [ ] Implement status polling with existing polling helpers where compatible. A monotonically increasing request generation guards every response; stop timers on unmount or report/section change. Polling never triggers create. Acceptance sends the displayed `proposal_digest`; a 409 leaves the proposal visible with a stale/conflict explanation; a 410 shows deleted revision; success emits the returned report ID once.

```javascript
export function isProposalAcceptable(proposal) {
  return proposal?.state === 'ready' &&
    typeof proposal?.proposal_digest === 'string' &&
    !proposal.findings?.some(finding => finding.blocking)
}
```

Define this pure helper in `evidenceProposal.js` and test missing data, pending/failed/rejected/stale states, and advisory findings. Render prose through SafeMarkdown and excerpts through Vue text interpolation; accessible buttons/details need clear labels, focus handling, and error text. Keep implementation hashes in expandable provenance details, not primary action labels.

- [ ] Verify late responses from the previous report cannot populate the current report or emit navigation; double acceptance stays one request; terminal status stops polling. Run frontend unit/component tests and build. Commit `feat: review and accept source-linked report revisions`.

## Task 9: Offline evaluation, browser flow, and final verification

**Files:** Create `backend/scripts/evaluate_evidence_drafts.py`, `backend/tests/test_evidence_draft_evaluation.py`, `backend/tests/fixtures/evidence_drafts/paired.jsonl`, `backend/scripts/smoke_evidence_drafts.py`, and `docs/evidence-first-reports.md`. Record final evidence in `docs/audits/2026-09-21-evidence-first-reports.md` using the actual completion date if later.

**Evaluation schema:** Each JSONL row contains `case_id`, `split`, `label_source`, `reviewed`, `baseline`, and `proposed`. Each side has `claims` with `claim_id`, `critical`, nullable independently supplied `factual_correct`, `attribution_correct`, `citation_valid`, `quote_valid`, model `supported`, `label_source`; `retrieved_source_ids`, `relevant_source_ids`, `important_omissions`; and optional measured `review_seconds`, `usage`, `elapsed_seconds`. Exclude unlabeled judgments from accuracy denominators and report their count. Synthetic labels have `reviewed=false` and cannot count as independent quality evidence.

- [ ] Write metric tests before implementation:

```python
def test_unlabeled_claim_is_not_counted_as_correct():
    from scripts.evaluate_evidence_drafts import score_claims
    result = score_claims([
        {"factual_correct": True, "supported": True, "critical": False},
        {"factual_correct": None, "supported": True, "critical": True},
    ])
    assert result["labeled_count"] == 1
    assert result["unlabeled_count"] == 1
    assert result["accuracy"] == 1.0
```

Implement `score_claims(claims: list[dict]) -> dict` and `evaluate_pairs(rows: list[dict]) -> dict` with explicit numerators/denominators, separate critical errors, per-case and pooled summaries, retrieval recall, and false-supported counts. When a denominator is zero, return null plus zero denominator. Do not substitute M3/Jev agreement for labels. Paired deltas require both sides and the same case/split. Report human review time only when measured. Optional pricing is a separate explicit JSON input; absent prices mean unknown cost.

- [ ] Run `cd backend && uv run pytest -q tests/test_evidence_draft_evaluation.py`, then implement an offline-only CLI accepting `--input` and `--output`; no live mode or imported provider client. Commit fixtures that cover missing evidence, attribution, negation, changed versions, exact quotes, and unlabeled examples.
- [ ] Implement the smoke script as an explicit `--synthetic --output-dir` harness. It must refuse the normal uploads directory, use a temporary report root, synthetic source storage and fake LLM outputs, and disable real provider access. Bind to loopback on a chosen free port; serve the real frontend using its development/build configuration. The script prints the synthetic report URL and how to stop the process; it is never imported by production startup.
- [ ] In a browser, open that saved report, create a proposal, inspect source/summary differences, accept, reload the new URL, navigate to the parent, and confirm both persisted versions and immutable controls. Exercise one blocked proposal and one stale acceptance. Verify actual backend files/digests before and after. Record screenshots only if they help demonstrate the result; no private data.
- [ ] Run `npm run check` from the repository root after targeted tests pass. Run the full backend suite in a clean temporary copy with the root/backend `.env` files absent and provider credentials unset; do not edit the operator's `.env`. A container copy is acceptable when available, but wait for its command to finish and inspect its exit status. Read output, record exact test counts, and distinguish synthetic browser evidence from real model quality.
- [ ] Use one fresh reviewer on the whole feature diff against the recorded implementation base. Provide spec/plan, implementation commit range, test evidence, and scoped instructions. Fix actionable correctness findings, add meaningful regressions, and rerun affected checks. Do not modify private production settings, promote Jev, merge branches, or push unless separately instructed.
- [ ] Commit documentation, evaluation harness, and validation evidence as `test: verify evidence report revisions end to end`. Final report links the revised design, implementation plan, principal feature entry points, and audit; states observed tests/browser behavior and remaining independent-quality limitations.

## Completion contract and execution record

Final-review implementation rulings: enforce immutability at every shared report writer and at generation with a supplied report ID; validate complete artifact paths including leaf files and legacy files; expose explicit `accepting` recovery and permit rejection only before publication under both operation leases; persist telemetry independently of terminal-state transitions; anchor lexical windows on matching terms, preserve intersecting requested quotations, and disclose clipping/candidate caps; invalidate pending status reads before UI mutations; and return typed deletion conflicts. These clarify the existing persistence, recovery, coverage, and concurrency contracts without expanding the feature's scope.

The implementation is complete only when all nine tasks and their verification steps are satisfied, the five review findings have explicit regression coverage, parent/revision persistence works through the real browser/API flow, and the final review has no unresolved actionable correctness finding. Merely finishing a document, mocked unit tests, or an LLM response is not completion.

Create an ignored progress ledger for this plan through the executing-plans skill. Record each task's base/commit, test commands/results, and any implementation ruling. If an interface needs adjustment, update the plan and ledger together, preserve the spec's invariants, and continue. The user's current instruction authorizes implementation immediately after this plan is finalized.
