# B09 ingestion and generated-output boundary

The private pilot accepts fictional PDF, TXT and Markdown sources, plus public
HTTP/HTTPS HTML, text and PDF responses. Text decoding respects declared encodings with bounded detection fallback; HTTPS verification uses the installed CA bundle, independent of worker environment overrides. Originals remain private project
artifacts; they are not served as executable web content. Invalid sources reject
the entire new ingestion batch before ontology/model work or case-version
publication. Newly created rejected-project files are removed. No antivirus or
external scanning service receives uploads. File signatures, decoded text checks,
resource limits and inert output are layered controls, not malware certification.

## Fixed resource envelope

| Boundary | Limit / behavior |
| --- | --- |
| HTTP request | 50 MiB including multipart overhead; 64 KiB form memory and 32 parts |
| File | 50 MiB; PDF header required at byte zero; known binary magic/control bytes rejected for text |
| Batch | Eight sources; eight million extracted characters; no silently skipped invalid file/URL |
| Extraction | Four million characters per source; 3,000 PDF pages; one scanned page per source, preflighted before OCR; encrypted PDFs rejected |
| OCR | Local Tesseract only; 16 million rendered pixels per page; 60 seconds per OCR subprocess |
| Worker | 120 seconds wall time, 90 seconds CPU per process, 768 MiB virtual address space, 64 file descriptors |
| Worker output | File-backed, with a fixed file-size limit; the parent reads at most that envelope |
| URL | HTTP/HTTPS standard ports only, no credentials, five redirects, five MiB body, 20-second total response deadline plus worker wall limit |
| Rendered Markdown | 200,000 displayed characters; explicit display-limit notice; saved report remains unchanged |

Workers start with isolated Python startup, closed inherited descriptors, a new
process group and an environment without provider keys, proxy settings or Python
startup hooks. Whole-group cleanup terminates OCR descendants on timeout and on
completion. OS limits are installed before native parsers load. This is resource
and process separation, **not an arbitrary-code/filesystem sandbox**: an exploited
native parser still runs as the app OS user. Keep the non-root container, private
fictional-data scope and tester gate. External hostile multi-tenant use needs its
separate B23 security acceptance and appropriate host isolation.

B08's durable account/workspace/global cumulative logical-write quotas and active
operation admission continue to apply; batch and parser caps do not renew those
quotas or claim to measure physical disk occupancy. Oversized or unsupported
sources must be split or omitted explicitly and resubmitted; truncation is not
source-completeness evidence. Scanned PDFs require local OCR; an unavailable OCR
engine rejects rather than drops the page.

## Network and browser behavior

Every source hostname is resolved once for each hop. All returned addresses must
be globally routable; mixed/private/shared/metadata, mapped and translated address
forms fail closed. The connection pins a validated IP while preserving the
original HTTPS hostname for certificate verification and SNI. Redirects are
manual; each new hop repeats validation. Environment proxies, netrc credentials,
cookies and model-supplied destinations are not used. Unsupported media types,
compressed responses, oversized/incomplete bodies and stalled reads reject with
closed connections. The worker wall limit also bounds DNS and header waits.

Raw source/model HTML stays escaped. External font requests are removed to honor the same-origin policy. Source links are not converted to executable
Markdown links or remote images. CSP restricts scripts and connections to the same
origin, disallows plugins/base changes/framing and restricts form destinations.
Downloads are attachments with an octet-stream type, `nosniff`, a sandbox CSP and
no-store. Security headers cover public, authenticated and error responses;
OIDC mode does not enable cross-origin API CORS. HTTPS-configured OIDC adds HSTS.
Production browser API use must be same-origin; cross-origin build overrides are
not compatible with this pilot policy.

Generated Neo4j labels require simple ASCII identifiers (up to 64 characters) before caching, embedding or writing; invalid older cache entries are treated as misses so a valid retry can replace them; label lookups pass the label as a query parameter.

Model-proposed report tools require an allowlisted name and object arguments.
Disabled interviews remain disabled; graph/simulation/workspace, URL and file
path destinations cannot be supplied by a tool call. Search result counts remain
bounded. Prompt guidance labels source instructions as data; server checks, scope
ownership and workflow allowances provide the enforcement boundary. These controls
do not establish that a model will always resist semantic prompt injection or
produce factually correct claims.

## Verification and delivery

`backend/tests/test_ingestion_hardening.py` exercises hostile and valid sources,
real disposable-worker failures, descendant termination, credential isolation,
HTTP payload errors, DNS/connection pinning, redirect/response bounds, ingestion
rollback, tool scope and response headers. Existing source-retrieval, OCR,
workspace and quota suites remain regressions. Frontend component tests cover
stored script/image/SVG/link payloads, malformed output objects and bounded
rendering. All testing is offline; no provider allowance is implied.

Local tests and a local image do not replace hosted CI, deployment identity or
external acceptance. Open the focused B09 PR, run hosted CI, then obtain merge
approval and verify main. The next roadmap area is B10 clean private staging with
HTTPS, constrained by the user's local/private scope and no-new-paid-services
decision, followed by B11 observed network/secrets hardening. Tester access stays
gated while remaining acceptance work is open.

Design references: [OWASP file upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
and [OWASP SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
These references support layered controls; they do not certify this implementation.
