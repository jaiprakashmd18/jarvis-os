#!/usr/bin/env python3
"""Fetch the fixed official Node runtime and verify its committed SHA256."""
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
import tarfile
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
pin=json.loads((ROOT/'config/node.json').read_text())
cache=ROOT/'cache/node'; cache.mkdir(parents=True,exist_ok=True)
archive=cache/pin['url'].rsplit('/',1)[-1]
if not archive.exists():
    tmp=archive.with_suffix('.part')
    try:
        with urllib.request.urlopen(pin['url'],timeout=60) as r, tmp.open('wb') as f:
            while chunk:=r.read(1024*1024): f.write(chunk)
        with tmp.open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=pin['sha256']: raise SystemExit('Node checksum mismatch')
        tmp.replace(archive)
    finally: tmp.unlink(missing_ok=True)
with archive.open('rb') as f:
    if hashlib.file_digest(f,'sha256').hexdigest()!=pin['sha256']: raise SystemExit('Cached Node checksum mismatch')
dest=cache/archive.name.removesuffix('.tar.xz')
# Avoid rewriting a runtime that another build is executing (ETXTBSY).
with tarfile.open(archive) as t:
    member = t.getmember(dest.name+'/bin/node')
    with t.extractfile(member) as f:
        expected_node=hashlib.file_digest(f, 'sha256').hexdigest()
    valid=False
    if (dest/'bin/node').is_file():
        with (dest/'bin/node').open('rb') as f:
            valid=hashlib.file_digest(f, 'sha256').hexdigest()==expected_node
    if not valid:
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            t.extractall(tmp,filter='data')
            if dest.exists(): shutil.rmtree(dest)
            os.replace(Path(tmp)/dest.name, dest)
print(dest)
