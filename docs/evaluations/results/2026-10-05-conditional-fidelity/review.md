# Conditional-fidelity correction and v7 guard review

**The separate Elmreach correction is source-faithful:** all **4 claims are supported**, all **5 material source facts** are covered, and the selected-claim summary preserves the unrelated suffix exactly once. This is an AI reviewer opinion, not human review, publication permission or release approval.

The correction preserves the schedule's explicit **only when a certified instructor is present** requirement, while reporting Sora's **could assist if accessible benches are confirmed** as possible future assistance rather than an existing commitment. It adds no universal claim that benches must be confirmed before every possible form of assistance. Attribution and citation support are correct for all four exact claim IDs; no material omission or additional unledgered source claim was found.

The inherited ventilation sentence is unchanged and appears once, outside the source-scoped text. Its factual status is not established by the two originals. No normalized edit spans are supplied for this separate correction, so this review verifies its supplied text, not an application to an original report. The v6 packet and its original reviews remain unchanged.

## What the fresh v7 blocks demonstrate

`run/results.json` records **2/2 cases blocked and 0/2 ready**. Saved proposal records and diagnostics identify **three flagged items**. All three are semantically source-supported in this targeted review:

| Case / blocked item | Observed change | AI assessment |
| --- | --- | --- |
| Toolroom `claim_03` — `conditional_source_requires_extract` | Drops the introductory document label; retains “Nila says the team might assist if adjustable tables are confirmed.” | Speaker, possibility and condition are unchanged. No semantic strengthening found. |
| Library paragraph index 2 — `conditional_paragraph_requires_extract` | Drops the document label; retains “Omar says the group may assist provided accessible carts are confirmed.” | Faithful conditional statement; no current commitment asserted. |
| Library paragraph index 3 — same guard code | Attributes “possible future assistance, not an existing commitment” explicitly to the participant note. | Faithful paraphrase and attribution, although not an exact source sentence. |

The toolroom record is blocked after planning; the library record includes a saved drafting response but is also blocked. Both have empty `after` objects and null accepted-report IDs. The diagnostics are evidence of attempted text, not accepted final drafts.

**These are conservative exact-wording/extraction blocks, not verified catches of changed conditional meaning.** The guard did reject changed text, but the inspected differences preserve the source meaning. Do not count these outcomes as factual-quality successes or successful model completions. Conversely, the blocks do not justify labelling these three statements unsupported: exact-contract compliance and semantic source support are different judgments. No conclusion about the guard's broader performance follows from two cases.

## Evidence and provenance

The correction task and both complete fictional originals were read first; five material facts were frozen before correction prose. V7 source windows were read before the flagged text. The saved `results.json`, proposal records and diagnostics were inspected without running a provider or application code. A read-only database schema inventory was used only to locate evidence; no database payload was used. Original v6 artifacts were not opened or changed.

Reviewer: `gpt-6-astra-max-conditional-fidelity-correction-review`; kind **ai**; model `gpt-6-astra`; reasoning effort `max`; reviewed at `2026-10-05T06:45:06.249493+00:00`. Both review-time fields are null; no human ratings or human timing are claimed.

- Correction packet SHA-256: `4eb4440077f1b5e57cc8fab108f3358077992f7018aa1634657523894cf61d55`.
- Source S01 (`original.txt`) SHA-256: `cfb48bfe76c7f967a7a7d6098622f7a08aa9fb968465dcfe8ba892d17f0d0319`.
- Source S02 (`followup.txt`) SHA-256: `e2b0a10eebecbddbd947e3dbf8a45d3d5ac6c2f2a7443c842cb350857ae61285`.
- Frozen source-first facts SHA-256: `a878cca1b5e76e2cdcbd824daff855831b9a9c0dd5178bd6d43df532974ff682`.
- V7 results SHA-256: `4d6f1773f85f9e3daafae8c9601cbfe697846e8924b1c2db821a4c22509f9ad5`.

Exact packet/source hashes, all four claim IDs, source-first fact preservation, summary composition and suffix count were validated. The JSON review also records the exact proposal/diagnostic hashes and each flagged-text comparison.

Keep this correction review separate from the original v6 judgment. For v7 reporting, distinguish the observed 0/2 ready result and strict extraction noncompliance from semantic defects; the inspected flags establish the former, not the latter. This review does not change guard policy or accept any proposal.

- [Correction review and v7 comparisons](correction-review.json)
- [Frozen correction source facts](correction-source-first-reference-facts.json)
- [Correction input](elmreach-correction.json)
