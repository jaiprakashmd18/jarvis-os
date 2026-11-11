# Inspected sources and platform

The initially empty jarvis-os repository has no existing implementation,
lockfiles or agent instructions. Its local branch is unborn `work`, and a
successful `git ls-remote origin` returned no refs; there is no remote main yet.
No commits or pushes were made by setup.

Assistant revision: 3a1a06ad6d57d91460665af4a3a9ace816485630.
Python >=3.11, uv workspace and uv.lock; core and FastAPI in core/ and services/api/.
Frontend apps/web uses Next 15.5.29, React 19.1.1, npm package-lock.json,
Node >=20, standalone production output. `npm ci` installs the project-local
Next executable; `npm run build` succeeds on Linux. “next is not recognized”
did not reproduce after installing from the lockfile. Do not install Next globally.

Production execution: Python `-m jarvis_api.main`, with Alembic migrations and
SQLite; Node `apps/web/.next/standalone/server.js`, with .next/static and public
copied alongside. Backend ping: /api/system/ping. The distribution's desktop
profile uses upstream JARVIS_ENV=desktop, not its cloud production profile,
which requires secure HTTPS cookies and MFA. This loopback desktop profile still
requires first-owner account creation; it ships no accounts or keys. Secrets and
SQLite are redirected outside /opt into per-user data. PYTHONPATH points at the
pinned source because upstream's API_DIR locates migrations relative to source.

Existing frontend features reused unchanged: conversation history, memory CRUD,
export, model configuration, approvals, system status and voice console. Core
currently registers time, telemetry and memory tools, not desktop actions.
The native bridge adds deterministic desktop commands independent of any model.
The bridge's notes/settings and the upstream assistant database are separate;
the UI labels this distinction. Wake-word detection is not implemented.

Environment: Debian 13 container, x86-64, Node 24.22.1, Python 3.12.14,
uv 0.13.5, Chromium available, approximately 60 GiB disk space at inspection.
No /dev/kvm, VMware, sudo or scoped system-package installer. Systemd binaries
exist but there is no graphical user session here. An Ubuntu build VM remains
required for the release ABI and privileged squashfs/chroot operations.

Installer reconnaissance: Ubuntu noble universe Packages.xz advertises
calamares 3.3.5-0ubuntu4 and calamares-settings-kubuntu 1:24.04.39.
The Kubuntu settings DEB and common DEB were downloaded via HTTPS and inspected
without executing their contents. /etc/calamares/settings.conf has show steps
welcome, locale, keyboard, pkgselect, partition, users, summary; the exec steps
include partition, unpackfs, users, bootloader. `prompt-install: true`.
unpackfs.conf uses /cdrom/casper/filesystem.squashfs. This establishes a candidate
workflow, not validation of the unavailable 24.04.3 ISO. Its exact payload and
UEFI boot/install must be inspected before a release can be claimed. The build
script refuses unexpected layouts rather than guessing. No installer settings
are changed by the overlay.

Release Node runtime is separately pinned in config/node.json and bundled, avoiding
a dependency on Noble's older APT Node. Its official archive is SHA256-verified.
