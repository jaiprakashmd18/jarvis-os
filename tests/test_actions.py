import json
from pathlib import Path
import pytest
from jarvis_desktop.actions import Actions, Store

@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path/'data.db'); yield s; s.close()

@pytest.mark.parametrize('command', ['open terminal; touch /tmp/pwn', 'volume 101', 'timer 0','timer 1441','rm -rf ~','open $(id)','volume -1'])
def test_rejects_unapproved_commands(store, command):
    calls=[]
    with pytest.raises(ValueError): Actions(store,calls.append).execute(command)
    assert calls==[]

def test_atlas_uses_argument_array_and_persists(tmp_path):
    p=tmp_path/'data.db'; store=Store(p)
    store.set('atlas_url','http://127.0.0.1:9123/atlas?view=heart&lang=en'); store.remember('anatomy review')
    store.close(); store=Store(p); calls=[]
    Actions(store,calls.append).execute('Open my anatomy atlas')
    assert calls==[['xdg-open','http://127.0.0.1:9123/atlas?view=heart&lang=en']]
    assert store.memories()==[(1,'anatomy review')]
    store.edit(1,'updated'); assert json.loads(store.export())['memories']==[[1,'updated']]
    store.delete(1); assert store.memories()==[]
    store.erase(); assert store.get('atlas_url')==''
    assert p.stat().st_mode & 0o777==0o600
    store.close()

@pytest.mark.parametrize('url',['file:///etc/passwd','javascript:alert(1)','https://user:password@example.com','https://a\n.example','--help'])
def test_rejects_unsafe_atlas_url(store,url):
    with pytest.raises(ValueError): store.set('atlas_url',url)

def test_power_requires_confirmation(store):
    calls=[]; a=Actions(store,calls.append)
    with pytest.raises(PermissionError): a.execute('shutdown')
    assert not calls
    a.execute('restart',confirmed=True); assert calls==[['systemctl','reboot']]

def test_volume_and_timer_allowlisted(store):
    calls=[]; a=Actions(store,calls.append)
    a.execute('volume 42'); a.execute('timer 3')
    assert calls[0]==['wpctl','set-volume','@DEFAULT_AUDIO_SINK@','42%']
    assert '--on-active=3m' in calls[1]

def test_search_does_not_follow_symlink(store,tmp_path,monkeypatch):
    home=tmp_path/'home'; home.mkdir(); approved=home/'notes'; approved.mkdir(); outside=tmp_path/'outside'; outside.mkdir()
    (approved/'heart.txt').write_text('ok'); (outside/'secret-heart.txt').write_text('no')
    (approved/'escape').symlink_to(outside,target_is_directory=True)
    monkeypatch.setattr(Path,'home',classmethod(lambda cls: home))
    store.set('search_roots',json.dumps([str(approved)]))
    result=Actions(store).execute('search heart')
    assert 'heart.txt' in result and 'secret-heart' not in result
    with pytest.raises(ValueError): store.set('search_roots',json.dumps([str(outside)]))

def test_speech_punctuation_still_requires_power_confirmation(store):
    calls=[]; a=Actions(store,calls.append)
    a.execute('Open Terminal.')
    assert calls==[['konsole']]
    with pytest.raises(PermissionError): a.execute('Shutdown.')
    assert calls==[['konsole']]


def test_gui_launch_does_not_wait_for_or_kill_application(tmp_path,monkeypatch):
    import sys
    import time
    from jarvis_desktop.actions import launch
    monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path))
    started=time.monotonic()
    proc=launch([sys.executable,'-c','import time; time.sleep(30)'])
    try:
        assert time.monotonic()-started<3
        assert proc.poll() is None
    finally:
        proc.terminate();proc.wait(timeout=3)
    assert (tmp_path/'jarvis-os/desktop-actions.log').stat().st_mode & 0o777==0o600


def test_gui_immediate_failure_reports_logs(tmp_path,monkeypatch):
    import sys
    from jarvis_desktop.actions import launch
    monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path))
    with pytest.raises(RuntimeError,match='open Logs'):
        launch([sys.executable,'-c','raise SystemExit(7)'])
