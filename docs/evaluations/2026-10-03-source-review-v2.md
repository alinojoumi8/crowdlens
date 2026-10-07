# Held-out source review v2 — 2026-10-03

## Result and boundary

Four new fictional held-out source packets produced actual MiniMax-M3 proposal drafts. All four proposals were blocked by existing production validation: **0 ready / 4 attempted**. Nine model requests completed within the frozen 12-request/900-second workflow. Admission is closed, workflow stopped, and in-flight count is zero. This is an observed proposal-path result, not a factual-error rate, forecasting score, full upload-to-report E2E run, or release approval. Billing amount is unknown; token usage and elapsed time are in the [receipt](results/2026-10-03-source-review-v2/receipt.json).

Application behavior and production prompts remain unchanged from application candidate `4faf90a4b5a57b99397a47e413a27c2ca2ac3806`. There were no proposal acceptances, provider retries, prompt tuning against these inputs, publication, main merge, push, deployment, or new generation-model downloads. Authored comparison parents are evaluation inputs, not actual model baselines. Their files remained unchanged during collection. Source admission respected current original-document scope; retrieval selected one of two originals per case, which does not establish retrieval completeness.

## Protocol and provenance

The [definition](source-review-v2-definition.md) and separate four-case corpus were frozen in `c826f854d94e89148493527478d72ab97da98176`. Actual execution began at that HEAD with three uncommitted evaluation-file overlays after a staging command used the wrong directory. Those exact bytes were subsequently committed as `98a8cc465ebe524b06ab315fb705a7e00ca7b441`. This was **not a clean-commit launch**. The original results retain the launch HEAD; supplemental launch identity records overlay hashes. Later collector/export corrections were not used to generate or retry these outputs.

Original actual responses, sealed proposal diagnostics, authored parents and stopped budget state remain at `/home/ali/Documents/CrowdLens-reviews/2026-10-03-source-review-v2/run`. The [private artifact manifest](results/2026-10-03-source-review-v2/private-artifact-hashes.json) records hashes without mixing administrator evidence into the reviewer UI. Initial partial exports are retained separately; the usable export is `review-final`, with an original-results hash and zero-new-request receipt. Previously retained 99 original artifacts also match their prior hashes.

## Human review handoff — PENDING

The user will review in the [local browser page](http://127.0.0.1:18788/). Four packets contain all eight frozen current original documents and 19 actual ledger claims. Each candidate section is rendered from its actual blocked draft; the comparison summary is authored input, and actual proposed replacement spans are shown unapplied. These are drafts of blocked proposals, not ready or accepted report revisions.

Read original sources and write material reference facts before revealing each candidate. Use the manual timer only for active review. Review support, attribution, citation support, relevant conflicts and omissions; inspect premise-source chains for analysis claims. Additional assertions outside the ledger belong in notes. Enter your own reviewer ID and Human reviewer kind. Download JSONL or copy the prepared JSONL before closing/reloading: unsaved forms live only in the tab. Partial reference notes survive export without becoming assessed omissions. Supply the saved file path for verified import.

Packet UI omits model identity and automatic findings, but the user knows the collection method and aggregate blocked outcome; this is not a fully blinded study. No independent factual ratings or human review time have been supplied. Rates and effort remain null/PENDING. QA sentinel notes and timer measurements are explicitly technical probes, not human reviews. Imported disagreements must remain separate; one reviewer does not establish adjudicated truth.

## Verification and evaluation tooling repairs

Full repository check passed: 597 backend, 12 Node and 54 component tests (**663 total**) plus production build. Five focused evaluation tests passed again after the final instruction text. Browser QA verified four navigable packets, two full original sources per packet, unique field IDs, blank judgments, retained partial source notes in prepared JSONL, and manual timer start/pause/reset. Browser download-event verification timed out; the displayed copy fallback was verified. The page is left on Packet 1, candidate hidden, timer unmeasured, and all judgments blank.

Independent code review verified the collector preserves the four-case denominator when `WorkflowHalt` occurs; citation numbers follow ledger first-use order; analysis claims may omit direct citation fields; provenance notices do not misclassify actual outputs as scripted substitutes; control IDs are unique; and partial reference notes survive export and strict import without invented labels. An initially reported escaping issue was withdrawn after reproduction. These checks validate tooling, not source quality.

## Next step

Import the user's actual reviews and report reviewed/attempted denominators, unsupported-claim judgments, attribution/citation errors, omissions, disagreements and measured effort with unresolved values retained. Three cases encountered the summary-patch contract gate; repair that behavior on separate development data after review, then freeze fresh held-out cases for verification. Do not tune against this holdout or claim release readiness from these four packets. Exact-candidate remote CI/deployment reconciliation remains a separately scoped task.

## Authorized AI review follow-up

The user substituted GPT-6 Astra with maximum reasoning for their own review. The [completed AI assessment](results/2026-10-03-source-review-v2/astra-ai-review/review.md) covers four packets, eight originals and 19 exact ledger claims. Source-only facts were frozen before candidate inspection: 28 facts, with 10 judged materially omitted. Astra judged 17 claims supported, one unsupported and one ambiguous. These are single-AI-reviewer judgments, not human ratings or adjudicated truth. Human review status and time remain PENDING/null.

The coordinator verified packet hashes, exact claim coverage, typed judgments, reference IDs and null timing; the unchanged human importer correctly rejects these AI rows. All 47 previously preserved collection/reviewer artifacts remain unchanged. Application behavior, proposal states and human blank forms are unchanged. The AI review is shown separately at http://127.0.0.1:18789/.

Highest-priority next work is source coverage and attribution, alongside the previously observed summary-patch contract failures, implemented on separate development data and verified on fresh holdout inputs. The packet-level summary-target observations do not independently diagnose runtime behavior. Original drafts and AI judgments remain preserved.
