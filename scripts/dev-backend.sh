#!/usr/bin/env bash
# Run API from repo root. Uses venv Python so pyenv shims cannot steal uvicorn.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/venv/bin/activate"
fi
export PATH="$ROOT/venv/bin:${PATH:-}"

python -m pip install -q -r backend/requirements.txt
exec python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
