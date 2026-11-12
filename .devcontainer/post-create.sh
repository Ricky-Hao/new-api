#!/usr/bin/env bash
set -euo pipefail

maintenance_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec bash "$maintenance_root/tools/prepare.sh" "$@"
