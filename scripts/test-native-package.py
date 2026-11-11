"""Headless functional check, run as nobody within the test-only chroot."""
from PyQt5.QtWidgets import QApplication
from jarvis_desktop.app import Window
import time
app=QApplication([])
w=Window(); w.speech.setChecked(False)
assert not w.wake.isChecked()
w.entry.setText('help');w.command()
end=time.monotonic()+5
while w.jobs and time.monotonic()<end:
    app.processEvents();time.sleep(.01)
assert 'Open my anatomy atlas' in w.transcript.toPlainText()
w.store.set('atlas_url','http://127.0.0.1:9123/atlas')
w.store.remember('Native package persistence fixture')
w.resize(640,480); assert w.minimumSizeHint().width()<=640
w.close()
w=Window();assert w.atlas.text()=='http://127.0.0.1:9123/atlas'
assert any('Native package persistence fixture' in x[1] for x in w.rows)
w.close()
print('Packaged native GUI, typed command, opt-in default, resizing and data reopen passed as unprivileged user.')
