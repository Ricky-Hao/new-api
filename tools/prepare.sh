#!/usr/bin/env bash
set -euo pipefail

maintenance_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
application="$maintenance_root/.work/application"

python3 "$maintenance_root/tools/patchset.py" branch --target "$application" "$@"

for cache in "${GOCACHE:-}" "${GOMODCACHE:-}" "${BUN_INSTALL_CACHE_DIR:-}"; do
  if [[ -n "$cache" ]]; then
    mkdir -p "$cache"
  fi
done

for module in . relaykit tokenkit; do
  (cd "$application/$module" && GOWORK=off go mod download)
done

# The backend embeds web/dist; prepare real assets in the generated application.
(cd "$application/web" && bun install --frozen-lockfile && \
  DISABLE_ESLINT_PLUGIN=true VITE_REACT_APP_VERSION=$(cat ../VERSION) bun run build)
python3 "$maintenance_root/tools/patchset.py" verify --target "$application"
