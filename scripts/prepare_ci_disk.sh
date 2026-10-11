#!/usr/bin/env bash
# Only for disposable GitHub-hosted Linux runners, never an operator's host.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != true || "${RUNNER_ENVIRONMENT:-}" != github-hosted || "${RUNNER_OS:-}" != Linux ]]; then
  echo 'Refusing SDK cleanup outside a GitHub-hosted Linux runner.' >&2
  exit 1
fi
# CrowdLens needs Python/Node/Docker; these preinstalled SDKs are unused.
sudo rm -rf /usr/local/lib/android /usr/share/dotnet
available_kib=$(df -Pk / | awk 'NR == 2 {print $4}')
if (( available_kib < 35 * 1024 * 1024 )); then
  echo 'At least 35 GiB free is required for dependency cache, image export and smoke loading.' >&2
  df -h /
  exit 1
fi
df -h /
