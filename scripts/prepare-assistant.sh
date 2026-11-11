#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
node_root=$(python3 scripts/fetch-node.py)
export PATH="$node_root/bin:$PATH"
python3 scripts/fetch-assistant.py
cd vendor/jarvis
for patch in ../../patches/*.patch; do
  if ! git apply --reverse --check "$patch" 2>/dev/null; then
    git apply --check "$patch"
    git apply "$patch"
  fi
done
../../.venv/bin/uv sync --frozen --extra voice --python /usr/bin/python3
../../.venv/bin/uv run --extra voice pytest
cd apps/web
npm ci --no-audit --no-fund
npm run lint
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build
cp -a .next/static .next/standalone/.next/
cp -a public .next/standalone/
