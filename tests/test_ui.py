import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt5.QtWidgets import QApplication
from jarvis_desktop.app import Window


def test_keyboard_command_and_settings_persist(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path))
    app=QApplication.instance() or QApplication([])
    window=Window(); window.speech.setChecked(False); window.show()
    window.entry.setText('help'); window.command()
    import time
    deadline=time.monotonic()+5
    while window.jobs and time.monotonic()<deadline:
        app.processEvents(); time.sleep(.01)
    assert not window.jobs
    assert 'Open my anatomy atlas' in window.transcript.toPlainText()
    window.store.set('atlas_url','http://127.0.0.1:9123/atlas')
    window.store.remember('test memory'); window.resize(640,480); app.processEvents()
    window.close()
    second=Window()
    assert second.atlas.text()=='http://127.0.0.1:9123/atlas'
    assert second.rows==[(1,'test memory')]
    second.close()


def test_keyboard_fullscreen_escape_and_plain_transcript(tmp_path,monkeypatch):
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path))
    app=QApplication.instance() or QApplication([])
    w=Window();w.show();app.processEvents()
    QTest.keyClick(w.entry,Qt.Key_F11);app.processEvents()
    assert w.isFullScreen()
    QTest.keyClick(w.entry,Qt.Key_Escape);app.processEvents()
    assert w.isMinimized()
    w.transcript.appendPlainText('<img src="file:///test-only">')
    assert '<img' in w.transcript.toPlainText()
    w.close()
