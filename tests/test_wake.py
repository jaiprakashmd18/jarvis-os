import os
import time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt5.QtWidgets import QApplication
from jarvis_desktop.wake import wake_command
from jarvis_desktop.app import Window


def test_wake_only_matches_deliberate_prefix():
    assert wake_command('Hey Jarvis, open terminal')=='open terminal'
    assert wake_command('JARVIS shutdown')=='shutdown'
    assert wake_command('Please ask Jarvis to open terminal') is None
    assert wake_command('open terminal') is None


def test_wake_off_by_default_and_missing_model_stops(tmp_path,monkeypatch):
    monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path))
    monkeypatch.setenv('JARVIS_VOICE_MODEL',str(tmp_path/'absent.bin'))
    app=QApplication.instance() or QApplication([])
    window=Window(); assert not window.wake.isChecked()
    window.wake.setChecked(True)
    deadline=time.monotonic()+3
    while window.wake_worker.isRunning() and time.monotonic()<deadline:
        app.processEvents(); time.sleep(.01)
    app.processEvents()
    assert not window.wake.isChecked()
    assert 'model missing' in window.transcript.toPlainText().lower()
    assert window.entry.text()==''  # detecting or failing wake never runs actions
    window.resize(640,480); app.processEvents()
    assert window.minimumSizeHint().width()<=640
    window.close()


def test_stop_waits_for_process_launch_and_terminates_capture(monkeypatch):
    import threading
    from jarvis_desktop.wake import WakeWorker
    import jarvis_desktop.wake as module
    entered=threading.Event();release=threading.Event();terminated=threading.Event();stopped=threading.Event()
    class Child:
        returncode=None
        def __init__(self,*a,**kw):
            entered.set();assert release.wait(2)
        def poll(self): return self.returncode
        def terminate(self): self.returncode=-15;terminated.set()
        def communicate(self,timeout=None):
            assert terminated.wait(2);return '',''
    monkeypatch.setattr(module.subprocess,'Popen',Child)
    worker=WakeWorker('python','model')
    capture=threading.Thread(target=lambda: worker.invoke(['arecord'],3))
    capture.start();assert entered.wait(1)
    def stop(): worker.stop();stopped.set()
    stopper=threading.Thread(target=stop);stopper.start()
    assert not stopped.wait(.05)
    release.set();stopper.join(2);capture.join(2)
    assert terminated.is_set() and stopped.is_set()
