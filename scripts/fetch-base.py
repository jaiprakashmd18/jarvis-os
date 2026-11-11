#!/usr/bin/env python3
"""Authenticate Ubuntu's signed checksum manifest before accepting any ISO bytes."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import urllib.request
ROOT = Path(__file__).resolve().parents[1]
pin = json.loads((ROOT/'config/base.json').read_text())
cache = ROOT/'cache/base'; cache.mkdir(parents=True,exist_ok=True)

def fetch(url, path):
    tmp=path.with_suffix(path.suffix+'.part')
    try:
        with urllib.request.urlopen(url,timeout=90) as r, tmp.open('wb') as f:
            while chunk:=r.read(4*1024*1024): f.write(chunk)
        tmp.replace(path)
    finally: tmp.unlink(missing_ok=True)

fetch(pin['checksums'],cache/'SHA256SUMS')
fetch(pin['signature'],cache/'SHA256SUMS.gpg')
keyring = os.environ.get('JARVIS_UBUNTU_KEYRING', '/usr/share/keyrings/ubuntu-archive-keyring.gpg')
if shutil.which('gpgv'):
    verifier = ['gpgv', '--status-fd=1', '--keyring', keyring]
else:
    home=cache/'gnupg'; home.mkdir(exist_ok=True, mode=0o700)
    verifier=['gpg','--batch','--homedir',str(home),'--no-default-keyring', '--keyring',keyring,'--status-fd=1','--verify']
p=subprocess.run(verifier+[str(cache/'SHA256SUMS.gpg'),str(cache/'SHA256SUMS')], capture_output=True,text=True,check=True)
(cache/'signature-status.txt').write_text(p.stdout+p.stderr)
if f'[GNUPG:] VALIDSIG {pin["signer"]} ' not in p.stdout:
    raise SystemExit('Manifest was not signed by the pinned Ubuntu CD image key')
name=pin['url'].rsplit('/',1)[-1]
entries=[line.split() for line in (cache/'SHA256SUMS').read_text().splitlines()]
hashes=[parts[0] for parts in entries if len(parts)==2 and parts[1].lstrip('*')==name]
if len(hashes)!=1 or len(hashes[0])!=64: raise SystemExit('Missing/unexpected image checksum')
expected=hashes[0]
if pin.get('sha256') and pin['sha256']!=expected: raise SystemExit('Base checksum changed')
iso=cache/name
if not iso.exists(): fetch(pin['url'],iso)
with iso.open('rb') as f:
    if hashlib.file_digest(f,'sha256').hexdigest()!=expected: raise SystemExit('ISO checksum mismatch')
# An authenticated input lock is retained alongside build evidence. Promote this
# reviewed value into config/base.json before issuing a release.
(cache/'verified.json').write_text(json.dumps({'file':name,'sha256':expected,'signer':pin['signer']},indent=2)+'\n')
print(iso)
