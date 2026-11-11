"""CPU-only STT shared by PTT and opt-in wake-word capture; no network or actions."""
from pathlib import Path
import sys


def transcribe(model_path, audio_path):
    from jarvis_core.voice.audio import read_wav
    import numpy as np
    from pywhispercpp.model import Model
    model_path = Path(model_path)
    if not model_path.is_file():
        raise RuntimeError('Local voice model missing; use typed commands.')
    audio = read_wav(Path(audio_path).read_bytes(), max_seconds=60)
    if audio.duration_s < .15 or audio.rms() < .003:
        return ''
    model = Model(str(model_path), n_threads=2, print_progress=False, print_realtime=False, context_params={'use_gpu': False},
                  redirect_whispercpp_logs_to=None)
    samples = np.asarray(audio.to_float32(), dtype=np.float32)
    return ' '.join(s.text for s in model.transcribe(samples)).strip()


if __name__ == '__main__':
    try:
        print(transcribe(sys.argv[1], sys.argv[2]))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
