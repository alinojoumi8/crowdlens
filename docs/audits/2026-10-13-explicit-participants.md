# Explicit participant selection

The October 13 live Cedarbrook canary selected a municipality under the four-agent
cap and omitted the requested shop owner. Type coverage did not preserve the named
roster. This change adds `participant_ids` as an exact entity-ID roster, selectable
by name/type/ID in environment setup. Empty selection retains automatic type
coverage. Explicit selection neither fills unused slots nor silently truncates.

Missing IDs, duplicate/malformed IDs, conflicting type filters and a roster larger
than the cap fail validation. The preparation endpoint checks the roster before
creating a background task or generating profiles, and returns 503 when the graph
cannot validate an explicit roster. The worker repeats validation against its
current graph read before profile generation. Names and types of selected entities
persist in the coverage receipt; omitted eligible entities are listed explicitly.
Saved prediction settings restore the exact selection in the UI.

Validation: 961 backend tests; 12 frontend unit tests and 85 component tests;
production frontend build. Regressions cover the Cedarbrook four-person roster
through profiles, config and persisted state, stale/missing IDs, filter conflicts,
cap overflow, graph outage before dispatch, duplicate names distinguished by IDs,
UI blocking and restored request payloads. The existing backend suite includes
PDF/text workflow integration with declared synthetic generation stages.

Browser verification used the current production frontend build in the disposable
provider-disabled browser harness, with five fictional entity nodes substituted
and an unprepared simulation. Selecting five entities under a cap of four disabled
Prepare and displayed the reason; selecting Maya, Leo, Priya and Daniel enabled
Prepare and left Cedarbrook unselected. The screenshot is in
[evidence](evidence/2026-10-13-participants/explicit-roster.png). Backend generation
was not invoked by this browser check. No hosted rerun or production deployment is
claimed by these local tests. The previous live artifacts remain unchanged.

This fixes roster control, not prompt-based name extraction, balanced viewpoints,
zero-reaction runs, terminal-state cleanup, or summary-scope validation. Those
follow-up items remain in the Confluence delivery backlog.
