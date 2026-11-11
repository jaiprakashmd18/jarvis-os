#!/usr/bin/env python3
"""Require an immutable model URL and SHA256. Never bless a newly downloaded hash."""
import hashlib
import json
from pathlib import Path
import urllib.request
ROOT = Path(__file__).resolve().parents[1]
pin = json.loads((ROOT/'config/voice.json').read_text())
if not pin.get('sha256') or not pin.get('url'):
    raise SystemExit('Voice model pin unresolved. See docs/VOICE.md; release build is blocked.')
p = ROOT/'cache/models/ggml-base.en.bin'; p.parent.mkdir(parents=True, exist_ok=True)
if not p.exists():
    tmp = p.with_suffix('.part')
    try:
        with urllib.request.urlopen(pin['url'], timeout=60) as r, tmp.open('wb') as f:
            while chunk := r.read(1024*1024): f.write(chunk)
        if hashlib.file_digest(tmp.open('rb'), 'sha256').hexdigest()!=pin['sha256']:
            raise SystemExit('Model checksum mismatch')
        tmp.replace(p)
    finally: tmp.unlink(missing_ok=True)
with p.open('rb') as f:
    if hashlib.file_digest(f, 'sha256').hexdigest()!=pin['sha256']: raise SystemExit('Cached model checksum mismatch')
print(p)
