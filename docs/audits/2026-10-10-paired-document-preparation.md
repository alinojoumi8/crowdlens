# Paired-document preparation verification

## Scope

A visible local-browser run used two selected motion notices, 21 PDF pages total,
from separately dated opposing-party records. This was a product workflow test,
not a full-record merits assessment. Original filings, selected PDFs, source
hashes, logs, and generated reports remain in private local storage; none are
included in this repository.

## Defects and corrections

- Time/event configuration previously sliced the start of a combined document
  context. A long first document displaced later documents. Bounded context now
  shares the existing character budget across document headings and excerpts,
  with an explicit warning that omitted text is not absent evidence. This is
  partial source coverage, not exhaustive retrieval.
- Preparation retries now prefer saved simulation settings over project defaults,
  while explicit request settings still win. Saved forecast mode, horizon,
  scenario, ensemble count and memory mode survive an omitted-field retry.
- Preparation preview counts honor excluded entity types and the agent cap.
  The manager persists the capped count before profile generation begins.
- Reloading an active preparation page resumes monitoring the existing task
  without admitting a second generation request.

## Verification

- `npm run check`: 769 Python, 12 Node, and 64 Vue tests passed; production build
  passed. New tests exercise both generation-stage prompts, small/tiny budgets,
  saved-setting precedence and capped counts, and refresh without re-admission.
- Live browser: upload, graph, preparation, refresh recovery, three-round
  simulation, and four-section report completed. A forced preparation retry was
  also exercised through the API; the initial bad retry was stopped, then the
  corrected six-profile configuration was generated and inspected.
- Corrected event configuration represented both selected notices and disclosed
  excerpt limits rather than claiming the second notice was not supplied.
- The baseline report's 11 saved files retained their pre-test SHA-256 hashes.
- PR #9's post-merge main CI run `38011655891` succeeded before this work began.

## Limits and follow-up

The capped participant set did not include a plaintiff persona. Only one agent
produced three non-noop model actions. Initial posts and scheduled entries are
inputs, not observed reactions; this run establishes no balanced consensus or
forecast calibration. The scenario probabilities remain uncalibrated.

Manual source checking caught an affidavit year transcribed as 2025 instead of
2023 in section 2. A separate source-based proposal was requested in the browser;
the original report is retained as the comparison baseline. The proposal removed
the wrong-year wording but expanded into lengthy verbatim excerpts, so it was
rejected rather than accepted as a focused correction. The original report
therefore still contains the known year error and must remain Needs review.
Automated source
checks must not be treated as a guarantee of factual accuracy.

No previous screenshot baseline was available, so visual regression is
inconclusive. Accessibility and web-vitals measurements were not performed.
The next quality milestone should exercise balanced participant selection and
exact date/page attribution using synthetic adversarial fixtures, followed by
bounded full-record source verification where appropriate.
