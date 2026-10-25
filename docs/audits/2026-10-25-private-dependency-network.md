# B11 first slice: inventory and private-network preparation

Scope: consumer inventory and a host-compatible Compose override, based on merged B10 main `9461e3a8ed146bd5eab56caa45d2c4b38c7c6703`. Running shared services, credentials, model/graph data and the B10 staging release are not migrated by this change.

## Read-only observations

- Running Neo4j HTTP/Bolt and Ollama listeners/mappings publish on IPv4/IPv6 wildcard ports 7474/7687/11434. The existing base Compose file instead specifies loopback: there is confirmed runtime/configuration drift.
- The CrowdLens application uses `neo4j:7687` and `ollama:11434` on `mirofish-local_default`. An active host Graphiti MCP process has established connections to `localhost:7687`; its selected embedding configuration uses `localhost:11434`. Other Graphiti configuration shares Ollama while pointing at its separate Neo4j on 7690. This prevents treating the dependencies as Docker-only services.
- The inventory found seven stopped/running container endpoint candidates, three visible process endpoint candidates and four explicitly inspected configuration files. 1,164 process environments were inaccessible at capture time. Those counts are a dated observation, not exhaustive discovery or proof that each configured endpoint is actively used.
- Observed immutable images: application `sha256:6b28dd78e5fe4b1b21a2879d612f519f8229a84c31f9ea56315504fb0f6bfe7e`, Neo4j `sha256:8f01f7bb053e5564eb84a3f1824e4ca2202d29dd415d196cf8e27c8f7e6b611e`, Ollama `sha256:a6149234667efc71d37766d61c1a16f24c33e4cd7a0bf4125c44a7e47e2419c4`. Ollama reports 0.24.0. The overlay freezes these current images rather than performing an upgrade or applying the base file's different Ollama tag.
- Docker Engine is 29.8.1 and Compose is 5.1.3 on this host. CodeRabbit identified the older-Engine same-L2 loopback exposure as a Major prerequisite issue; the preflight now requires Engine >= 28.0.0 and Compose >= 2.24.4 and rejects old/unrecognized versions. Real same-LAN/external-client denial remains unverified, independently of that version gate.

## Prepared policy and evidence

The private override replaces host port lists, pins current images without pulling/building, preserves legacy data/project/service identities, retains host loopback consumers and separates dependency network membership from the application's default bridge. It does not deny dependency egress or constitute database authorization.

Focused tests exercise endpoint-only redaction, invalid/unrelated URLs, secret-field omission, absent targets and process/configuration evidence limits. Docker Compose renders are checked both with/without the GPU override and with wildcard/extra ports deliberately injected into the base. The resulting ports must all be loopback, images must remain pinned despite ambient image variables, service DNS must survive, and legacy volume names must remain unchanged.

A disposable synthetic Compose project rendered the actual base/private overrides with a final fixture layer. All three services used the same existing Python-capable image, fictional environment only, no application/data mounts and fresh network names. The fixture replaced container names, entrypoints, ports and health checks before startup. It exercised the real bridge topology and loopback-only publication without running a database, model service or application workflow:

- Host loopback requests reached all five dynamically assigned fixture ports.
- The application fixture reached the Neo4j/Ollama fixture endpoints using service DNS.
- A peer on the application's default bridge could not connect directly to the Neo4j fixture on the separate dependency bridge.
- Inspect confirmed loopback-only mappings, expected network membership and no existing mounts.
- The rehearsal's containers/networks were stopped and removed normally. Before/after IDs, start times, images, port mappings and network metadata of the three real services matched exactly.

Private inventory, copied fixture manifests, rehearsal script/logs and receipt are retained at `/home/ali/.local/state/crowdlens/b11-20261025-5vtmy6ai/`. No raw environment dump, database query, generation, embedding or provider allowance renewal was used. [The runbook](../private-dependency-network.md) explains the gate for actual application and rollback.

This audit records the first-slice evidence. Full test/build, CodeRabbit and hosted-CI results belong to the delivery receipt/PR when completed; this text does not assert an unperformed check. Actual service migration, unknown/remote consumer confirmation, authorized external-client/firewall acceptance, credential rotation and broader B11 acceptance remain open.
