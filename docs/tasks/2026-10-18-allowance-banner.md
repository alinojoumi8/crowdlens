# Separate workflow allowance counts

The allowance banner previously labeled only `in_flight` as “in flight or delivery unknown,” hiding completed requests with unresolved usage. It now renders `in_flight` and `unknown_usage_attempts` separately, with a note that the counts can overlap. Missing usage counts display “not reported,” rather than zero. Backend accounting, limits, renewal, and stop behavior are unchanged.

Verification:

- Four new regressions failed before implementation, covering stopped/unknown usage, overlapping counts, zero unknown usage and an omitted count. Viewing the banner makes no authorization, renewal or stop call.
- `UV_PYTHON=3.11 pnpm check` using Node 22 passed: 1,073 backend tests, 12 frontend Node tests, 110 component tests, and production build (1,195 total tests). The affected component tests passed again after a wording correction.
- Browser inspection against the live stopped workflow showed 39/60 total, 0 in flight and 1 with unknown token usage. Desktop 1440×1050 and mobile 390×844 were inspected; mobile had no horizontal overflow.
- CodeRabbit identified one minor wording issue (overlap is possible, not certain); corrected. A fresh follow-up CodeRabbit review completed on both changed files with zero findings. The intervening cached review was not counted as fresh validation.
- Lint/typecheck scripts are not configured. Hosted CI was not run.

No MiniMax requests were made or allowance renewed. The workflow remains stopped at 39/60 total with one historical unknown-usage receipt. Private evidence is in `/home/ali/.local/state/crowdlens/allowance-banner-20261018/`.

Local deployment: `8940f6ac94156a07951fec78473fc5483221c899`, healthy runtime fingerprint `48ae1b1a845468c88e5645fcdb313e06315e6e1712d9229e44c7e582ac7c9b7f`. Docker image built successfully. The backup was verified and rollback container `mirofish-offline-before-allowance-banner-20261018` retained. All 5,790 existing upload/report files and provider receipts remained unchanged. The deployed browser showed the expected stopped counts.

Next: publish the accumulated reviewed fixes through the canonical `alinojoumi8/crowdlens` pull-request workflow and run hosted CI. No PR currently exists for `codex/section-review-recovery`. A live check of the new concise-summary prompt remains a separate, explicitly authorized MiniMax test.

Atlassian backlog and runbook updates were read back at versions 42 and 18, with prior content preserved.
