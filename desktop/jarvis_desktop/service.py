"""Supervise pinned production servers; keep their lifetime tied to the user unit."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request


def ready():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/system/ping', timeout=1) as r:
            data = json.load(r)
        if data.get('service') != 'jarvis-api' or data.get('ok') is not True:
            return False
        with urllib.request.urlopen('http://127.0.0.1:3000', timeout=1) as r:
            return r.status == 200
    except (OSError, ValueError):
        return False


def main():
    os.umask(0o077)
    root = Path(os.environ.get('JARVIS_UPSTREAM', '/opt/jarvis/upstream'))
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'jarvis-os'
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = os.environ.copy()
    env.update(JARVIS_DATABASE_URL=f'sqlite:///{data}/assistant.db',
               JARVIS_SECRET_KEY_FILE=str(data/'secret.key'),
               JARVIS_HOST='127.0.0.1', JARVIS_PORT='8000',
               JARVIS_ENV='desktop', JARVIS_COOKIE_SECURE='false',
               JARVIS_ALLOWED_ORIGINS='["http://localhost:3000","http://127.0.0.1:3000"]',
               JARVIS_WHISPER_MODEL_PATH='/opt/jarvis/models/ggml-base.en.bin',
               PYTHONPATH=str(root/'core/src')+':'+str(root/'services/api/src'),
               JARVIS_TTS_ENGINE='espeak', HOSTNAME='127.0.0.1', PORT='3000', NODE_ENV='production')
    procs = []
    def stop(*_):
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    try:
        procs.append(subprocess.Popen([str(root/'.venv/bin/python'), '-m', 'jarvis_api.main'], cwd=root, env=env))
        procs.append(subprocess.Popen([os.environ.get('JARVIS_NODE', '/opt/jarvis/runtime/node'), str(root/'apps/web/.next/standalone/server.js')], cwd=root/'apps/web', env=env))
        for _ in range(90):
            if any(p.poll() is not None for p in procs):
                raise RuntimeError('A production server exited; inspect journalctl --user -u jarvis')
            if ready():
                print('JARVIS backend and web ready', flush=True)
                break
            time.sleep(1)
        else:
            raise RuntimeError('Readiness timeout')
        while all(p.poll() is None for p in procs):
            time.sleep(1)
        raise RuntimeError('A production server exited')
    finally:
        stop()


if __name__ == '__main__':
    main()
