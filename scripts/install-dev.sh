#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_USER_BASE="${PYTHONUSERBASE:-/data/.local}"

cd "$ROOT_DIR"
PYTHONUSERBASE="$PY_USER_BASE" python3 -m pip install --user --break-system-packages -e .

echo
if command -v ralph-loop >/dev/null 2>&1; then
  echo "✅ ralph-loop installed and available on PATH"
  ralph-loop --help >/dev/null 2>&1 || true
else
  echo "⚠️ ralph-loop installed but not found on PATH"
  echo "Add this to your shell profile:"
  echo "  export PATH=\"$PY_USER_BASE/bin:\$PATH\""
fi
