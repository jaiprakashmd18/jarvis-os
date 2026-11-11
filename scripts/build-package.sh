#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && $(uname -m) == x86_64 ]] || { echo 'Build the release package on Ubuntu 24.04 amd64 (glibc/Python ABI).' >&2; exit 1; }
[[ -f vendor/jarvis/apps/web/.next/standalone/server.js ]] || { echo 'Run scripts/setup-build-vm.sh first'; exit 1; }
# A distributable package contains no editable paths, developer data, .env or Git credentials.
root="$PWD/build/package"
[[ ! -e "$root" ]] || { echo 'Move the previous build/package out of the way first'; exit 1; }
mkdir -p "$root/opt/jarvis/upstream" "$root/opt/jarvis/desktop" "$root/DEBIAN" "$root/usr/bin" \
 "$root/usr/lib/systemd/user" "$root/usr/share/applications" "$root/etc/xdg/autostart"
rsync -a --exclude=.git --exclude=.venv --exclude=node_modules --exclude=.env --exclude=data \
 --exclude=__pycache__ --exclude=.pytest_cache --exclude=.next vendor/jarvis/ "$root/opt/jarvis/upstream/"
# Build dependencies directly in the package tree using the frozen lock; Python modules
# are noneditable. service.py supplies source PYTHONPATH for upstream Alembic paths.
.venv/bin/uv sync --project "$root/opt/jarvis/upstream" --frozen --no-dev --no-editable --extra voice --python /usr/bin/python3
# Venv bin/python must resolve to the target's system interpreter, not the build directory.
ln -sfn /usr/bin/python3.12 "$root/opt/jarvis/upstream/.venv/bin/python"
ln -sfn python "$root/opt/jarvis/upstream/.venv/bin/python3"
ln -sfn python "$root/opt/jarvis/upstream/.venv/bin/python3.12"
mkdir -p "$root/opt/jarvis/upstream/apps/web/.next"
cp -a vendor/jarvis/apps/web/.next/standalone "$root/opt/jarvis/upstream/apps/web/.next/"
cp -a desktop/jarvis_desktop "$root/opt/jarvis/desktop/"
find "$root" -type d -name __pycache__ -prune -exec rm -rf {} +
install -m755 packaging/jarvis-desktop packaging/jarvis-session "$root/usr/bin/"
install -m644 packaging/systemd/jarvis.service "$root/usr/lib/systemd/user/"
install -m644 packaging/applications/jarvis.desktop "$root/usr/share/applications/"
mkdir -p "$root/usr/share/kglobalaccel"
install -m644 packaging/applications/jarvis.desktop "$root/usr/share/kglobalaccel/"
install -m644 packaging/autostart/jarvis.desktop "$root/etc/xdg/autostart/"
mkdir -p "$root/usr/share/icons/hicolor/scalable/apps"
install -m644 packaging/branding/jarvis.svg "$root/usr/share/icons/hicolor/scalable/apps/jarvis.svg"
# Voice model is a mandatory verified input to the release, never downloaded at login.
python3 scripts/fetch-model.py
node_root=$(python3 scripts/fetch-node.py)
mkdir -p "$root/opt/jarvis/runtime"
install -m755 "$node_root/bin/node" "$root/opt/jarvis/runtime/node"
cp "$node_root/LICENSE" "$root/opt/jarvis/runtime/LICENSE"
mkdir -p "$root/opt/jarvis/models"
cp cache/models/ggml-base.en.bin "$root/opt/jarvis/models/"
cat > "$root/DEBIAN/control" <<'CONTROL'
Package: jarvis-os-desktop
Version: 1.0.0
Architecture: amd64
Maintainer: JARVIS OS contributors
Depends: python3 (>= 3.12), python3 (<< 3.13), python3-pyqt5, espeak-ng, alsa-utils, pipewire-bin, xdg-utils, libnotify-bin, konsole, dolphin, systemsettings, libgomp1, libstdc++6
Description: JARVIS local assistant and offline KDE desktop command center
 CPU local voice and per-user data. Optional Ollama conversation provider.
CONTROL
chmod -R a+rX,go-w "$root"
mkdir -p dist
dpkg-deb --threads-max=2 -Zzstd -z6 --root-owner-group --build "$root" dist/jarvis-os-desktop_1.0.0_amd64.deb
(cd dist && sha256sum jarvis-os-desktop_1.0.0_amd64.deb > jarvis-os-desktop_1.0.0_amd64.deb.sha256)
