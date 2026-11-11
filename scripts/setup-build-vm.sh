#!/bin/bash
set -euo pipefail
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo 'Use an Ubuntu/Kubuntu 24.04 x86-64 build VM.' >&2; exit 1; }
[[ $(uname -m) == x86_64 ]] || exit 1
sudo apt-get update
sudo apt-get install -y git curl ca-certificates gnupg ubuntu-keyring xorriso squashfs-tools rsync \
 python3 python3-venv python3-pip python3-pyqt5 python3-pyqt5.qtmultimedia \
 build-essential cmake pkg-config espeak-ng alsa-utils ffmpeg dpkg-dev
node_root=$(python3 scripts/fetch-node.py)
export PATH="$node_root/bin:$PATH"
python3 -m venv .venv
.venv/bin/pip install uv==0.13.5
./scripts/prepare-assistant.sh
