"""Deterministic, bounded desktop actions. All process calls use argument arrays."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from urllib.parse import urlsplit

APPS = {'browser': ['xdg-open', 'https://start.ubuntu.com'],
        'files': ['dolphin'], 'terminal': ['konsole'], 'settings': ['systemsettings']}


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'jarvis-os/desktop.db'
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.path)
        os.chmod(self.path, 0o600)
        self.db.executescript('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);'
                              'CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, content TEXT NOT NULL);')

    def set(self, key, value):
        if key not in ('atlas_url', 'search_roots', 'speak'):
            raise ValueError('Unknown setting')
        if key == 'atlas_url' and value:
            parts = urlsplit(value)
            if len(value)>2048 or parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password or any(ord(c)<32 for c in value):
                raise ValueError('Use an http(s) URL without embedded credentials')
        if key == 'search_roots':
            roots = json.loads(value)
            if not isinstance(roots, list) or len(roots)>10:
                raise ValueError('Choose up to ten folders')
            for root in roots:
                p = Path(root).expanduser().resolve()
                if not p.is_dir() or not p.is_relative_to(Path.home().resolve()):
                    raise ValueError('Search folders must be inside your home directory')
            value = json.dumps([str(Path(p).expanduser().resolve()) for p in roots])
        if key == 'speak' and value not in ('true', 'false'):
            raise ValueError('Invalid speech setting')
        self.db.execute('INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
        self.db.commit()

    def get(self, key, default=''):
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return row[0] if row else default

    def remember(self, content):
        if not content.strip() or len(content)>2000:
            raise ValueError('Memory must contain 1–2000 characters')
        cur = self.db.execute('INSERT INTO memories(content) VALUES (?)', (content.strip(),))
        self.db.commit()
        return cur.lastrowid

    def memories(self):
        return self.db.execute('SELECT id,content FROM memories ORDER BY id').fetchall()

    def edit(self, mid, content):
        if not content.strip() or len(content)>2000:
            raise ValueError('Memory must contain 1–2000 characters')
        self.db.execute('UPDATE memories SET content=? WHERE id=?', (content.strip(), int(mid)))
        self.db.commit()

    def delete(self, mid):
        self.db.execute('DELETE FROM memories WHERE id=?', (int(mid),))
        self.db.commit()

    def export(self):
        return json.dumps({'settings': dict(self.db.execute('SELECT key,value FROM settings')), 'memories': self.memories()}, indent=2)

    def erase(self):
        self.db.executescript('DELETE FROM memories; DELETE FROM settings; VACUUM;')

    def close(self):
        self.db.close()


def launch(argv):
    # GUI programs can legitimately remain alive for hours. Never wait for their
    # lifetime or kill them on an action timeout; only inspect immediate startup.
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'jarvis-os'
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    log_path = data/'desktop-actions.log'
    fd = os.open(log_path, os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'ab') as log:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                start_new_session=True)
    try:
        code = proc.wait(timeout=.35)
    except subprocess.TimeoutExpired:
        return proc
    if code:
        raise RuntimeError(f'{argv[0]} could not start (exit {code}); open Logs for details.')
    return proc


def run(argv):
    if argv[0] in ('xdg-open', 'dolphin', 'konsole', 'systemsettings'):
        launch(argv)
        return ''
    result = subprocess.run(argv, capture_output=True, text=True, timeout=15, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[:300] or f'{argv[0]} failed')
    return result.stdout.strip()


class Actions:
    def __init__(self, store, runner=run):
        self.store, self.runner = store, runner

    def execute(self, command, confirmed=False):
        if not isinstance(command, str) or len(command)>2200:
            raise ValueError('Command is too long')
        raw, cmd = command.strip(), command.strip().lower().rstrip(".!?")
        if cmd == 'help':
            return 'Open browser / files / terminal / settings; Open my anatomy atlas; volume 0–100; timer 1–1440; search NAME; remember TEXT; shutdown; restart. General conversation: open Assistant.'
        if cmd == 'open my anatomy atlas':
            url = self.store.get('atlas_url')
            if not url:
                raise ValueError('Set the anatomy atlas URL in Settings first')
            self.store.set('atlas_url', url)  # revalidate data loaded from disk
            self.runner(['xdg-open', url])
            return 'Opened your anatomy atlas in the guest browser.'
        if cmd.startswith('open ') and cmd[5:] in APPS:
            self.runner(APPS[cmd[5:]])
            return f'Started {cmd[5:]}.'
        if re.fullmatch(r'volume (\d{1,3})', cmd):
            value = int(cmd.split()[1])
            if value>100:
                raise ValueError('Volume must be 0–100')
            self.runner(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', f'{value}%'])
            return f'Volume set to {value}%.'
        if re.fullmatch(r'timer (\d{1,4})', cmd):
            minutes = int(cmd.split()[1])
            if not 1 <= minutes <= 1440:
                raise ValueError('Timer must be 1–1440 minutes')
            self.runner(['systemd-run', '--user', '--collect', f'--on-active={minutes}m',
                         '/usr/bin/notify-send', 'JARVIS timer', f'{minutes} minutes elapsed'])
            return f'Timer set for {minutes} minutes.'
        if cmd.startswith('remember '):
            mid = self.store.remember(raw[9:])
            return f'Saved memory {mid}. Manage it in Saved data.'
        if cmd.startswith('search '):
            needle = raw[7:].strip().lower()
            if not needle or len(needle)>100 or '/' in needle or '\x00' in needle:
                raise ValueError('Search for a filename of 1–100 characters')
            roots = json.loads(self.store.get('search_roots', '[]'))
            if not roots:
                raise ValueError('Approve search folders in Settings first')
            found, visited = [], 0
            home = Path.home().resolve()
            for root in roots:
                p = Path(root).resolve()
                if not p.is_relative_to(home):
                    raise ValueError('Search root is outside your home')
                for folder, dirs, files in os.walk(p, followlinks=False):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and not (Path(folder)/d).is_symlink()]
                    for name in files:
                        visited += 1
                        entry = Path(folder)/name
                        if not entry.is_symlink() and needle in name.lower():
                            found.append(str(entry))
                        if len(found)>=50 or visited>=20000:
                            return '\n'.join(found) or 'No matches within the 20,000-file search limit.'
            return '\n'.join(found) or 'No matching files.'
        if cmd in ('shutdown', 'restart'):
            if not confirmed:
                raise PermissionError('Confirmation required')
            self.runner(['systemctl', 'poweroff' if cmd == 'shutdown' else 'reboot'])
            return f'Requested {cmd}.'
        raise ValueError('Unknown local command. Type help, or open Assistant for optional model chat.')
