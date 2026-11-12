#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

mkdir -p "${GOCACHE}" "${GOMODCACHE}" "${BUN_INSTALL_CACHE_DIR}"

GOWORK=off go mod download
(cd relaykit && GOWORK=off go mod download)
(cd tokenkit && GOWORK=off go mod download)

# The backend embeds web/dist, so prepare real frontend assets before Go builds.
(cd web && bun install --frozen-lockfile && bun run build)
