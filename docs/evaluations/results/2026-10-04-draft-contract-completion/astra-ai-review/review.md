# Astra AI source review — v5

**Two exported drafts reviewed; a pool-summary defect remains.** All **10 exact ledger claims are supported**, with correct attribution/citation judgments, and all **10 frozen material source facts** are covered by the complete sections. No material section omissions or unresolved source conflicts were found. These results do not certify the summaries or constitute release approval.

| Packet | Section and ledger | Summary finding |
| --- | --- | --- |
| `packet_813bf897be6b` — Meadowbank exhibition | Five supported claims; both session populations and evidence limits preserved | Source-scoped summary is supported. Unrelated inspection context is retained once outside the replacement and remains unverified. |
| `packet_e0107f297db0` — Brookvale pool | Five supported claims; staffing/accessibility conditions and possible future support preserved | Section-summary replacement includes an unrelated unsupported inspection statement; the combined summary repeats it twice. |

## Concrete remaining problem

In the pool packet, `candidate_section_summary.text` and the span edit's `new_text` include **“An unrelated equipment inspection is pending.”** Neither S01 `record.txt` nor S02 `followup.txt` (both p. 1, paragraph 1) says anything about an inspection, and none of the five linked claim IDs supports it.

The original comparison summary contains that sentence once, **after** the declared pool approval/endorsement target. The supplied `candidate_summary` contains it **twice**. The replacement has therefore pulled unrelated comparison context into the source-scoped summary while that context remains in the original suffix. This is visible in the packet text; no production/runtime behavior is inferred. Presence in the old comparison text establishes provenance, not factual support.

Meadowbank does not introduce the sentence inside its replacement: its source-scoped summary concerns only the two sessions, and the combined summary retains the unrelated original sentence once. That retained context is outside this review's factual verification; it should not be counted as newly invented source prose or as verified inspection status.

## What the sources support

**Meadowbank:** S01 `record.txt`, p. 1 ¶1, records 72 morning public visitors and four separately counted staff. S02 `followup.txt`, p. 1 ¶1, records 55 afternoon public visitors, no recorded afternoon staff attendance, and neither session as a vote or endorsement. The section and its scoped summary preserve every distinction. They do not infer zero afternoon staff, combine sessions into unique individuals, or convert attendance into support. The repeated morning staff exclusion is a minor editorial redundancy.

**Brookvale:** S01 `record.txt`, p. 1 ¶1, permits two supervised evening sessions only with two lifeguards and does not approve permanent evening opening. S02 `followup.txt`, p. 1 ¶1, attributes to Nia possible future group support if accessible changing facilities are confirmed and explicitly denies an existing endorsement. The section preserves both conditions and the speaker's qualified position. Its analysis is supported through the stated premise-source chains; no direct analysis citation is required. The task-relevant part of the summary also retains these limits.

All complete sections were inspected for additional material propositions outside the ledger; none were found. The unsupported inspection proposition is separately recorded on the **section-summary/replacement surface**, so it is not hidden by the 10/10 supported-ledger count. Primary omission and conflict fields refer to complete sections.

## Target checks and limits

Both supplied span edits were compared with `original_comparison_summary`: **2 of 2** have in-bounds, exact old-text matches under zero-based half-open character offsets. Both replacement texts equal their supplied section-summary text. `candidate_summary_replacements` is empty in both packets. No separate raw original-section document was supplied; the available raw target is each span edit's declared `old_text` and its original-summary range. No missing target or accepted report was reconstructed.

Input was limited to `/home/ali/Documents/CrowdLens-reviews/2026-10-04-source-review-v5/review-final/reviewer`. Tasks and all four complete fictional originals were read first; ten material facts were frozen before candidate prose. Only the two actual exported drafts were rated. No unavailable attempt, administrator mapping, run/results, diagnostics, production gate, application code or outside source was inspected. Originals were preserved; no provider was called and no proposal was accepted, applied or published.

Reviewer: `gpt-6-astra-max-source-review-v5`; kind **ai**; model `gpt-6-astra`; effort `max`; reviewed at `2026-10-04T12:14:39.804583+00:00`. Every `review_seconds` is null. These are source-bounded AI opinions, not human ratings, measured human time, adjudicated truth or release approval.

Frozen reference SHA-256: `2289f877f5cfd874aaedde304c75e49de3e0cfc2823fe68c1aac4f53cc68f9c9`.

## Next steps

1. Keep the pool section-summary replacement within its supported source/topic boundary; prevent unrelated trailing context from entering it again.
2. Preserve unrelated original context once and distinguish preservation from factual verification. Check each summary sentence against its linked claims as well as checking the ledger alone.
3. Recheck summary scope and resulting text after any repair. The supported ledger and complete sections do not by themselves establish a clean combined summary.

- [Frozen source-first facts](source-first-reference-facts.json)
- [Two complete AI review records](reviews.jsonl)
- [This review](review.md)
