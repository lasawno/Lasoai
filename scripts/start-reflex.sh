#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root/apps/reflex"
if [[ ! -d .web ]]; then
  printf '%s\n' 'Run python3 scripts/setup_reflex.py from the repository root first.' >&2
  exit 1
fi
export REFLEX_TELEMETRY_ENABLED=false
# Reflex 0.10 production mode serves UI and Python events on one origin.
# This is a development preview, not a deployment to production hosting.
exec uv run reflex run --env prod
