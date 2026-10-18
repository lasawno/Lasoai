#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root/apps/reflex"
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q rxconfig.py lasoai_workspace
uv run python -c 'from lasoai_workspace.lasoai_workspace import app; print("Reflex app import passed")'
uv run python "$project_root/scripts/check_reflex_preview.py"
