#!/usr/bin/env bash
# Start the API and the web dev server together (native processes, no containers).
# The job worker joins in Phase 2, when the jobs table exists.
# Usage: scripts/dev.sh
set -euo pipefail
cd "$(dirname "$0")/.."

uv run uvicorn weta_api.main:app --reload --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM

pnpm --filter web dev
