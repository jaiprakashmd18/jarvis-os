#!/bin/bash
# Dedicated software-emulated installation test. The only writable guest disk is
# a new file created here; no block-device paths or existing disks are accepted.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/qemu
phase="${1:-live}"
if [[ -S build/qemu/monitor.sock ]]; then echo 'Stop the previous test first'; exit 1; fi
if [[ -f build/qemu/qemu.pid ]] && kill -0 "$(cat build/qemu/qemu.pid)" 2>/dev/null; then exit 1; fi
disk=build/qemu/install-disk.qcow2
vars=build/qemu/install-vars.fd
extra=()
if [[ "$phase" == live ]]; then
 [[ ! -e "$disk" && ! -e "$vars" ]] || { echo 'Preserve existing installation-test files before a fresh run'; exit 1; }
 python3 scripts/create-test-disk.py
 cp /usr/share/OVMF/OVMF_VARS_4M.fd "$vars"
 extra=(-cdrom dist/jarvis-os-1.0.0-amd64.iso -boot d)
elif [[ "$phase" == installed ]]; then
 [[ -f "$disk" && -f "$vars" ]] || exit 1
 extra=(-boot c)
else
 echo 'Use live or installed'; exit 1
fi
exec qemu-system-x86_64 -accel tcg,thread=multi -cpu Nehalem -smp 4 -m 6144 \
 -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
 -drive if=pflash,format=raw,file="$vars" \
 -drive if=virtio,format=qcow2,file="$disk" "${extra[@]}" \
 -vga std -display none -device qemu-xhci,id=usbtest -device usb-tablet,bus=usbtest.0 \
 -serial file:build/qemu/install-serial.txt -pidfile build/qemu/qemu.pid \
 -monitor unix:build/qemu/monitor.sock,server=on,wait=off \
 -netdev user,id=net0 -device virtio-net-pci,netdev=net0 \
 -audiodev driver=none,id=silent -device intel-hda -device hda-duplex,audiodev=silent
