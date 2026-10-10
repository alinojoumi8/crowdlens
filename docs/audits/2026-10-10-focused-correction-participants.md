# Focused corrections and capped participant coverage

The previous paired-document QA found two incorrect year references and a capped
participant list that omitted one labelled side. This change provides a narrow
correction path and type-aware selection without rewriting existing simulations.

## Implementation

- Separate `focused-literal-correction-v1` proposal policy permits digit changes
  only. Exact patch rendering, occurrence count, frozen parent/source integrity,
  immutable request retry and supported context audit are checked before saving.
  Original reports remain unchanged. Raw provider diagnostics are retained locally.
- Capped selection uses deterministic type round robin, prioritizing explicit
  Plaintiff/Defendant labels for legal reports. Filters still apply; missing sides
  produce warnings. State and generated configuration retain coverage metadata.
- Preparation refresh restores saved controls and coverage while monitoring the
  existing task; it does not admit a replacement generation.

## Verification

Local `UV_PYTHON=3.11 npm run check`: 783 Python, 12 Node and 66 Vue tests plus
production build. Regression coverage includes negative/uncertain audits, stale
sources, immutable revisions, unchanged inherited content, request retries,
ordering, filters, capped profile generation and persisted coverage on reload.

Visible browser verification with MiniMax-M3.1-Flash-Preview:

- A focused date correction changed exactly two references in one section,
  received a supported context judgment, and saved a separate Needs review
  revision. Reload retained it. Summary and other sections were identical;
  original report and earlier baseline file hashes remained unchanged.
- A fresh six-profile preparation on the paired-document graph completed and
  retained both labelled sides plus four other types. Browser coverage and saved
  profiles/configuration were checked. Template profiles were used; three model
  configuration calls plus one focused audit were admitted for this verification.
- Existing sparse simulation output was preserved. No new simulation activity or
  outcome calibration was performed. Prepared roles remain graph labels rather
  than independently verified party identities.

Private filings, quotations, report artifacts and screenshots remain outside Git.
One development case does not establish general factual accuracy. Next: run and
inspect activity across both sides in a fresh bounded simulation, then evaluate
focused corrections on held-out synthetic ambiguous dates and amounts.
