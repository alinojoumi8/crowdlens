# Astra AI review of v3 verification packets

**Complete independent AI opinion — not human review, adjudication or acceptance.** Four final packets, eight original source documents and all 33 exact ledger claims were assessed. Results: **31 supported, 1 unsupported, 1 ambiguous; no conflicting ledger labels**. Attribution/citation judgments are each true for 31 and false for 2 claims. All **28 frozen material facts are covered by the complete sections**; no material section omissions were found. These counts describe one AI review, not real-world accuracy or a release gate.

## Material findings

| Packet | Ledger result | Main finding |
| --- | --- | --- |
| `packet_14a5a90af7e4` — shade | 5 supported | Section covers costs, limits and all attributed positions. Summary retains an inventory assertion outside the source evidence. |
| `packet_1fd04b4fabe7` — procurement | 7 supported; 1 unsupported | `claim_08` invents unsigned quotation status and strengthens no recorded spending/no purchase order into no purchase. Summary repeats the categorical no-purchase assertion. |
| `packet_33c45e4e3fba` — lending | 9 supported; 1 ambiguous | `claim_07` can imply actual conditional support rather than Ivo's possible support. Candidate summary still states approval and commencement contrary to the sources, despite a separate corrective proposal. |
| `packet_ec808a4e312f` — attendance | 10 supported | Section and substantive summary preserve both populations, unresolved account status and evidence limits. Summary correctly declines to verify inventory status. |

**Procurement — unsupported strengthening.** S01 `decision.txt`, p. 1 ¶1, records no spending and excludes permanent installation. S02 `procurement.txt`, p. 1 ¶1, has a pending $1,460 quotation, no purchase order and a $1,800 ceiling that is not a paid amount. Neither says the quotation is unsigned or proves that no unrecorded purchase happened. Those extra assertions in `claim_08` are unsupported, not merely missing citations. The complete section does contain all six material reference facts; completeness does not cure the added assertions.

**Lending — modality and separate summary failure.** S01 `consultation.txt`, p. 1 ¶1, says Ivo *could support* the pilot if training is demonstrated. `claim_07`'s “support is conditional” admits both a faithful shorthand and a stronger actual-commitment reading, so it is ambiguous. More seriously, the supplied `candidate_summary` still says everyone approved permanent lending and lending already began. S01 states no permanent decision/no start; S02 `agenda.txt`, p. 1 ¶1, states no vote. That summary is unsupported and contradicts the records. It equals the original comparison summary, has no span edits, and is accompanied by separate replacement proposals. Their existence is not evidence that this supplied summary or any accepted report has been corrected.

**Unrelated inventory prose.** Shade, procurement and lending summaries retain “The separate equipment inventory remains unchanged.” The original comparison summaries establish where that text came from, but the source documents provide no inventory evidence. This is an inherited, unverified assertion, not a finding that the changed proposal newly invented it. The attendance summary instead explicitly says those sources cannot confirm or update inventory status.

## Complete sections, summaries and proposals

Every complete section was checked for material claims outside its ledger; none were found. All sources are materially represented. Conflict handling is true for the sections: differing shade positions are disclosed, both attendance populations are preserved without resolving or replacing one account, and the procurement/lending source statuses are retained. This field does not certify summary accuracy or excuse the unsupported/ambiguous claims above. Analysis claims were judged through valid premise-source chains; absence of a direct citation alone was not treated as failure.

Candidate summaries were assessed independently. Shade compresses the three specific positions into “mixed”; procurement omits the pending quotation and overstates purchase absence; lending retains contrary original assertions; attendance omits the repeat-visitor identifier limitation from the summary while preserving it in the section. These summary observations do not change the section-only omission count.

All four proposal surfaces were inspected: **4 raw span edits and 6 old-text/new-text replacement entries**. Under zero-based half-open character offsets, **4 of 4 raw spans** is both in bounds and an exact match for its declared old_text against the now-supplied `original_comparison_summary`; **6 of 6 replacement entries** have a unique matching old_text there. The span values and precise comparisons are retained in the JSONL. These are packet-level observations, not runtime or acceptance conclusions. No proposal was applied, corrected, accepted or published.

## Provenance and limits

Final input: `/home/ali/Documents/CrowdLens-reviews/2026-10-03-source-review-v3/review-final/reviewer`. Source-only facts were frozen before any candidate content was displayed, from the initial `/review/reviewer` export. The final export adds **`original_comparison_summary`**, so the available summary inputs did change. I verified that every preexisting field, including sources, filenames, tasks, claims, candidate text and proposal fields, stayed identical. The frozen facts therefore remain valid and unchanged; the review rows preserve the **final** blank-form packet hashes and separately record the initial hashes. Original comparison text was used only as an edit target, never as source evidence.

No administrator material, run diagnostics, corpus, application code, aggregate gates or prior review artifacts were consulted for calibration. Supplied source filenames were treated as evidence metadata. Sources are fictional, and no underlying events were independently verified. No provider or browser was used, no original artifact/importer was changed, and no human provenance or measured timing is claimed. Borderline judgments remain reviewer opinions.

Reviewer: `gpt-6-astra-max-source-review-v3`; `reviewer_kind: ai`; model `gpt-6-astra`; effort `max`; reviewed at `2026-10-04T00:23:23.592262+00:00`; `review_seconds: null` in every row.

Frozen reference SHA-256: `addcc72ca89326902199dac1f7653294488e8ab092c055cb3eef68369959311d`.

## Prioritized next steps

1. Preserve procurement record qualifiers and remove or substantiate the quotation-signature assertion before relying on that analysis or summary.
2. Review the lending summary as a separate artifact and retain Ivo's possible-support modality; do not count an unapplied replacement as a corrected report.
3. Keep inherited inventory prose explicitly outside this source review's verification scope. Check actual target/offset handling separately before any future application; this review makes no runtime diagnosis.
4. Retain these AI judgments separately from human/adjudicated records. Use fresh independent evidence for broader performance claims.

- [Source-first frozen facts](source-first-reference-facts.json): four packets, 28 facts, unchanged after freezing.
- [Complete AI reviews](reviews.jsonl): four rows, 33 exact claim assessments, summary/proposal findings and final packet hashes.
- [This concise report](review.md).
