# Homepage setup UI

Completed the four approved homepage improvements:
- Compact header and smaller brand illustration bring source selection into view sooner.
- Three setup steps: Upload documents, Describe scenario, Authorize and start. On narrow screens the setup form precedes the explanatory workflow panel.
- Plain-language workflow labels replace Reality Seeds, Graph Build, and Env Setup on the homepage.
- Visible status guidance explains missing inputs, provider availability, fingerprint preparation, and authorization. Disabled start styling and accessible descriptions clarify readiness.

Generation, authorization rules, fingerprinting, persistence, and API behavior are unchanged. The scroll shortcut now targets setup instead of the bottom of the page.

Verification: 12 Node tests and 54 component tests pass; production build and git diff whitespace check pass. Browser inspection completed at the normal desktop viewport and 390 x 844 mobile viewport, with no horizontal overflow on mobile. Source-only and source-plus-scenario inputs produced the expected guidance and button states. Inputs were cleared; no authorization or provider calls were initiated. Viewport override was reset.

Local review URL: http://127.0.0.1:18810/
