#!/usr/bin/env python3
"""Fetch only the pinned source; never overwrite an existing checkout."""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
pin = json.loads((ROOT / 'config/assistant.json').read_text())
dest = ROOT / 'vendor/jarvis'
if not dest.exists():
    dest.parent.mkdir(exist_ok=True)
    subprocess.run(['git', 'clone', pin['repository'], str(dest)], check=True)
if subprocess.check_output(['git', '-C', str(dest), 'status', '--porcelain']).strip():
    patches = sorted((ROOT / 'patches').glob('*.patch'))
    for patch in patches:
        subprocess.run(['git', '-C', str(dest), 'apply', '--reverse', '--check', str(patch)], check=True)
    # Only accept exactly our recorded patch; never discard unknown work.
    expected = ''.join(p.read_text() for p in patches)
    actual = subprocess.check_output(['git', '-C', str(dest), 'diff', '--no-ext-diff'], text=True)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['git', 'clone', '--shared', '--no-hardlinks', str(dest), tmp], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', '-C', tmp, 'checkout', '--detach', pin['commit']], check=True, stdout=subprocess.DEVNULL)
        for patch in patches:
            subprocess.run(['git', '-C', tmp, 'apply', str(patch)], check=True)
        wanted = subprocess.check_output(['git', '-C', tmp, 'diff', '--no-ext-diff'], text=True)
    status = subprocess.check_output(['git', '-C', str(dest), 'status', '--porcelain'], text=True)
    if actual != wanted or any(not line.startswith(' M ') for line in status.splitlines()):
        raise SystemExit('Unrecognized source changes; preserve them before setup.')
    print(dest)
    raise SystemExit(0)
subprocess.run(['git', '-C', str(dest), 'fetch', 'origin', pin['commit']], check=True)
subprocess.run(['git', '-C', str(dest), 'checkout', '--detach', pin['commit']], check=True)
assert subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'HEAD'], text=True).strip() == pin['commit']
print(dest)
