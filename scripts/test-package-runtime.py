#!/usr/bin/env python3
"""Run inside the isolated Ubuntu builder against the unpacked package service.

The fixed test account lives only in a temporary chroot directory removed before
image assembly. Never run first-run setup against a real owner's service.
"""
import http.cookiejar
import json
from pathlib import Path
import sys
import urllib.request
import urllib.error
import time

cookies=http.cookiejar.LWPCookieJar('/workspace/jarvis-os/build/smoke-cookies')
phase=sys.argv[1]
if Path(cookies.filename).exists(): cookies.load(ignore_discard=True)
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
base='http://127.0.0.1:8000'
def call(path,body=None,raw=False):
    data=body if raw else (json.dumps(body).encode() if body is not None else None)
    r=opener.open(urllib.request.Request(base+path,data=data,headers={'Origin':'http://127.0.0.1:3000','Content-Type':'audio/wav' if raw else 'application/json'}),timeout=120)
    return r if path.endswith('/speak') else json.load(r)
for _ in range(60):
    try:
        assert call('/api/system/ping')['service']=='jarvis-api'; break
    except OSError: time.sleep(1)
else: raise RuntimeError('Service not ready')
assert urllib.request.urlopen('http://127.0.0.1:3000',timeout=5).status==200
if phase=='before':
    first=call('/api/auth/status')['setup_required']
    if first: call('/api/auth/setup',{'username':'release_smoke','display_name':'Release smoke','password':'Ephemeral-Release-Test-Only-123!'})
    if first: call('/api/memories',{'content':'Package restart persistence fixture'})
    cookies.save(ignore_discard=True)
    print('First-run owner creation and memory write passed.')
health=call('/api/system/health'); assert health['database']['ok']
assert any(m['content']=='Package restart persistence fixture' for m in call('/api/memories'))
voice=call('/api/voice/status'); assert voice['active_stt']=='whispercpp' and voice['active_tts']['en']=='espeak'
if phase=='before':
    audio=Path('/workspace/jarvis-os/build/open-terminal.wav').read_bytes()
    result=call('/api/voice/transcribe?language=en',audio,raw=True)
    print('Packaged CPU recognition:',result['text'])
    assert 'terminal' in result['text'].lower()
    r=call('/api/voice/speak',{'text':'Local voice is working','language':'en'})
    wav=r.read(); assert wav.startswith(b'RIFF') and len(wav)>1000
    print('Packaged local espeak WAV synthesis passed:',len(wav),'bytes.')
print('Unprivileged production web/API, health, voice availability and memory passed:',phase)
