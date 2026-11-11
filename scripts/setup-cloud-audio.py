#!/usr/bin/env python3
"""Install a verified Debian test-only TTS runtime under a user-writable prefix.

No sudo, system changes, unsigned metadata, or dependencies enter the release DEB.
"""
import hashlib
import lzma
from pathlib import Path
import subprocess
import sys
import urllib.request

prefix=Path(sys.argv[1] if len(sys.argv)>1 else '/workspace/tts-tools').resolve()
prefix.mkdir(parents=True,exist_ok=True)
keyring=Path('/usr/share/keyrings/debian-archive-keyring.gpg')
if not keyring.exists(): raise SystemExit('Debian test runtime only; use signed APT on the Ubuntu build VM.')
home=prefix/'gnupg'; home.mkdir(exist_ok=True,mode=0o700)

def fetch(url,path):
    with urllib.request.urlopen(url,timeout=60) as response, path.open('wb') as f:
        while chunk:=response.read(1024*1024): f.write(chunk)

fetch('https://deb.debian.org/debian/dists/trixie/InRelease',prefix/'InRelease')
subprocess.run(['gpg','--batch','--homedir',str(home),'--no-default-keyring','--keyring',str(keyring),
                '--verify',str(prefix/'InRelease')],check=True)
fetch('https://deb.debian.org/debian/dists/trixie/main/binary-amd64/Packages.xz',prefix/'Packages.xz')
manifest=(prefix/'InRelease').read_text()
rows=manifest.split('SHA256:\n',1)[1].split('\nSHA',1)[0].splitlines()
expected=next(x.split()[0] for x in rows if x.strip().endswith('main/binary-amd64/Packages.xz'))
with (prefix/'Packages.xz').open('rb') as f:
    if hashlib.file_digest(f,'sha256').hexdigest()!=expected: raise SystemExit('Index checksum mismatch')
paras=lzma.open(prefix/'Packages.xz','rt').read().split('\n\n')
for name in ('espeak-ng','espeak-ng-data','libespeak-ng1','libpcaudio0','libsonic0'):
    para=next(p for p in paras if p.startswith('Package: '+name+'\n'))
    meta=dict(l.split(': ',1) for l in para.splitlines() if ': ' in l and not l.startswith(' '))
    path=prefix/(name+'.deb')
    fetch('https://deb.debian.org/debian/'+meta['Filename'],path)
    with path.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=meta['SHA256']: raise SystemExit('Package checksum mismatch: '+name)
    subprocess.run(['dpkg-deb','-x',str(path),str(prefix/'root')],check=True)
    print(name,meta['Version'],'signature chain and SHA256 verified')
(prefix/'bin').mkdir(exist_ok=True)
# Quote the prefix for shell paths; no secrets or caller text enter this wrapper.
import shlex
lib=shlex.quote(str(prefix/'root/usr/lib/x86_64-linux-gnu'))
binary=shlex.quote(str(prefix/'root/usr/bin/espeak-ng'))
wrapper=prefix/'bin/espeak-ng'
wrapper.write_text('#!/bin/sh\nexport LD_LIBRARY_PATH='+lib+'\nexec '+binary+' --path='+lib+' "$@"\n')
wrapper.chmod(0o755)
subprocess.run([str(wrapper),'-w',str(prefix/'test.wav'),'JARVIS local speech is ready'],check=True)
print('For tests: prepend',prefix/'bin','to PATH. This does not test a physical speaker.')
