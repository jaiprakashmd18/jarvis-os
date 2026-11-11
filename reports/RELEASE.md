# JARVIS OS 1.0 release candidate — 2026-11-11

Status: ISO built; offline QEMU installation, disk boot, sign-in, native data
persistence and service recovery passed. VMware release certification remains
pending. This report records observed results, not an assertion that VMware
installation is certified. No Windows host or VMware connection is available.
The build used pinned Ubuntu 24.04 userspace in rootless Docker on this Debian
cloud executor, not an Ubuntu VM. No environment publication or Git push was made during validation.

## Verified inputs

- Kubuntu 24.04.3 amd64 ISO: SHA256
  `8c69dd380e5a8969b77ca1708da59f0b9a50d0c151f0a65917180585697dd1e6`;
  SHA256SUMS.gpg verified against Ubuntu CD image key fingerprint
  `843938DF228D22F7B3742BC0D94AA3F0EFE21092`.
- Assistant: Git commit `3a1a06ad6d57d91460665af4a3a9ace816485630` with
  patches/0001-missing-power-supply.patch. Its original lockfiles remain intact.
- Whisper base.en: immutable Hugging Face commit
  `5359861c739e955e79d9a303bcbc70fb988958b1`, LFS SHA256
  `a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002`.
- Official Node 22.23.4 archive and Ubuntu builder image digest are pinned in
  config/node.json and config/builder.json. Node download SHA256 was verified.

The network download denials from initial setup are resolved. Earlier settings
save failures are historical, not a current download blocker. See
HISTORICAL-SETUP.md for initial results; this report supersedes its status.

## Observed validation

| Check | Result | Evidence/limits |
|---|---|---|
| Patched upstream core/API suite | 91 passed | logs/real-tts-python.txt; includes actual CPU espeak synthesis |
| Frontend TypeScript, 22 Vitest tests, production build in Ubuntu userspace | Passed | logs/ubuntu-web-build.txt |
| Chromium first-run/chat/approval/memory/login and voice flow | 3 E2E passed | logs/browser-real-tts.txt; real espeak, diagnostic recognition and model provider |
| Native desktop and boot-config tests | 25 passed | logs/desktop-current.txt; includes command validation, confirmation, data persistence, wake opt-in/default/fallback, 640-pixel sizing, F11/Esc keyboard behavior, plain transcript and explicit casper/noswap regression and microphone cancellation during process launch and persistent GUI launch regression |
| Actual model inference | Passed | logs/real-stt.txt: “Open Terminal.” from generated speech; CPU-only whisper.cpp |
| Noble package assembly and dpkg installation | Passed | logs/release-package.txt, package-with-indicator.txt, package-install.txt |
| Packaged production API/web as UID 65534 (unprivileged) | Passed | logs/nobody-service-current.txt and package-functional.txt |
| Packaged actual STT/TTS | Passed | logs/package-functional.txt; real CPU transcript and 70,752-byte WAV through authenticated API |
| Account setup, health and saved memory | Passed | logs/package-functional.txt; synthetic account only in temporary test data |
| Saved memory after service stop/start | Passed | logs/package-restart.txt; not an OS reboot or package migration test |
| Packaged native GUI as unprivileged user | Passed | logs/native-package.txt; offscreen typed help, resize and settings/notes close/reopen; font cache warnings caused by the test UID having no writable home |
| Test-data hygiene | Passed | logs/image-hygiene.txt; temporary test account/databases/secret removed before squashfs build |
| Original device metadata preserved | Passed | logs/image-hygiene.txt; rootless extraction uses pseudo nodes with original device major/minor and mode |
| BIOS and UEFI boot entries | Present | dist/boot-layout.txt; original EFI appended image and GRUB boot image preserved |
| Software-emulated UEFI firmware and GRUB menu | Passed | evidence/uefi-boot.png; QEMU/OVMF with no disk attached |
| Branded live boot splash and systemd startup | Observed | evidence/live-progress.png and live-boot-status.png; corrected casper kernel command line |
| Offline Calamares installation | Passed in QEMU | evidence/installer-complete.png; new 40 GiB disposable virtual disk |
| UEFI disk boot without ISO, account sign-in and JARVIS autostart | Passed in QEMU | evidence/installed-login.png, installed-desktop.png, installed-root-service.png |
| Native note/preferences after offline OS reboot | Passed in QEMU | evidence/reboot-note-persisted.png and reboot-settings-persisted.png |
| Stop/restart backend while desktop/local actions remain usable | Passed in QEMU | evidence/installed-terminal-service-off.png and installed-service-recovered.png |

## Recoverable build findings

The build now handles rootless device nodes without ignoring extraction failures,
uses recursive /dev binds so APT's verifier sees the actual /dev/null, retains
required proxies through sudo, and fails on APT update/signature errors. No TLS,
checksum or package-signature verification was disabled.

Kubuntu's squashfs intentionally lacks the kernel/initrd kept in casper. The
recipe restores the unmodified signed kernel and generates a matching live initrd.
The original boot menu assumed a casper default embedded in the original initrd;
the first candidate reached an initramfs shell (evidence/initial-live-boot.png).
The corrected menu explicitly passes boot=casper and noswap in every live entry.
The original stray grub_platform command was removed. Failed attempts are retained
as logs and are not counted as successful live desktop tests.

Mapping the entire extracted tree invalidated GRUB's boot image references.
scripts/assemble-iso.py instead replaces only modified data/config files and
replays the original boot layout. The original detached squashfs signature is
removed because it does not sign the remix. Ubuntu's signed APT channels stay
intact. Source bootloader/account/locale/partition confirmation modules are
preserved; their disk-selection and formatting-confirmation screens were exercised in the dedicated QEMU installation test.

The native microphone tray indicator stays visible during opt-in wake capture,
including while the main window is minimized. Wake mode refuses to start without
a desktop tray indicator and always defaults to off. No recognized or model-
generated text can execute arbitrary shell commands; wake capture only fills the
entry for review. Actual microphone, wake accuracy and speaker output remain
pending guest checks.

## Live desktop result

The standard VGA/Nehalem diskless UEFI test reached Plasma, its panel/launcher,
KDE welcome and the automatically started JARVIS command center. This hardware
configuration avoided the earlier VirtIO/CPU-max renderer failure without
changing distributed desktop settings. Evidence: live-desktop.png and
standard-vga-services.png. The system was booted from the ISO with no writable
guest disk attached. This does not validate installation or disk persistence.

## Required VMware checks still pending

Follow docs/VMWARE.md using a separate UEFI VM and a new blank VMDK. No physical
disks or existing data disks should be mapped.

- Live Plasma desktop and assistant autostart; disk non-mount/non-write behavior.
- Calamares disk selection and formatting confirmation, installation, removal of
  live-only packages, then cold boot and sign-in with the ISO disconnected.
- Browser, Dolphin, Konsole, System Settings, display resizing, network, speaker,
  lock screen, power menu, Discover and signed base updates.
- Actual typed desktop actions, push-to-talk and opt-in wake capture, visible
  microphone indicator, transcript, real action and audible response.
- Anatomy atlas guest-browser launch with your URL, or the documented local test
  page; your real atlas URL has not been supplied or tested.
- Settings and both memory stores across an OS reboot and offline cold boot.
- User service autostart/restart policy and recovery while Plasma stays usable.
- A versioned package upgrade and rollback with data preservation. Reinstalling
  the same package during building is not a versioned migration test.
- Secure Boot is not certified; the initial VMware procedure disables it.

Ollama is optional and no model is bundled. Its conversation behavior is not
claimed tested here. Actual CPU recognition/synthesis is verified independently
of any LLM, paid API, external server or GPU.

## QEMU graphics diagnosis

The initial software-emulated run used CPU max and unaccelerated VirtIO VGA.
It reached the live console and graphical Kubuntu welcome prompt. KWin then
segfaulted; guest logs report “failed to create dri3 screen” and “failed to load
driver: virtio_gpu”, followed by Plasma startup timeouts. Software Qt/Mesa and
compositing overrides were tried in the ephemeral guest; a successful complete
Plasma desktop was not recorded in that configuration. This is a failed desktop check for that
emulation configuration, not a passed release test. See logs/qemu-graphics.txt,
logs/qemu-guest-session.txt and evidence/live-plasma.png.

The same live guest's user manager automatically started jarvis.service; the
first readiness attempt timed out under emulation, then its restart policy
recovered and the expected backend ping and web readiness were logged. This is
additional live-service evidence, not proof the graphical command center opened.
A separate standard VGA/Nehalem run reached the Plasma desktop and automatically opened the JARVIS native window. See evidence/live-desktop.png and evidence/standard-vga-services.png. No user units were failed in that run. No workaround
from that diagnostic guest was baked into the distributed desktop defaults.

The image retains the pinned point-release base with signed update channels;
available base updates have not all been applied. Applying updates and verifying
the resulting installed system remains part of the required VMware checklist.

## Live action regression and atlas flow

A typed “open terminal” initially exposed a launcher defect: synchronous
subprocess.run killed a long-running GUI at its 15-second timeout. The corrected
handler detaches GUI launches, checks immediate startup failures, and keeps a
private action log accessible through Logs. The live guest was patched with the
same source packaged into the final artifacts; Konsole then remained open beyond
the previous timeout. Evidence: live-launch-fixed.png. Two regression tests cover
persistent launches and immediate failures.

The anatomy URL was saved through the native Settings UI and “Open my anatomy
atlas” opened Firefox inside the guest. The visible page at 127.0.0.1:9123 showed
“Anatomy atlas local test”. Evidence: atlas-configured.png and atlas-browser.png.
Your real URL and its 3D content remain untested. These guest changes lived only
in the test VM's RAM overlay, not in the distributed ISO.

SDDM configuration inspection found the initial numeric override was superseded
by the base default.conf. The brand override now sorts last as zz-jarvis.conf;
the installed-system login screen rendered with the JARVIS background (evidence/installed-login.png).

The public desktop configuration, live polkit rule and branding assets were
corrected to explicit 0644 files/0755 directories after an unprivileged-read
audit found copied source files retained mode 0600. Generated system files now
use umask 022; the empty machine-id is not world-writable. Unprivileged read and
non-write checks passed (logs/integration-permissions.txt). This fix is included
in the final ISO and its installation-test image.


## Dedicated offline installation result

Calamares completed an offline normal installation onto a newly created 40 GiB
QCOW2 test disk using GPT, a 300 MiB FAT32 ESP and an ext4 root. Only this new
file-backed disk was writable; no physical disks were mapped. The normal
keyboard, account, explicit disk-selection, summary and formatting-confirmation
screens were exercised. The test timezone is synthetic and is not a user
location preference. Evidence: installer-summary.png, installer-confirmation.png,
installer-complete.png and logs/calamares-completion.txt (completion: succeeded).
The unmodified base's setup includes two initramfs generations and was slow
under CPU emulation; both completed. Live shutdown logged a failed CD-ROM
unmount while the ISO was still in use, then completed casper shutdown and
poweroff after Enter. The installed target was already unmounted.

A new QEMU process then booted that disk and the same persistent EFI variables
with no ISO/CD-ROM image attached. Networking was disconnected before OS boot.
The JARVIS boot splash, branded SDDM login and synthetic account sign-in worked.
Plasma reached its desktop/panel and JARVIS opened automatically without terminal
commands. Evidence: installed-uefi.png, installed-splash.png, installed-login.png,
installed-desktop.png and logs/installed-boot-command.txt. The root filesystem was
/dev/vda2 ext4 (installed-root-service.png).

The per-user jarvis.service was active, the actual production readiness helper
returned True, and API/web sockets were bound to 127.0.0.1:8000/3000
(installed-ready-private.png). After deliberately stopping that service, native
“open terminal” still opened Konsole while Plasma stayed usable
(installed-service-stopped.png, installed-terminal-service-off.png). A test note
and atlas URL were saved through the native GUI; these synthetic values are
only in the ignored test disk, not the ISO or source archive.


The manually restarted production service returned ready again
(installed-service-recovered.png). After an actual offline OS reboot and a
second graphical sign-in, JARVIS autostarted and the saved test note, atlas URL
and disabled speech-reply preference were still present. Wake capture remained
off. Evidence: reboot-login.png, reboot-note-persisted.png and
reboot-settings-persisted.png. This validates native saved-data persistence;
upstream chat memory was separately checked across a service restart, not an
OS reboot. A typed shutdown displayed the required confirmation dialog
(installed-power-confirmation.png).

The supplemental guest used QEMU TCG, OVMF UEFI, Nehalem CPU, four vCPUs,
6 GiB RAM and standard VGA. There is no accelerated GPU or physical audio
backend. These observed results do not certify Windows VMware hardware,
actual microphone/speakers, 3D atlas content, signed-system update execution,
a schema-changing package upgrade, or Secure Boot. Those checks remain pending
in docs/VMWARE.md. Source changes are present in the jarvis-os workspace and
source archive. No environment publication was performed during validation.
