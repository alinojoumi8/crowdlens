# Autonomous activity outcomes and deterministic smoke activation

The Cedarbrook canary finished two rounds with setup/scheduled posts but zero
model responses. Run lifecycle completion is now displayed as rounds ended;
recorded activity separately identifies no autonomous activity, unverified
provenance, actions without writing, or written responses. Successful runtime
model-origin actions require explicit success, valid agent/round IDs, and authored
nonempty post/comment/quote text to establish a written response. Inputs, no-ops,
failures and legacy unknown origins cannot establish discussion. Recorded writing
is not a quality, coverage, consensus or forecast-accuracy judgment.

Preparation exposes opt-in `activation_mode=smoke_round_robin`. It rotates unique
agent IDs on the runtime's zero-based rounds, capped by the configured active
agent limit, bypassing sleep hours and probability only for this explicit test
mode. Normal stochastic activation is unchanged. Model actions still use the
existing transport and workflow limits; scheduling does not guarantee a response.
Changing the mode of an already-prepared simulation requires explicit regeneration
or a new simulation. Saved settings and effective configuration retain the mode.

Smoke disclosure is frozen in report grounding, shown in activity accounting,
provided to section generation, and added deterministically to saved/downloaded
Markdown. The notice is not a quotation and passes the existing provenance guard.
Historical reports and runner terminal states are not rewritten by this change.

Validation: 971 backend tests, 12 frontend unit and 89 component tests, production
frontend build. New tests cover zero-activity outcomes across lifecycle states,
authored text and explicit provenance, deterministic round rotation and caps,
normal-mode compatibility, prepared-mode conflict, actual action-logger output,
report freeze/reload/Markdown and quotation validation. A provider-disabled browser
fixture displayed ended rounds with no autonomous activity and explicit smoke
limitations; opening it did not launch a simulation. No hosted test is claimed.

Independent AI subagent review found and verified corrections for zero-based round
rotation, an initial UI null state and Markdown blockquote/provenance conflict.
Its final review reported no remaining blocking findings and independently passed
the six new outcome/report tests. This is AI review, not human quality ratings.

Deployment and exact-revision CI evidence are recorded separately in the Confluence
backlog/runbook and the private zero-activity-20261013 deployment receipts. A future
hosted acceptance test requires its own allowance and actual autonomous action plus
transport receipts; deterministic scheduling alone does not satisfy it.
