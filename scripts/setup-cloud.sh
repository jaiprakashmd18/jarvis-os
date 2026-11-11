#!/bin/bash
# Developer setup for this managed cloud executor; not the release build VM.
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-/workspace/.cache/uv}"
export npm_config_cache="${npm_config_cache:-/workspace/.cache/npm}"
python3 scripts/fetch-assistant.py
for patch in "$PWD"/patches/*.patch; do
 if ! git -C vendor/jarvis apply --reverse --check "$patch" 2>/dev/null; then
  git -C vendor/jarvis apply --check "$patch"
  git -C vendor/jarvis apply "$patch"
 fi
done
uv venv --allow-existing .venv
uv pip install --python .venv/bin/python PyQt5==5.15.11 pytest==9.2.0 uv==0.13.5
uv sync --project vendor/jarvis --frozen --extra voice
(cd vendor/jarvis/apps/web && npm ci --no-audit --no-fund && NEXT_TELEMETRY_DISABLED=1 npm run build && cp -a .next/static .next/standalone/.next/ && cp -a public .next/standalone/)
if [[ -f /usr/share/keyrings/debian-archive-keyring.gpg ]] && command -v gpg >/dev/null; then
 python3 scripts/setup-cloud-audio.py /workspace/tts-tools
 export PATH="/workspace/tts-tools/bin:$PATH"
fi
PYTHONPATH=desktop QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_actions.py tests/test_ui.py
(cd vendor/jarvis && uv run --extra voice pytest)
