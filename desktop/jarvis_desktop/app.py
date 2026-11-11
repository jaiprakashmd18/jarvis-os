"""Native desktop fallback, offline actions, and entry into the existing web assistant."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from PyQt5.QtCore import QThread, QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QCheckBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QTabWidget,
    QPlainTextEdit, QVBoxLayout, QWidget, QSystemTrayIcon, QMenu)
from .actions import Actions, Store
from .service import ready
from .wake import WakeWorker


class Work(QThread):
    done = pyqtSignal(str)
    error = pyqtSignal(str)
    def __init__(self, fn, parent):
        super().__init__(parent)
        self.fn = fn
    def run(self):
        try:
            self.done.emit(str(self.fn()))
        except Exception as exc:
            self.error.emit(str(exc))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('JARVIS OS · Command Center')
        self.resize(960, 680)
        self.store = Store()
        self.jobs = []
        self.recorder = None
        self.audio_file = None
        self.wake_worker = None
        self.mic_tray = QSystemTrayIcon(QIcon.fromTheme('audio-input-microphone'), self)
        menu = QMenu(self)
        stop = menu.addAction('Stop microphone listening')
        stop.triggered.connect(self.stop_microphone)
        self.mic_tray.setContextMenu(menu)
        self.voice_python = os.environ.get('JARVIS_VOICE_PYTHON', '/opt/jarvis/upstream/.venv/bin/python')
        self.voice_model = os.environ.get('JARVIS_VOICE_MODEL', '/opt/jarvis/models/ggml-base.en.bin')
        self.setStyleSheet('QWidget{background:#101923;color:#e4edf5;font-size:15px} QLineEdit,QTextEdit,QListWidget{background:#192837;border:1px solid #456;padding:8px} QPushButton{padding:9px;background:#244354} QPushButton:focus{border:2px solid #8dddf2}')
        main = QWidget(); self.setCentralWidget(main); layout = QVBoxLayout(main)
        top = QHBoxLayout(); layout.addLayout(top)
        top.addWidget(QLabel('JARVIS OS 1.0'))
        self.state = QLabel('Offline local commands ready · microphone off'); self.state.setWordWrap(True); top.addWidget(self.state)
        self.button(top, 'Normal desktop (Esc)', self.showMinimized)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        page = QWidget(); box = QVBoxLayout(page); self.tabs.addTab(page, 'Commands')
        self.transcript = QPlainTextEdit(); self.transcript.setReadOnly(True); self.transcript.setAccessibleName('Command transcript'); box.addWidget(self.transcript)
        self.entry = QLineEdit(); self.entry.setPlaceholderText('Type help or Open my anatomy atlas'); self.entry.setAccessibleName('Command'); self.entry.returnPressed.connect(self.command); box.addWidget(self.entry)
        row = QHBoxLayout(); box.addLayout(row)
        self.send = self.button(row, 'Run command', self.command)
        self.ptt = QPushButton('Hold to talk · microphone off'); row.addWidget(self.ptt)
        self.ptt.pressed.connect(self.record); self.ptt.released.connect(self.transcribe)
        self.button(row, 'Open Assistant', self.open_assistant)
        row = QHBoxLayout(); box.addLayout(row)
        self.button(row, 'Retry service', self.retry)
        self.button(row, 'Logs', self.logs)
        self.button(row, 'Full screen (F11)', self.fullscreen)
        data = QWidget(); data_box = QVBoxLayout(data); self.tabs.addTab(data, 'Saved data')
        data_box.addWidget(QLabel('Local notes and approved memories. Assistant chat memory is managed inside Assistant.'))
        self.memories = QListWidget(); self.memories.setAccessibleName('Saved memories'); data_box.addWidget(self.memories)
        self.memory_text = QLineEdit(); self.memory_text.setPlaceholderText('New or edited memory'); data_box.addWidget(self.memory_text)
        self.memories.currentRowChanged.connect(self.select_memory)
        row = QHBoxLayout(); data_box.addLayout(row)
        self.button(row, 'Add', self.add_memory); self.button(row, 'Save edit', self.edit_memory)
        self.button(row, 'Delete selected', self.delete_memory)
        row = QHBoxLayout(); data_box.addLayout(row)
        self.button(row, 'Export JSON', self.export)
        self.button(row, 'Delete all local data', self.erase)
        settings = QWidget(); form = QFormLayout(settings); self.tabs.addTab(settings, 'Settings')
        self.atlas = QLineEdit(self.store.get('atlas_url')); form.addRow('Anatomy atlas URL', self.atlas)
        self.roots = QLineEdit(self.store.get('search_roots','[]')); form.addRow('Approved search folders (JSON array)', self.roots)
        self.speech = QCheckBox('Speak local command replies (espeak-ng)'); self.speech.setChecked(self.store.get('speak','true')=='true'); form.addRow(self.speech)
        save = QPushButton('Save settings'); save.clicked.connect(self.settings); form.addRow(save)
        self.wake = QCheckBox('Listen for Jarvis (this session only; microphone on)'); self.wake.toggled.connect(self.toggle_wake); form.addRow(self.wake)
        form.addRow(QLabel('Wake-word listening is off at every login. Recognized commands require review.\nOptional Ollama: install and select a model in Assistant → Models.\nNo model or paid API is required for local commands.'))
        self.refresh()
        self.transcript.appendPlainText('Local desktop ready. Type help for supported commands. Esc returns to the desktop.')
        self.timer = QTimer(self); self.timer.setInterval(60000); self.timer.timeout.connect(self.transcribe)
        for label in self.findChildren(QLabel): label.setWordWrap(True)
        self.entry.setFocus()

    def button(self, layout, label, callback):
        b = QPushButton(label); b.clicked.connect(callback); layout.addWidget(b); return b

    def job(self, fn, callback):
        w = Work(fn, self); self.jobs.append(w)
        w.done.connect(callback); w.error.connect(self.failure)
        w.finished.connect(lambda: self.jobs.remove(w))
        w.start()

    def failure(self, message):
        self.state.setText('Error · typed commands available · microphone off')
        self.transcript.appendPlainText('Error: '+message)
        self.send.setEnabled(True)

    def command(self):
        if self.wake.isChecked():
            self.wake.setChecked(False); self.failure("Wake listener is stopping. Review and run the command again."); return
        text = self.entry.text().strip()
        if not text or not self.send.isEnabled(): return
        confirmed = False
        if text.lower().rstrip('.!?') in ('shutdown', 'restart'):
            confirmed = QMessageBox.question(self, 'Confirm power action', f'{text.capitalize()} this guest now?') == QMessageBox.Yes
            if not confirmed: return
        self.entry.clear(); self.transcript.appendPlainText('You: '+text)
        self.send.setEnabled(False); self.state.setText('Processing local command · microphone off')
        # SQLite connections belong to their creating thread.
        def execute():
            store = Store(self.store.path)
            try: return Actions(store).execute(text, confirmed)
            finally: store.close()
        self.job(execute, self.result)

    def result(self, message):
        self.transcript.appendPlainText('JARVIS: '+message); self.refresh(); self.send.setEnabled(True)
        self.state.setText('Local commands ready · microphone off')
        if self.speech.isChecked():
            self.state.setText('Speaking · microphone off')
            def speak():
                subprocess.run(['espeak-ng', '--', message[:1000]], check=True, timeout=120)
                return ''
            self.job(speak, lambda _: self.state.setText('Local commands ready · microphone off'))

    def record(self):
        if self.wake.isChecked(): self.wake.setChecked(False)
        if self.wake_worker and self.wake_worker.isRunning():
            self.failure("Wake listener is stopping; try push-to-talk again."); return
        if self.recorder is not None: return
        fd, self.audio_file = tempfile.mkstemp(suffix='.wav'); os.close(fd)
        try:
            self.recorder = subprocess.Popen(['arecord','-q','-f','S16_LE','-r','16000','-c','1',self.audio_file], stderr=subprocess.DEVNULL)
            self.microphone_indicator('Listening · MICROPHONE ON'); self.ptt.setText('Recording · release to stop'); self.timer.start()
        except OSError as exc:
            self.clear_audio(); self.failure('Microphone unavailable. Use typed commands. '+str(exc))

    def clear_audio(self):
        self.recorder = None
        if self.audio_file:
            Path(self.audio_file).unlink(missing_ok=True)
        self.audio_file = None

    def transcribe(self):
        self.mic_tray.hide()
        self.timer.stop()
        if self.recorder is None: return
        proc = self.recorder; proc.terminate()
        try: proc.wait(timeout=2)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        path = self.audio_file; self.recorder = None; self.audio_file = None
        self.ptt.setEnabled(False); self.ptt.setText('Transcribing · microphone off'); self.state.setText('Processing speech · microphone off')
        def stt():
            try:
                if not Path(self.voice_model).is_file(): raise RuntimeError('Local voice model missing. Use typed commands; see docs/VOICE.md.')
                p = subprocess.run([self.voice_python, str(Path(__file__).with_name('voice.py')), self.voice_model, path], capture_output=True, text=True, timeout=120)
                if p.returncode: raise RuntimeError(p.stderr.strip()[-300:] or 'Speech recognition failed; check microphone and model. Use typed commands.')
                return p.stdout.strip()
            finally: Path(path).unlink(missing_ok=True)
        def transcript(text):
            self.ptt.setEnabled(True); self.ptt.setText('Hold to talk · microphone off')
            self.entry.setText(text); self.state.setText('Transcript ready · review and run command · microphone off')
        self.job(stt, transcript)
        # Always restore the PTT button, including on inference failure.
        self.jobs[-1].finished.connect(lambda: (self.ptt.setEnabled(True), self.ptt.setText('Hold to talk · microphone off')))

    def microphone_indicator(self, text):
        self.state.setText(text)
        if 'MICROPHONE ON' in text:
            self.mic_tray.setToolTip('JARVIS · '+text)
            self.mic_tray.show()
        else:
            self.mic_tray.hide()

    def stop_microphone(self):
        self.wake.setChecked(False)
        if self.recorder: self.transcribe()
        self.mic_tray.hide()

    def toggle_wake(self, checked):
        if not checked:
            if self.wake_worker: self.wake_worker.stop()
            return
        if self.recorder or self.jobs or (self.wake_worker and self.wake_worker.isRunning()):
            self.wake.setChecked(False); self.failure('Finish the current voice operation first.'); return
        if Path(self.voice_model).is_file() and not QSystemTrayIcon.isSystemTrayAvailable():
            self.wake.setChecked(False)
            self.failure('Wake listening requires a visible desktop microphone tray indicator. Use push-to-talk.')
            return
        worker = WakeWorker(self.voice_python, self.voice_model, self)
        self.wake_worker = worker
        worker.state.connect(self.microphone_indicator)
        worker.error.connect(self.failure)
        def detected(text):
            self.entry.setText(text)
            self.transcript.appendPlainText('Wake-word heard. Review the transcript and run the command.')
        worker.detected.connect(detected)
        def finished():
            self.wake.setChecked(False)
            self.mic_tray.hide()
            self.state.setText('Wake listener stopped · microphone off · typed commands ready')
        worker.finished.connect(finished)
        worker.start()

    def retry(self):
        self.job(lambda: subprocess.run(['systemctl','--user','restart','jarvis.service'],check=True,timeout=15).returncode,
                 lambda _: self.transcript.appendPlainText('Service restart requested. Use Open Assistant when ready.'))

    def open_assistant(self):
        def check():
            if not ready(): raise RuntimeError('Assistant is not ready. Use Retry service or Logs. Local desktop commands remain available.')
            subprocess.run(['xdg-open','http://127.0.0.1:3000'],check=True,timeout=15)
            return 'Opened Assistant. Create your owner account on first use.'
        self.job(check, lambda msg: self.transcript.appendPlainText(msg))

    def logs(self):
        def read():
            journal = subprocess.run(['journalctl','--user','-u','jarvis.service','-n','80','--no-pager'],capture_output=True,text=True,timeout=10).stdout
            path = self.store.path.parent/'desktop-actions.log'
            actions = path.read_text(errors='replace')[-16000:] if path.exists() else ''
            return journal+'\nDesktop action log:\n'+actions
        self.job(read, lambda text: self.transcript.appendPlainText(text or 'No service logs yet.'))

    def refresh(self):
        self.rows = self.store.memories(); self.memories.clear()
        self.memories.addItems([f'{mid}: {text}' for mid,text in self.rows])

    def select_memory(self, row):
        if 0 <= row < len(self.rows): self.memory_text.setText(self.rows[row][1])

    def guarded(self, fn):
        try: fn()
        except Exception as exc: QMessageBox.warning(self,'JARVIS',str(exc))

    def add_memory(self):
        self.guarded(lambda: self.store.remember(self.memory_text.text())); self.refresh()

    def edit_memory(self):
        row = self.memories.currentRow()
        if row>=0: self.guarded(lambda: self.store.edit(self.rows[row][0], self.memory_text.text())); self.refresh()

    def delete_memory(self):
        row = self.memories.currentRow()
        if row>=0 and QMessageBox.question(self,'Delete memory','Delete the selected memory?')==QMessageBox.Yes:
            self.store.delete(self.rows[row][0]); self.refresh()

    def export(self):
        path,_ = QFileDialog.getSaveFileName(self,'Export local data','jarvis-data.json','JSON (*.json)')
        if path:
            def write():
                fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600)
                with os.fdopen(fd,'w') as f: f.write(self.store.export())
            self.guarded(write)

    def erase(self):
        if QMessageBox.question(self,'Delete local data','Delete all desktop notes and settings? Assistant chat data is separate.')==QMessageBox.Yes:
            self.store.erase(); self.atlas.clear(); self.roots.setText('[]'); self.refresh()

    def settings(self):
        def save():
            self.store.set('atlas_url',self.atlas.text())
            self.store.set('search_roots',self.roots.text())
            self.store.set('speak','true' if self.speech.isChecked() else 'false')
            QMessageBox.information(self,'Settings','Saved for this user.')
        self.guarded(save)

    def fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def keyPressEvent(self, event):
        if event.key()==Qt.Key_Escape: self.showNormal(); self.showMinimized()
        elif event.key()==Qt.Key_F11: self.fullscreen()
        else: super().keyPressEvent(event)

    def closeEvent(self, event):
        self.mic_tray.hide()
        if self.wake_worker and self.wake_worker.isRunning():
            self.wake.setChecked(False); self.wake_worker.stop()
            if not self.wake_worker.wait(2000):
                event.ignore(); return
        if self.jobs:
            QMessageBox.information(self,'JARVIS','Wait for the current operation or minimize the window.'); event.ignore(); return
        if self.recorder:
            self.recorder.terminate(); self.recorder.wait(timeout=3); self.clear_audio()
        self.store.close(); event.accept()


def main():
    os.umask(0o077)
    app = QApplication(sys.argv)
    window = Window(); window.show()
    sys.exit(app.exec_())

if __name__ == '__main__': main()
