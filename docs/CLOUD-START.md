# Cloud startup (local fallback for failed settings persistence)

Environment settings draft reads and writes returned INVALID_ARGUMENT; neither
install_script, start_skill nor requested domain changes were confirmed saved.
The following are tested constituent commands and the intended reusable settings.
This file itself does not register them with the platform or publish a snapshot.

Install script:

```
#!/bin/bash
set -euo pipefail
cd /workspace/jarvis-os
./scripts/setup-cloud.sh
```

Startup instructions:

Use the existing /workspace/jarvis-os checkout. Cloud tasks are already isolated;
do not create a worktree unless explicitly requested. Read README.md and
reports/RELEASE.md. Retained dependencies are distinct from running processes.

From /workspace/jarvis-os, start this in a managed background execution session:

```
mkdir -p build/cloud-data
export PATH="/workspace/tts-tools/bin:$PATH"
PYTHONPATH=desktop JARVIS_UPSTREAM="$PWD/vendor/jarvis" \
 JARVIS_NODE="$(command -v node)" XDG_DATA_HOME="$PWD/build/cloud-data" \
 .venv/bin/python -m jarvis_desktop.service > build/service.log 2>&1
```

Verify `/api/system/ping` at 127.0.0.1:8000 returns ok=true and service=jarvis-api,
and an HTTP GET to 127.0.0.1:3000 returns 200. Use these for internal checks, not
user-facing preview links. Inspect build/service.log if startup fails. Do not
start a second server over existing ports; stop only the processes you started.
For a graphical native window:

```
PYTHONPATH=desktop XDG_DATA_HOME="$PWD/build/cloud-data" \
 .venv/bin/python -m jarvis_desktop.app
```

Headless checks:

```
PYTHONPATH=desktop QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_actions.py tests/test_ui.py
PATH="/workspace/tts-tools/bin:$PATH" UV_CACHE_DIR=/workspace/.cache/uv \
 uv run --project vendor/jarvis --extra voice pytest vendor/jarvis/core/tests vendor/jarvis/services/api/tests
```

The Debian-only local TTS helper is retained in /workspace/tts-tools and can be
refreshed via scripts/setup-cloud-audio.py; it verifies signed repository
metadata and package hashes, installs nothing into the system, and is excluded
from the Ubuntu release package. Native package/ISO building still requires the
Ubuntu build VM and verified base/voice inputs described in BUILD.md.

For the pinned release-equivalent runtime, replace JARVIS_NODE's value above with
`$PWD/cache/node/node-v22.23.4-linux-x64/bin/node` after
`python3 scripts/fetch-node.py`. The production server was also verified using
this runtime (reports/logs/pinned-node-service.txt).
