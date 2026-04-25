#!/usr/bin/env bash
# Run from repo root: ./scripts/run_server.sh
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d venv ]]; then
  echo "Create venv first: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  exit 1
fi
exec ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
