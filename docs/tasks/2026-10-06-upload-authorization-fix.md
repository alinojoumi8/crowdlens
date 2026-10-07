# Website and PDF authorization failure

## Finding

The running browser app at port 18810 returned HTTP 400 from `/api/execution/authorize`, before the upload endpoint ran. The response reason was `secondary_provider_allowance_unsupported`. The backend inherited optional Jev modes from the primary checkout environment. Workflow allowances cover the primary configured provider and local embeddings, so rejecting that secondary-provider configuration was intentional.

## Correction

- Restarted the integration backend on loopback port 18811 with `JEV_INTERVIEW_MODE`, `JEV_RERANK_MODE`, and `JEV_EVIDENCE_MODE` set to `off` after loading the existing environment. The primary `.env` was preserved.
- The configuration endpoint now exposes `authorization_blocker` using the same guard as authorization. The frontend disables authorization and explains how to correct unsupported configuration before submission.
- HTTP errors preserve their Axios response/status while surfacing the server's error reason. Workflow controls translate known configuration errors into actionable messages.
- README records the process overrides needed for future restarts. Provider authorization checks remain enforced.

## Verification

- Frontend: `npm test` — 12 unit tests and 57 component tests passed.
- Backend: `UV_PYTHON=3.11 uv run pytest tests/test_execution_api.py -q` — 16 passed, including each secondary-provider mode blocking authorization and recovery after disabling it.
- Production frontend build passed; `git diff --check` passed.
- Actual browser + MiniMax-M3, Attio website: authorization succeeded; ontology and graph completed. Project `proj_f63abe1dc246`, graph `8f7bdac3-4852-4a93-aac3-e4f513516ce5`: 32 nodes and 14 edges. Two admitted provider requests, none in flight when checked.
- Actual browser file chooser + MiniMax-M3, newly created fictional PDF: authorization succeeded; PDF text parsing, ontology and graph completed. Project `proj_19d44a043e74`, graph `e6129acd-7525-431f-8395-373d0837289c`: 3 nodes and 2 edges. Two admitted provider requests, none in flight when checked.
- Both results remain open at `http://127.0.0.1:18810/process/<project_id>` for review. Browser screenshots saved to `/tmp/crowdlens-attio-upload-fixed.png` and `/tmp/crowdlens-pdf-upload-fixed.png`.

These checks establish successful input ingestion through graph creation. They do not establish full simulation/report completion, factual quality of generated entities, or product-launch forecasting accuracy. The user's original PDF was not used; a fictional test PDF verified the attachment path.
