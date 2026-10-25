# B11: consumer inventory and prepared private networking

This first B11 slice prepares an existing-host network migration. It does not change the running stack, rotate credentials, upgrade Neo4j/Ollama, or connect the provider-disabled B10 stack to them. Live service recreation, firewall/external-client acceptance and credential rotation remain later coordinated steps.

## Observed consumers, October 25, 2026

| Consumer | Dependency route | Evidence and migration implication |
| --- | --- | --- |
| Running `mirofish-offline` | `bolt://neo4j:7687`, `http://ollama:11434` | Container environment and shared `mirofish-local_default` network. Preserve service DNS and the application image. Hosted inference uses a separate configured provider; no provider request was made. |
| Host Graphiti MCP (`graphiti-mcp-legal.service`) | `localhost:7687`; configured `localhost:11434` embeddings | Running process environment plus established Neo4j TCP connections. Selected Graphiti configuration also names Ollama. Keep host loopback access; no generation/embedding query was used to check this. |
| Other host Graphiti configuration | `127.0.0.1:11434`; its own Neo4j at `127.0.0.1:7690` | Configuration evidence only; `graphiti.service` was restarting, not verified healthy. Do not modify the separate `graphiti-neo4j` database. |
| Host MiroFish backend/bridge | Configured Graphiti bridge on `127.0.0.1:8011` | Potential indirect Ollama consumer through the Graphiti configuration. Backend/frontend units are running; this does not establish a successful bridge journey. Confirm the selected bridge configuration before migration. |
| Checkout-local developer configuration | `localhost:7687`, `localhost:11434` | Configuration hints for future host runs, not proof of an active developer process. |
| Stopped CrowdLens application/verification containers | Service DNS or host-gateway access to the same dependency ports | Rollback/restart candidates. Review their network attachments before restarting them after a topology change. |
| B10 staging application | Closed local port 9 for model/graph endpoints | Intentionally provider-disabled; not a consumer of these shared dependencies. Its separate state/CA/network remains unchanged. |

Current live Neo4j HTTP/Bolt and Ollama mappings are wildcard IPv4/IPv6 on 7474/7687/11434, despite the base Compose file already specifying IPv4 loopback. Config changes alone do not reconcile an existing container. Listeners were confirmed with `ss`; this is not proof of Internet reachability or a complete firewall audit.

Refresh the endpoint-only inventory into protected storage:

```bash
umask 077
python scripts/dependency_inventory.py --config .env --config /protected/selected-graphiti.yaml > /protected/consumer-inventory.json
ss -tnp '( dport = :7687 or dport = :11434 or dport = :7474 )'
```

Pass only configuration files selected for the actual consumers. The collector reads Docker metadata, readable process environments and explicitly supplied env/YAML/TOML configuration files. Only allowlisted endpoint fields produce hints; prompt/description fields are ignored. It emits endpoint protocol/host/port only, omitting URL credentials/path/query/fragment, other environment values, arbitrary labels and bind-source paths. Raw credentials and source documents are not exported. Active Docker port mappings are reported separately from requested bindings, including stopped-container restart candidates. It lists missing target containers and inaccessible process counts, and exits nonzero if required containers are absent or Engine/Compose version prerequisites fail. Code defaults, unreadable processes, dynamic endpoints, other client machines and unselected configuration can be absent: this is a review inventory, not automatic proof that every consumer was found. Keep even the redacted report private because it contains local topology and file names.

## Prepared configuration

Use `deploy/private-network/compose.yaml` **last**, after the root Compose file and optional GPU override. Require Docker Engine 28.0.0 or newer and Compose 2.24.4 or newer. The preflight rejects older/unrecognized versions. Engines older than 28 can expose loopback-published ports to same-L2 peers; this manifest does not support those engines as a firewall workaround. Port lists are replaced completely using `!override`, including unsafe extra ports in an older base. All five retained host ports bind to IPv4 loopback. Same-LAN/external denial must still be checked during coordinated acceptance. See [Docker's publishing boundary](https://docs.docker.com/engine/network/port-publishing/).

The application keeps the existing `default` bridge for its configured outbound provider path and joins a new `dependencies` bridge. Neo4j and Ollama join only `dependencies`. This removes them from the application's ingress/default network while preserving direct service DNS. Host clients retain `127.0.0.1:7474/7687/11434` access.

The dependency bridge is deliberately **not** `internal: true`: this slice retains host-published dependency access and outbound model-provisioning compatibility. It constrains inbound publication and network membership; it is not an egress-denial sandbox, database authorization, or protection from an administrator who can attach containers. No model provisioning is performed by this change. B10's independent internal application network is not changed.

The overlay pins the observed Neo4j 5.18 image digest and the observed Ollama image digest (runtime version 0.24.0), rather than adopting either `latest` or the base file's newer Ollama tag. It also pins the currently running application image by local immutable ID and removes its build configuration. `pull_policy: never` prevents implicit downloads; the exact images must already be present. This is a host-specific migration manifest, not a portable release recipe or a claim that these versions are current. Re-inventory/review pins if runtime images change. Dependency upgrades and deployment of a new application revision are separate operations.

The legacy project, service/container names, application bind mount and named Neo4j/Ollama volumes remain intact. The new dependency network is the only additional network; do not choose a different Compose project and accidentally create fresh databases.

Validate without starting or replacing services:

```bash
umask 077
python scripts/dependency_inventory.py --config .env > /protected/consumer-inventory.json &&
docker compose --project-name mirofish-local --env-file .env -f docker-compose.yml -f deploy/private-network/compose.yaml config --quiet
# GPU installations: put -f docker-compose.gpu.yml before the private override.
```

Rendered Compose JSON can contain credentials from service env files. Use `config --quiet` for ordinary validation; protect any operator-only rendered snapshot and never commit it. The tests render only copied manifests and fictional environment files. The `!override` boundary applies to this reviewed file ordering; do not append an unreviewed override afterwards.

## Coordinated application and rollback gate

1. Refresh consumer/connection inventory and obtain owner confirmation for configured, stopped, remote and unreadable consumers. Require the Engine >= 28.0.0 / Compose >= 2.24.4 preflight to pass before recreation. Record the active application/dependency IDs, aliases, volume names, selected Compose files, image digests and protected credential configuration. Capture the original network topology and protected rollback inputs; the redacted inventory alone cannot recreate an entire deployment.
2. Recheck the existing backup/recovery receipt and a maintenance window. Quiesce owned workflows and pause affected host consumers. Verify that the candidate keeps the intended provider settings and credentials and that the pinned images are present. Do not infer compatibility from image tags alone.
3. After the coordinated change is authorized, recreate the affected application/dependency containers together using the reviewed project, data, images and override order. This has a connection interruption. Do not apply only the dependency half while leaving the application on its old network.
4. Verify actual listeners/mappings and container networks, authenticated database access, selected host consumers, application service DNS and the intended ingress. Verify denial from an unauthorized external client. Provider inference/embedding tests require an explicit allowance; metadata/TCP checks do not prove those workflows.
5. If a consumer fails, stop new work, restore the recorded previous network/configuration/images on the same project and volumes, and verify recovery before resuming. Older stopped application containers may need their original dependency topology restored. Keep generated data and retained rollback artifacts.

The actual runtime change, host firewall/external-device checks, secret-storage/rotation and minimal-public-diagnostics work are still open B11 acceptance. These are not completed by rendering the overlay or passing the synthetic rehearsal. See the [first-slice audit](audits/2026-10-25-private-dependency-network.md) for observed evidence and limits.
