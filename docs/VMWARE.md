# VMware Workstation release verification

All checks below are pending until observed in VMware on the Windows host.
Use a separate VM from the build VM. Record ISO/package SHA256, Workstation
version, VM resources, firmware mode, date, screenshots and relevant journal logs
in reports/RELEASE.md. Never mark a check passed from a script's existence.

On Windows, place the ISO and its SHA-256 file in the same folder and verify them
in PowerShell before attaching the image:

```powershell
$jarvisExpected = (Get-Content .\jarvis-os-1.0.0-amd64.iso.sha256).Split()[0]
$jarvisActual = (Get-FileHash .\jarvis-os-1.0.0-amd64.iso -Algorithm SHA256).Hash
if ($jarvisActual -ne $jarvisExpected) { throw "ISO checksum mismatch" }
```

1. Create a new custom Linux Ubuntu 64-bit VM, **UEFI**, 4 vCPU, 8 GiB RAM,
   one **new blank 40 GiB VMDK**, NAT networking, sound card, display auto-resize.
   Disable Secure Boot for the first test: the repacked image is not certified
   for it. Do not configure raw/physical disks, shared folders, USB storage,
   host disk passthrough or a host microphone until you intentionally test it.
2. Attach dist/jarvis-os-1.0.0-amd64.iso and cold boot. Select the live session.
   Reach Plasma; inspect the branded splash, Breeze login/background and JARVIS
   launcher. Use `lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS` and `swapon --show`
   to confirm attached virtual disks are not mounted and swap is inactive.
   The live overlay disables desktop UDisks mounting and adds noswap. These
   controls require observation; they are not a verified disk-write guarantee.
3. Open the **base Kubuntu installer**. Select keyboard/timezone and create your
   own account. Confirm the disk list contains only the blank test VMDK. Review
   the partition summary. Explicitly choose it and approve formatting. Cancel
   once before confirmation and verify no partition change. Reopen and install.
   Never select a host physical disk or an existing data VMDK.
4. Shut down after installation. Disconnect the ISO in VM settings, set disk
   first in boot order and cold boot. Sign in. Record successful disk boot and
   ensure the installer/live-only packages are removed as intended.
5. Open browser, Dolphin, Konsole and System Settings. Change display size and
   verify auto-resize. Check NAT browsing and speaker output through KDE tools.
   Lock/unlock and test the power menu. Confirm signed base update sources.
6. JARVIS should start without a terminal. Run `open terminal` and observe the
   real window and result. Test Tab/Shift+Tab focus, Enter, F11, Esc, 640×480 and
   normal/fullscreen resizing. Check Meta+J; bind it if packaging did not register.
7. Pass a microphone into the guest intentionally. Use docs/VOICE.md to record
   a phrase, review transcript and run the action. Observe audible speech;
   diagnostic browser audio in the cloud does not count as this test.
8. Settings → anatomy atlas URL: use your real URL. If unavailable, in the guest
   run `mkdir -p /tmp/atlas-test`, create `/tmp/atlas-test/index.html` with a visible
   “Anatomy atlas test” heading, and run `python3 -m http.server 9123 --bind
   127.0.0.1 --directory /tmp/atlas-test` in Konsole. Set
   `http://127.0.0.1:9123/`, run “Open my anatomy atlas” and observe the guest
   browser page. Record the actual URL check separately as pending.
9. Set an atlas URL, approve a home folder, save a note and upstream memory.
   Reboot (not merely restart the application) and inspect all saved values.
   Exercise edit/export/delete controls on test data.
10. Disconnect NAT, cold boot and sign in. Run local app/volume/timer/search
    commands and CPU voice. Verify typed fallback for missing microphone/model.
    Open Assistant; absent Ollama/model/network should show useful errors while
    the desktop stays responsive. Restore networking after recording results.
11. Stop jarvis.service and verify Plasma, its terminal and native commands still
    work. Use Retry service and then Open Assistant. Simulate server termination;
    verify the unit restarts it and logs the failure. Test disabling via marker.
12. Snapshot the VM, back up test data, apply signed Ubuntu updates, then install
    a second versioned JARVIS package as in DESKTOP.md. Confirm package version,
    boot and data persistence; test recovery using the original package/backup.
    Reinstalling the same DEB alone does not validate a schema-changing upgrade.

A release requires all mandatory checks passed, including offline actual speech,
install/disk cold boot, and upgrade persistence. Actual atlas URL can be recorded
pending if the local-page flow passed and the real URL is unavailable. Do not
publish a release described as complete while mandatory checks are unresolved.
