# Public opinion evidence-draft review

Official PDF: https://www.supremecourt.gov/opinions/23pdf/22-429_h315.pdf
PDF SHA-256: `7dba0b08254d8d0eccd91ccfe915ecccd33ac1daaada7daabcae3f5bc743a952`
Source subset: the four majority-opinion pages (PDF pages 2–5). The syllabus and concurrences are excluded.
The extracted text joins PDF line breaks. Check wording and context against the linked PDF.

Model for both paths: **MiniMax-M3**. The baseline uses one direct call; the evidence-first path plans a ledger, drafts, and audits.
Proposal state: **ready**. Human factual review is pending.

## Baseline section

Laufer urged the Court to dismiss the case as moot and to refrain from resolving the standing question, characterizing mootness as easy and standing as hard. Acheson urged the Court to decide the standing issue despite mootness, emphasizing the live circuit split and concerns about litigants manipulating the Court's jurisdiction. The Court dismissed the case as moot, vacated the First Circuit's judgment, and remanded with instructions to dismiss, without reaching the standing issue.

## Evidence-first section

Laufer urged the Court to refrain from resolving the standing question and to dismiss the case as moot, characterizing mootness as easy and standing as hard. [1]

Acheson urged the Court to decide the standing issue despite mootness, emphasizing the live circuit split, efficiency concerns, and the risk that litigants could manipulate the Court's jurisdiction by abandoning claims to evade review. [1]

Laufer voluntarily dismissed her pending ADA cases with prejudice, including her complaint against Acheson in the District of Maine, following the suspension of her lawyer Tristan Gillespie by the U.S. District Court for the District of Maryland. [2]

The Court dismissed the case as moot, expressing sensitivity to Acheson's concern about litigants manipulating the Court's jurisdiction but concluding it was not convinced Laufer abandoned her case to evade review; the Court emphasized it might exercise its discretion differently in a future case. [1]

The Court vacated the judgment and remanded the case to the First Circuit with instructions to dismiss the case as moot under the Munsingwear practice, without reaching the standing issue. [1] [3]

## Baseline summary

The Court dismissed Acheson Hotels v. Laufer as moot after Laufer voluntarily dismissed her underlying claims, declining to address whether she had Article III standing to sue.

## Evidence-first summary

The Court dismissed Acheson Hotels v. Laufer as moot after Laufer voluntarily dismissed her underlying claims, declining to address whether she had Article III standing to sue.

## Measurements

- Baseline: 0.83 s, 1 model call; estimated cost 0.00068 USD.
- Evidence-first: 4.74 s, 3 model calls; estimated cost 0.004238 USD.
- Structured source claims: 5; citation links: 6; optional verbatim quote fields: 0 (0 matched cited source chunks).
- Factual correctness, attribution correctness, omissions, and human review time await your review.
- The price estimate uses [published MiniMax-M3 standard-priority rates](https://platform.minimax.io/subscribe/token-plan?tab=api-enterprise). Actual billing may differ by plan and caching.

## Trial history

- `proposal_72e044ea2a4c48f390a37260db0ee065`: blocked; findings: analysis_citations_must_use_premises, premise_unverified, quote_absent; 1 model call; estimated cost 0.004352 USD.
- `proposal_b749f157527840648bfab71c870820ae`: blocked; findings: missing_attribution, premise_unverified, quote_absent; 1 model call; estimated cost 0.002833 USD.
- `proposal_fa187043999948dfbb796487a2298fc6`: blocked; findings: invalid_summary_edits, paragraph_kind_mismatch; 2 model calls; estimated cost 0.003187 USD.
- `proposal_674e04c55d884618a7445d6eb1c0a9c2`: ready; findings: none; 3 model calls; estimated cost 0.004238 USD.

## Your review

The majority opinion says Laufer did not argue that the Court **must** dismiss for mootness. Check whether both drafts overstate her position by saying she urged dismissal.

| Measure | Baseline | Evidence-first |
| --- | --- | --- |
| Factual errors | pending | pending |
| Attribution errors | pending | pending |
| Citation meaning and page match | n/a | pending |
| Material omissions | pending | pending |
| Human review time | pending | pending |

- [ ] Check each factual statement in both sections against the PDF.
- [ ] Check whose position each statement represents: the Court, Laufer, or Acheson.
- [ ] Check source page links and whether cited excerpts support the full meaning of each claim.
- [ ] Note important omissions and whether the revised summary reflects the Court’s actual disposition.
- [ ] Record your review time and any errors before deciding whether to save the revision.

## Reproduce

Build the frontend, provide an existing local `.env` with MiniMax credentials, and use a new empty directory under `/tmp`:

```bash
UV_PYTHON=3.11 uv run --frozen --directory backend python scripts/public_evidence_demo.py \
  --pdf /path/to/22-429_h315.pdf --model-env /path/to/.env \
  --output-dir /tmp/mirofish-public-evidence-replay
```

The script refuses a PDF with a different SHA-256 and leaves any accepted revision to the reviewer.
