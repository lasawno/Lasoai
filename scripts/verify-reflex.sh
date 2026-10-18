#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root/apps/reflex"
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q rxconfig.py lasoai_workspace
uv run python -c 'from lasoai_workspace.lasoai_workspace import app; print("Reflex app import passed")'
uv run python -c 'from urllib.request import urlopen; response = urlopen("http://127.0.0.1:3000/ping", timeout=5); assert response.status == 200; print("Running Python backend /ping passed")'
