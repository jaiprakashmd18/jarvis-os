"""Wake recognition only prepares a transcript; it never executes a command."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from PyQt5.QtCore import QThread, pyqtSignal


def wake_command(text):
    match = re.match(r'^\s*(?:hey\s+)?jarvis\b[\s,:.!-]*(.*)$', text, re.I)
    return match.group(1).strip() if match else None


class WakeWorker(QThread):
    state = pyqtSignal(str)
    detected = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, python, model, parent=None):
        super().__init__(parent)
        self.python, self.model = python, model
        self.stopping = threading.Event()
        self.process = None
        self.process_lock = threading.Lock()

    def stop(self):
        with self.process_lock:
            self.stopping.set()
            if self.process and self.process.poll() is None:
                self.process.terminate()

    def invoke(self, argv, timeout):
        with self.process_lock:
            if self.stopping.is_set():
                return ''
            self.process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = self.process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill(); self.process.communicate()
            raise RuntimeError('Voice operation timed out; use typed commands.')
        if self.process.returncode and not self.stopping.is_set():
            raise RuntimeError('Voice input unavailable: '+stderr.strip()[-300:])
        return stdout.strip()

    def run(self):
        try:
            if not Path(self.model).is_file():
                raise RuntimeError('Local model missing; wake-word listening stays off. Use typed commands.')
            while not self.stopping.is_set():
                fd, name = tempfile.mkstemp(suffix='.wav'); os.close(fd)
                try:
                    self.state.emit('Listening for Jarvis · MICROPHONE ON')
                    self.invoke(['arecord','-q','-d','4','-f','S16_LE','-r','16000','-c','1',name], 8)
                    if self.stopping.is_set(): break
                    self.state.emit('Processing wake-word audio · microphone off')
                    text = self.invoke([self.python, str(Path(__file__).with_name('voice.py')), self.model, name], 120)
                    command = wake_command(text)
                    if command is not None:
                        self.detected.emit(command)
                        break
                finally:
                    Path(name).unlink(missing_ok=True)
        except Exception as exc:
            if not self.stopping.is_set(): self.error.emit(str(exc))
        finally:
            self.stop()
