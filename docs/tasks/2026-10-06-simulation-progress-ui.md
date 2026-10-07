# Simulation progress UI

Completed the approved simulation-screen clarity pass using the existing ECC interface guidance.

| Area | Before | After |
| --- | --- | --- |
| Run status | Raw status and technical labels | Plain-language status summary, Public feed, Discussion community, and Run status labels |
| Next action | Disabled report button without an explanation | Visible report-readiness guidance; stopped and failed runs explicitly retain partial activity |
| Settings | Long configuration line always visible | Expandable Run settings and limits |
| Activity | Generic waiting state; narrow mobile timeline cards | State-specific empty messages and full-width mobile activity cards |
| Layout | Initial split view; fixed control-bar height | Initial workbench view, wrapping controls, mobile scrolling, and 44px action targets |

Simulation execution, polling, stop behavior, allowance checks, accounting, and report-generation eligibility remain unchanged. Start errors are now surfaced as alerts. Existing label assertions were updated without removing count or runtime-state checks.

Validation: 12 Node and 54 component tests passed; production build and whitespace checks passed. Browser inspected idle, running, and stopped states using an explicitly labeled, read-only fictional API fixture. At 390 x 844, page width matched viewport width and the activity card remained readable above the system log. No live provider calls, simulation mutations, or report generation occurred. Temporary viewport override was reset.

Fictional UI preview: http://127.0.0.1:18813/simulation/ui_running/start
