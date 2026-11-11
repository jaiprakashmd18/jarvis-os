#!/usr/bin/env python3
"""Replace only modified files so original GRUB/EFI boot image nodes survive."""
from pathlib import Path
import json
import subprocess
ROOT=Path(__file__).resolve().parents[1]
base=json.loads((ROOT/'config/base.json').read_text())
source=ROOT/'cache/base'/base['url'].rsplit('/',1)[-1]
tree=ROOT/'build/iso/tree'
out=ROOT/'dist/jarvis-os-1.0.0-amd64.iso'
if out.exists(): raise SystemExit('Output already exists; preserve or move it before rebuilding')
subprocess.run(['bash', str(ROOT/'scripts/refresh-integrity.sh')], check=True)
cmd=['xorriso','-indev',str(source),'-outdev',str(out),'-boot_image','any','replay','-volid','JARVIS_OS_1_0']
files=['casper/filesystem.squashfs','casper/filesystem.manifest','casper/filesystem.size','casper/initrd','md5sum.txt']
files += [str(p.relative_to(tree)) for pattern in ('boot/grub/*.cfg','isolinux/*.cfg') for p in tree.glob(pattern)]
for relative in files:
    cmd+=['-map',str(tree/relative),'/'+relative]
cmd+=['-rm','/casper/filesystem.squashfs.gpg','--']
subprocess.run(cmd,check=True)
