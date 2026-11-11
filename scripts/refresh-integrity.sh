#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
(cd build/iso/tree && find . -type f ! -name md5sum.txt ! -path './boot/grub/*' -print0 | sort -z | xargs -0 md5sum) > build/iso/md5sum.txt
cp build/iso/md5sum.txt build/iso/tree/md5sum.txt
