#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root/apps/reflex"
if [[ ! -d .web ]]; then
  printf '%s\n' 'Run python3 scripts/setup_reflex.py from the repository root first.' >&2
  exit 1
fi
# Do not launch a second server over a lingering listener.
python3 - <<'CHECK_PORT'
import socket
with socket.socket() as listener:
    listener.settimeout(0.5)
    if listener.connect_ex(("127.0.0.1", 3000)) == 0:
        raise SystemExit("Port 3000 is already in use. Run python3 scripts/stop-reflex.py from the repository root before restarting.")
CHECK_PORT
export REFLEX_TELEMETRY_ENABLED=false
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  # Private forwarding can load HTTPS while rejecting the WebSocket upgrade.
  # Use Reflex's supported HTTP event transport, without changing authentication.
  export REFLEX_TRANSPORT=polling
  # Engine.IO polling sessions must stay on one process.
  export GRANIAN_WORKERS=1
fi
# Reflex 0.10 production mode serves UI and Python events on one origin.
# This is a development preview, not a deployment to production hosting.
exec uv run reflex run --env prod
