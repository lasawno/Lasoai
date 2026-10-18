#!/usr/bin/env bash
# Read-only code fetch to a temporary directory; does not pull or replace user edits.
set -euo pipefail
scratch_dir=$(mktemp -d -t lasoai-synthetic-test-XXXXXX)
trap 'rm -rf "$scratch_dir"' EXIT
curl --fail --silent --show-error --connect-timeout 5 --max-time 45 \
  https://api.github.com/repos/lasawno/Lasoai/tarball/codex/lasoai-codespaces \
  -L -o "$scratch_dir/source.tar.gz"
mkdir "$scratch_dir/source"
tar -xzf "$scratch_dir/source.tar.gz" -C "$scratch_dir/source" --strip-components=1
python3 "$scratch_dir/source/scripts/test_optional_storage_live.py"
