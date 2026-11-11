# Local CPU voice

The DEB includes pywhispercpp from the assistant's frozen uv voice extra,
using two CPU threads, and espeak-ng from Ubuntu's signed repositories.
The release model is English base.en. Other languages/models are future work.
No cloud STT or paid API is enabled by this distribution.

The native command center records 16 kHz mono S16_LE with arecord only while
Hold to talk is pressed (maximum 60 seconds). It shows MICROPHONE ON, then
processing, then the transcript. Review the transcript and run the command;
recognized speech never executes immediately. A session-only opt-in wake listener is available in Settings. It records bounded
four-second windows, runs CPU recognition, and stops after hearing an initial
“Jarvis” or “Hey Jarvis”. It fills the command entry for review; it never runs it.
The microphone indicator tracks capture; disabling the option stops its capture
or inference process. It is always off at each application start. A desktop tray microphone indicator
remains visible during capture; wake listening is refused if no tray is available.
Missing devices, ALSA capture errors, missing models and inference errors fall
back to typed commands. Speaker output is optional in Settings. F11 toggles
full screen and Esc minimizes to the normal desktop.

This design uses ALSA's default capture device. In VMware select a microphone
in KDE's sound settings and ensure it is passed into the guest; physical
microphone and speaker behavior is not validated in the cloud container.
The existing assistant Voice Console is also available, but its push-to-talk
conversational replies need a selected model provider; native core actions do not.

## Verified immutable model input

These pins are complete in config/voice.json. The following steps describe
provenance and how to review a future model upgrade; no new permission is needed
for the current download.

1. Permit huggingface.co in environment settings and retry the official model
   repository. Inspect the actual redirect and allow its required CDN hostname.
2. Select a specific commit of `ggerganov/whisper.cpp` on Hugging Face containing
   `ggml-base.en.bin`. Read the Git LFS pointer at that revision; its
   `oid sha256:` is the artifact digest. Review the source/revision and license.
3. Set config/voice.json `url` to
   `https://huggingface.co/ggerganov/whisper.cpp/resolve/<full-commit>/ggml-base.en.bin`
   and `sha256` to the pointer's SHA256. Never use a moving main URL in a release.
4. Run `python3 scripts/fetch-model.py`; it verifies the digest before replacing
   the cached model. Build-package refuses a missing or mismatched model.
5. In the fresh VMware guest, hold the button, say “Open terminal”, release,
   verify the transcript, run it, and observe both Konsole and the audible reply.
   Repeat disconnected from the network and after a reboot.

Do not download models at login. Package them once after verification. The native listener's prefix parsing, off-by-default state and missing-model
fallback are tested. Real wake capture and microphone reliability still need
VMware testing. The existing browser Voice Console does not provide wake words.

The pinned base.en artifact has been SHA256-verified. The installed package
recognized a generated “Open terminal” WAV using actual CPU whisper.cpp, and
returned a real espeak WAV through the authenticated API. These checks validate
inference/synthesis, not a physical microphone or speaker. See the current report.
