# Conditional-completion development review — run 02

**Both cases remain blocked; no final section or summary exists.** The persisted ledgers do show **two faithful source-excerpt expansions**, but that is an intermediate result, not successful report completion.

Across **16 persisted ledger claims**, this AI review finds **14 supported, 1 unsupported and 1 ambiguous**. Attribution is correct for 14; precise citation support is correct for 13. All **10 frozen material facts** appear in the ledgers. Final-section omissions, conditional fidelity and summary/suffix fidelity remain **unassessed** because both `after` objects are empty and neither attempt reached drafting.

| Evidence layer | Observed result |
| --- | --- |
| MiniMax selection | One explicit `source_sentence_id` per case, with blank model text for that entry |
| Persisted server expansion | Both selected entries contain the exact current participant-note excerpt, including conditional possibility and no existing commitment |
| Additional MiniMax prose | 14 separately authored claims; not validated merely by the exact source extract beside them |
| Final rendered output | 0 sections, 0 summaries, 0 ready cases; no suffix behavior to assess |

## Remaining ledger issues

**Fernbank `claim_05` — unsupported strengthening.** The source says Tavi's team *could assist if adjustable worktables are confirmed*. The claim adds that **any team assistance is conditioned on confirmation**, broadening the stated conditional possibility into a universal necessary condition. Current `followup.txt` (repair_document_1, p. 1 ¶1) does not support that universal restriction. Its first clause about no existing commitment is supported. The guard flags this claim.

**Willowmere `claim_04` — attribution ambiguity.** The source says Leena reports that **the group** may assist. “Leena's stated willingness” can mean her report of that group position or Leena's personal willingness. The possible-future/not-existing-commitment qualifier is correct, but the actor is less precise than current `followup.txt` (sorting_document_1, p. 1 ¶1). The exact source excerpt in `claim_05` correctly retains the group as actor; its presence does not remove the separate ambiguity.

**Willowmere `claim_10` — incomplete citation coverage.** Its absence claim covers *the supplied records*, but it cites only original.txt. Both complete originals support the bounded absence assertion, yet the actual citation does not establish absence across the uncited participant note. This is a citation-completeness issue, not a finding that a purchase or agreement occurred.

Other guarded paraphrases preserve the source meaning: Fernbank `claim_02` retains *could assist if* and no existing commitment; Willowmere `claim_03` retains Leena/the group/*may assist provided*; `claim_08` confines missing confirmation to the record. The sorting analysis is supported through valid premise-source chains, including the exact source excerpt, even though an extra premise has attribution ambiguity. Guard findings therefore mix strict extraction requirements with substantive issues; they are not interchangeable with semantic error labels.

## MiniMax versus server responsibility

The saved raw MiniMax completion selects `claim_06` in repair and `claim_05` in sorting by source ID while leaving their text blank. The persisted ledger fills each with its complete current participant-note excerpt, matching the original source hash and wording exactly. This is direct evidence of faithful **ledger expansion**. It is not model-authored source prose, and it is not evidence that final paragraph or summary rendering ran.

The other 14 persisted claim texts match the raw model-authored texts. The review does not erase them or invent a clean final output containing only the two good extracts. Both proposal records remain blocked and unaccepted. The ledgers preserve all material facts collectively, but source completeness does not cure a stronger added claim.

## Provenance and limits

The same source-only facts were frozen **before run 01 outputs** and reused unchanged. Eligibility requires exact current graph/case/version scope and original-document origin. All four admitted source hashes match those references; superseded/foreign-case source bodies were excluded. Run 02 uses the same development cases with a tuned prompt and is **not holdout quality evidence**.

Reviewer: `gpt-6-astra-max-conditional-completion-development-review`; kind **ai**; model `gpt-6-astra`; effort `max`; reviewed at `2026-10-05T07:40:35.851151+00:00`. Human and review timing are null. No provider rerun, code change, acceptance or publication was performed by this reviewer.

- Run 02 results SHA-256: `bc0ddd42954bef02ae6427d615f271f8e506c8b6e6427a936905fb2f56efbfdc`.
- Frozen source-first facts SHA-256: `fff07b1f07c2f297458a9cc5041af0b96f89b5bbef4d447855d4d89faa2c6870`.
- Exact record, diagnostics, raw-completion and source hashes are retained in the JSON review.

The next development check must demonstrate actual final rendering while keeping unnecessary free prose from reintroducing conditional strengthening. Until a section and summary exist, their source coverage and unrelated-suffix preservation cannot be certified. Keep run 01 and run 02 as separate unchanged observations; neither is release approval.

- [Structured run 02 review](run02-review.json)
- [Unchanged run 01 review](review.json)
- [Frozen source facts](source-first-reference-facts.json)
