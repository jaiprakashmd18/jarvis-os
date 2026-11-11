#!/bin/bash
# Headless UEFI smoke test; never attaches a host or existing virtual disk.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/qemu
[[ -f dist/jarvis-os-1.0.0-amd64.iso ]] || { echo 'Build the ISO first'; exit 1; }
[[ ! -e build/qemu/monitor.sock ]] || { echo 'An existing QEMU session needs inspection first'; exit 1; }
if [[ -f build/qemu/qemu.pid ]] && kill -0 "$(cat build/qemu/qemu.pid)" 2>/dev/null; then
 echo "A QEMU test is already running" >&2; exit 1
fi
cp /usr/share/OVMF/OVMF_VARS_4M.fd build/qemu/vars.fd
exec qemu-system-x86_64 -accel tcg,thread=multi -cpu "${JARVIS_TEST_CPU:-Nehalem}" -smp 2 -m 4096 \
 -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
 -drive if=pflash,format=raw,file=build/qemu/vars.fd \
 -pidfile build/qemu/qemu.pid -cdrom dist/jarvis-os-1.0.0-amd64.iso -boot d \
 -vga "${JARVIS_TEST_VGA:-std}" -display none -serial file:build/qemu/serial.txt \
 -monitor unix:build/qemu/monitor.sock,server=on,wait=off \
 -netdev user,id=net0 -device virtio-net-pci,netdev=net0 \
 -audiodev driver=none,id=silent -device intel-hda -device hda-duplex,audiodev=silent
