# Fictional bike-lane run request accounting — 2026-10-03

The previous authorization admitted **30 MiniMax-M3 requests**, with one further
request blocked locally. It is exhausted and provides no authorization for
recovery or another run. Report generation and proposal review did not complete.
This repair pass used zero external generation requests.

Original evidence is preserved under
`/home/ali/Documents/CrowdLens-reviews/2026-10-02-bike-lane/`:
`budget/requests.jsonl`, `budget/state.json`, `test-result.md`, and
`evidence-at-original-limit/`. The [derived accounting JSON](evidence/2026-10-03-control-recovery/historical-request-accounting.json)
records receipt times, stage assignments, counts and token categories. The
[allowlisted raw receipt copy](evidence/2026-10-03-control-recovery/historical-relay-requests.jsonl)
contains no prompts, response bodies or credentials.

| Stage | Physical request numbers | Count | Input tokens | Output tokens | Cache-read input tokens | Assignment confidence |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Ontology | 1 | 1 | 1,704 | 2,430 | 134 | Matched stage timing/logs |
| Source graph | 2 | 1 | 1,359 | 917 | 128 | Matched stage timing/logs |
| Agent profiles | 3–6 | 4 | 4,010 | 6,959 | 528 | Matched stage timing/logs |
| Simulation configuration | 7–9 | 3 | 3,079 | 2,396 | 402 | Matched stage timing/logs |
| Graph memory | 10, 11, 12, 15, 16, 20, 21, 22, 25, 27, 28 | 11 | 7,910 | 6,567 | 7,261 | Matched stage timing/logs |
| Simulation responses | 13, 14, 17, 18, 19, 23, 24, 26 | 8 | 30,115 | 2,326 | 4,102 | Inferred by exclusion; individual platform/agent unknown |
| Report outline | 29 | 1 | 936 | 499 | 133 | Matched stage timing/logs |
| First section planning | 30 | 1 | 3,292 | 96 | 128 | Matched stage timing/logs |
| **Total upstream** | **1–30** | **30** | **52,405** | **22,190** | **12,816** | All receipts have upstream HTTP 200 |
| Local allowance rejection | 31 | 0 upstream | Unknown/not applicable | Unknown/not applicable | Unknown/not applicable | HTTP 403 from the relay; no upstream submission |

The first request started at Unix time `1790995662.7876046`; the authorized
deadline was `1790996562.7876046` (900 seconds). The last response finished at
`1790996303.2305474`, **640.443 seconds** after the first admission. Counts reached
the ceiling before the time window ended. The relay's final state also records
deadline shutdown. It does not prove that every historical application worker
had a correct terminal state.

Stop was requested at approximately `2026-10-03 02:57:58 UTC`. Graph-memory
requests 27 and 28 were admitted afterward. This supports the reproduced
shutdown-drain defect. The historical monitor also marked an incomplete sample
Completed: Twitter 5/10 rounds, Reddit 6/10 and 50 logged actions. The report
remained interrupted with no finished sections. These artifacts are preserved
as failed/partial evidence, not relabelled as successful.

## Unknowns and billing interpretation

The relay retains request/response byte counts, hashes, times, status and provider
usage, not prompt/response bodies or workflow/task/retry identifiers. Stage
reconstruction is therefore approximate where concurrent work overlaps. It
cannot identify each simulation agent/platform or prove logical retries from
these receipts alone. HTTP 200 does not certify meaningful model output.

Token categories are measured response metadata. Whether the reported input
category already includes cache-read tokens, the account's rate/plan, taxes,
rounding and actual invoice are unverified. Missing categories are unknown.

As checked on 2026-10-03, MiniMax's published Standard M3 rates for requests at
or below 512k input tokens are USD $0.30/M input, $1.20/M output and $0.06/M
cache reads. Priority costs 1.5 times Standard and larger inputs use higher
rates. [Official pricing](https://platform.minimax.io/docs/pricing/overview).

Applying those Standard rates conditionally to this usage gives **$0.03927–
$0.04312**, depending on cache/input overlap. This is a calculation, not an
observed bill. Doubling historical average usage to 60 requests suggests about
**$0.08–$0.09**; it does not measure a completed report/proposal workflow.

The [fresh acceptance plan](../visible-browser-acceptance.md) instead provides
a larger planning scenario: 60 attempts × 16k input/8k output tokens gives
**$0.864** before any cache savings. The proposed approximately $1 planning
allowance is not an enforced dollar cap. Physical request count and runtime
are enforced; total token spend still depends on actual prompts and output.

## Recovery preserves history

The preserved copy is at
`/home/ali/Documents/CrowdLens-reviews/2026-10-03-control-recovery/recovery-inputs/`,
with adjacent `recovery-inputs-sha256.json` and a
[copy receipt](evidence/2026-10-03-control-recovery/recovery-copy.json).
No generation has run on it. A legacy attachment must import the **30 consumed
requests**, preserve the original receipts, and obtain a separately approved
new total ceiling. The proposed recovery ceiling is 60 total (30 historical
plus at most 30 new), on the copy only. It is neither authorized nor equivalent
to a fresh end-to-end run.
