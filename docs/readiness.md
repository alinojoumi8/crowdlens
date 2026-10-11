# Readiness without inference

The home page displays `/api/status` checks instead of a fixed Ready label.
`/health` remains Docker process liveness. HTTP 200 from status does not mean
dependencies passed; inspect `readiness` and the individual states.

Generation and embedding probes never submit prompts, generate vectors, pull
models or retry inference. Ollama uses [GET /api/tags](https://docs.ollama.com/api/tags).
MiniMax/OpenAI-compatible configuration uses the endpoint's
[GET /models](https://platform.minimax.io/docs/api-reference/models/openai/list-models).
Checks have 1-second connect and 2-second read timeouts, a 4-second body deadline,
a 256 KiB body limit, no redirects/retries, and a 60-second process-local cache.
Concurrent requests share one check; another reader sees checking while it runs.
Gemini embeddings use [model metadata](https://ai.google.dev/api/models) with the
API key in a header; incomplete pagination remains unverified. Metadata checks
still make network requests to the configured provider.

| State | Meaning |
| --- | --- |
| unconfigured | Endpoint/model/required credential is missing or invalid. |
| reachable | The selected model is listed. Inference remains untested. |
| missing_model | The returned complete model list lacks the selected model. |
| unavailable | Timeout, connection, authorization or other HTTP failure. |
| unverified | Metadata unsupported, unfamiliar provider/format or incomplete list. |
| checking | Another metadata check is running. |

Unknown is never promoted to inference success. `inference_verified` stays false;
a generation canary requires separate workflow authorization. The existing
MiniMax-M3.1-Flash-Preview selection is retained. Its configured endpoint returned
unsupported model metadata in the 2026-10-10 read-only check, so readiness is
honestly unverified, not a proven inference outage.

Storage probes cover actual uploads, resolved report storage and the control
database directory. Each cached check measures available bytes/inodes and writes,
flushes, fsyncs and removes a private temporary file as the app user. Missing or
unwritable storage is unavailable; less than `DISK_CRITICAL_BYTES` (512 MiB by
default) is critical; less than `DISK_WARNING_BYTES` (2 GiB) is a warning. These
are snapshots, not reservations or guarantees that a run fits. Low space is
reported at startup and in the UI; liveness stays separate to avoid restart loops.
Existing operation-specific admission and error handling remain.

Offline verification passed 874 backend tests, 92 frontend tests and build.
Cases cover simultaneous polling, cache invalidation, denied/unsupported metadata,
missing models, timeouts, response bounds, local tags, actual writes, low space
and write denial. The embedding regression forbids inference and model pulls.
Fictional browser checks cover ready, missing model and low-space states.
