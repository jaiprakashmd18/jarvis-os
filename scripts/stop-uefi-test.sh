#!/bin/bash
# Run in the same build VM/container as test-uefi.sh (PID namespaces must match).
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f build/qemu/qemu.pid ]] || { echo 'No test PID file; inspect processes before cleanup'; exit 1; }
qemu_test_pid=$(cat build/qemu/qemu.pid)
[[ "$qemu_test_pid" =~ ^[0-9]+$ ]] || exit 1
[[ $(cat "/proc/$qemu_test_pid/comm") == qemu-system-x86* ]] || { echo 'PID does not identify the test emulator'; exit 1; }
kill -TERM "$qemu_test_pid"
for attempt in {1..50}; do
 if ! kill -0 "$qemu_test_pid" 2>/dev/null; then
  rm -f build/qemu/monitor.sock build/qemu/qemu.pid
  exit 0
 fi
 sleep .1
done
echo 'QEMU did not stop; inspect it before reusing test paths' >&2
exit 1
