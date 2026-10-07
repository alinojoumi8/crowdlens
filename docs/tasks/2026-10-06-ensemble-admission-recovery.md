# Ensemble admission and allowance recovery

## Runtime finding

User browser: simulation `sim_123b39057e21`, associated with Attio project `proj_f63abe1dc246`. The system log records rejection of the ensemble submission with `runtime_limit`. Workflow `wf_aa3b80e28b5b40b280ba04c804e661d8` had a 60-request, 1800-second allowance and had admitted 39 requests. At investigation, no requests remained in flight, admission was closed, and usage was in ontology, graph, profiles, and configuration stages. The simulation status endpoint returned `idle`, zero rounds, and zero actions. No simulation-stage provider calls were recorded. The rejected ensemble was not admitted and did not reset backend run state.

## UI corrections

- Offer ensemble generation only after the first simulation reaches `completed`, consistent with the workflow described by the existing component.
- Restore the prior phase and run status after rejected ensemble admission, preserving access to completed activity/report controls rather than leaving a false running phase and generic Error header.
- Display ensemble failure messages beside the controls, including actionable runtime-limit guidance. Keep the ensemble card visible after failure. Polling failures retain partial activity and settle the phase instead of leaving a permanent busy state.
- Add explicit allowance renewal controls for closed workflows. Show provider/model, total request ceiling including consumed calls, and minutes from renewal. Require acknowledgment for outstanding calls; preserve idempotency for retries and use new keys for changed terms. Renewal calls the existing fenced backend endpoint and never starts or retries generation automatically.

## Verification

Frontend tests: 12 unit + 61 component passed. Regression checks cover idle ensemble gating, rejected admission with completed-state preservation, explicit-only renewal, and outstanding-request acknowledgment. Production build passed. Browser inspection confirms the live page displays Idle / Not started, a disabled ensemble button with first-run guidance, and the expired workflow's renewal controls. No new paid simulation or ensemble was started during this fix.

Browser evidence: `/tmp/crowdlens-ensemble-recovery.png`. The next operator action is to choose limits and renew the allowance, then manually start the first simulation. A five-seed ensemble remains an optional later run; the 21 requests remaining under the old total ceiling are not a guarantee that a full simulation or ensemble can finish.
