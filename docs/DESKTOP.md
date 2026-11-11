# Desktop use and recovery

The base Kubuntu Plasma desktop supplies its launcher/taskbar, Firefox, Dolphin,
Konsole, System Settings, lock screen, networking, sound, Discover, updates and
power menu. JARVIS adds a launcher, a requested Meta+J shortcut, a KDE session
autostart and a user service. Meta+J must be checked in VMware (if unbound, set it
in System Settings → Shortcuts → JARVIS Command Center). It is not system-wide
root automation. F11 toggles the native command center; Esc minimizes it.

At login jarvis-session creates a private per-user directory, imports graphical
session variables, starts jarvis.service and opens the native UI. Open Assistant
checks both the backend's expected ping identity and an HTTP 200 from the web
server before launching the browser. Failure gives Retry and Logs controls.
Local desktop commands remain available even if the assistant crashes. First
assistant use requires creating your owner account. No shared login or password
is baked into the ISO.

Local commands: `help`, `open browser`, `open files`, `open terminal`,
`open settings`, `open my anatomy atlas`, `volume 42`, `timer 5`,
`search heart`, `remember Review anatomy`, `shutdown`, `restart`.
Power actions require a native confirmation dialog. Atlas URL must be http(s)
without embedded credentials; xdg-open runs in the guest. Configure it in Settings.
Approve search roots explicitly as a JSON array, e.g. `["/home/jai/Documents"]`.
Search is bounded to 20,000 files/50 matches and does not follow symlink folders.
No arbitrary process names, model-generated shell text or shell interpreter are
accepted. Ollama in the upstream web assistant is optional, selected explicitly
in Models; install/pull a CPU-sized model separately. Model conversations do not
have access to the native desktop action handler.

Data: `$XDG_DATA_HOME/jarvis-os` or `~/.local/share/jarvis-os`, private by default.
`desktop.db` stores native settings/notes; `assistant.db` stores upstream account,
chat and memory; `secret.key` protects upstream stored secrets. Manage native
notes in Saved data (add/edit/delete/export/delete all); manage assistant memories
in Assistant → Memory and account export in its Settings. Exports contain personal
data; save them privately. Never copy these into build/package, Git or the ISO.
Audio recordings use a random private temporary file and are deleted after STT.
Local ports 3000/8000 bind only 127.0.0.1; they are not a remote access service.
This does not isolate them from another hostile local user; shared-machine
threats need further hardening. Fixed ports currently support one assistant
session per machine; concurrent OS users need separate ports and web API config.

Inspect/recover in Konsole:

```
systemctl --user status jarvis.service
journalctl --user -u jarvis.service -n 100 --no-pager
systemctl --user restart jarvis.service
```

Disable automatic startup (native tools remain available through the launcher):

```
mkdir -p ~/.config/jarvis-os
touch ~/.config/jarvis-os/disabled
systemctl --user stop jarvis.service
```

Remove that marker to enable next login, or start the service manually.
The unit is started by KDE autostart, not enabled at boot. Standard Plasma
continues running independently. NoNewPrivileges is enabled; advanced mount-namespace restrictions are omitted
for compatibility with unprivileged user managers. Actual graphical session
startup still need guest validation.

Upgrade from a reviewed, checksum-verified DEB:

```
systemctl --user stop jarvis.service
cp -a ~/.local/share/jarvis-os ~/jarvis-os-backup
sudo apt install ./jarvis-os-desktop_1.0.0_amd64.deb
systemctl --user daemon-reload
systemctl --user start jarvis.service
```

Use a versioned backup and the correct new package filename for a future version.
Never overwrite your only backup. Upstream Alembic migrations run on startup;
back up before upgrades. Rollback requires the prior DEB and compatible database
backup; a new schema may not be readable by the old version. Package upgrade and
rollback must be tested before release. Keep Ubuntu's original signed update
channels; use Discover or `sudo apt update && sudo apt upgrade` for base updates.
There is no unattended external JARVIS update feed in this prototype.
