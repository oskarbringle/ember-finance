#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"

# Codex bundles a compatible Node runtime. Prefer it when available because
# vinext requires Node 22.13 or newer.
codex_node_dir="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"
if [[ -x "$codex_node_dir/node" ]]; then
  PATH="$codex_node_dir:$PATH"
fi

if ! node -e 'const [major, minor] = process.versions.node.split(".").map(Number); process.exit(major > 22 || (major === 22 && minor >= 13) ? 0 : 1)' 2>/dev/null; then
  echo "Ember requires Node.js 22.13 or newer. Current version: $(node --version 2>/dev/null || echo not installed)" >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

if ! .venv/bin/python -c 'import fastapi, openpyxl, pandas' >/dev/null 2>&1; then
  .venv/bin/pip install -r backend/requirements.txt
fi

if [[ ! -d node_modules ]]; then
  npm install
fi

if .venv/bin/python -c 'import socket, sys; sock = socket.socket(); sys.exit(0 if sock.connect_ex(("127.0.0.1", 8000)) == 0 else 1)'; then
  echo "Port 8000 is already in use. Stop the other Ember API, then run this script again." >&2
  exit 1
fi

.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM
echo "Ember is starting at http://localhost:3000"
npm run dev
