#!/usr/bin/env python3
"""Generated initrds need an explicit casper mode; prohibit live swap activation."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
count=0
for pattern in ('boot/grub/*.cfg','isolinux/*.cfg'):
    for path in root.glob(pattern):
        lines=[]
        for line in path.read_text().splitlines():
            if line.strip()=='grub_platform': continue  # stray command in original base
            if line.lstrip().startswith(('linux ', 'linux\t')) and '/casper/vmlinuz' in line:
                parts=line.split()
                flags=[flag for flag in ('boot=casper','noswap') if flag not in parts]
                parts[2:2]=flags
                line='\t'+' '.join(parts)
                count+=1
            lines.append(line)
        path.write_text('\n'.join(lines)+'\n')
if not count: raise SystemExit('No live kernel entries found; review this image layout')
print('Validated explicit casper/noswap flags in',count,'live entries')
