# Build from a clean clone

## Prerequisites

Use a disposable Ubuntu/Kubuntu 24.04 amd64 build VM on your Windows HP Victus:
4 vCPU, 12 GiB RAM, 80 GiB virtual disk, Internet, normal sudo-enabled build user.
A separate test VM is required. Never map host physical disks into either VM.
The cloud executor is suitable for assistant tests but is Debian, not this VM.

Required destinations: github.com and Git asset hosts, registry.npmjs.org,
pypi.org/files.pythonhosted.org, Ubuntu's signed APT mirrors,
cdimage.ubuntu.com, nodejs.org, huggingface.co and its official redirect CDN.
Network access is working in the current environment. Base ISO, Node and voice
model pins are recorded in config/*.json. Downloads are verified before use.

## Install tools and build assistant

Clone jarvis-os normally, then work in that checkout. Each cloud task is already
isolated; use the existing checkout and do not create a worktree unless requested.
The setup script downloads Node 22 LTS pinned in config/node.json. Its SHA256
was obtained from the versioned official nodejs.org SHASUMS256.txt over HTTPS;
every download/extraction is checked against that committed hash. The runtime
is bundled under /opt/jarvis/runtime/node, because Noble's signed APT archive
supplies Node 18 and cannot satisfy a nodejs>=20 package dependency. No Node PPA
or unverified installer script is used. The assistant lockfiles stay unchanged.

```
./scripts/setup-build-vm.sh
./scripts/prepare-assistant.sh  # safe to rerun; installs the reviewed patch only
```

These use frozen uv and npm locks, run Python and frontend checks, and build the
standalone server. `scripts/fetch-assistant.py` refuses unknown source changes;
it never resets user modifications. Review patches/*.patch when upgrading the
assistant. Run build tools as your ordinary account, not root.

The voice input pin has been completed and verified. Then:

```
./scripts/build-package.sh
(cd dist && sha256sum -c jarvis-os-desktop_1.0.0_amd64.deb.sha256)
```

The checksum file contains a basename; the exact verification command is:
`(cd dist && sha256sum -c jarvis-os-desktop_1.0.0_amd64.deb.sha256)`.
Package contents use /opt/jarvis, /usr/lib/systemd/user, desktop launcher and KDE
autostart. No credentials, databases, developer .env or node_modules are copied.
Build this on Noble: its binary Python speech extensions cannot be presumed
compatible if built on a different glibc/Python host. Inspect the package with
`dpkg-deb --contents dist/*.deb` before release.

## Verify and pin the base

```
python3 scripts/fetch-base.py
cat cache/base/verified.json
```

This verifies SHA256SUMS.gpg with ubuntu-archive-keyring and checks the exact
Ubuntu CD image signing fingerprint, then verifies the ISO SHA256. It records
the authenticated checksum in ignored cache/base/verified.json. Review that
value and add `sha256` to config/base.json. Commit that pin with the release
source. If the candidate point release moved, choose a supported official
Kubuntu LTS image, update its version and URLs together, and repeat verification.
Never substitute a bare checksum obtained from an untrusted mirror.

## Produce the image

```
./scripts/build-iso.sh
(cd dist && sha256sum -c jarvis-os-1.0.0-amd64.iso.sha256)
xorriso -indev dist/jarvis-os-1.0.0-amd64.iso -report_el_torito plain
```

The script verifies the base again, extracts its existing casper root, verifies
the expected Calamares steps, installs the local DEB through signed Ubuntu APT,
adds open-vm-tools-desktop and branding, rebuilds a Zstandard squashfs (supported by the pinned kernel) and initrd, and replays
the base image's boot metadata. It preserves Calamares partition/account/summary
configuration and filesystem.manifest-remove. It has been exercised in an isolated rootless Ubuntu 24.04 build container.
The recipe supports an Ubuntu build VM, but VM execution and VMware installation
are distinct checks and must not be inferred from the container build.

Do not run build-iso as root; only its scoped sudo operations need privilege.
Do not supply block devices. Temporary mounts are under build/iso/root; the
trap unmounts them. If interrupted by a machine crash, inspect `findmnt` and
unmount those paths in reverse order before moving the build directory. Never
blindly delete a directory containing live bind mounts.

Retain signed input manifests, source pins, package and ISO checksums,
build logs and dist/boot-layout.txt with the release. A checksum detects changes;
it does not establish bootability or certify the release. Complete VMware tests.

## Cloud build route used for this artifact

The cloud host is Debian. An isolated Ubuntu 24.04 container was used instead
of claiming it was an Ubuntu VM. The exact container image digest is pinned in
config/builder.json. Rootless Docker with its namespaced privileged mode was
needed for filesystem ownership and temporary /dev, /proc and /sys mounts.
No host disks or block devices were mapped. This is not a VMware test.

The observed setup commands were:

```sh
docker run -d --name jarvis-builder --privileged \
 --mount type=bind,src=/workspace,dst=/workspace \
 --mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/cloud-ca.crt,readonly \
 -e SSL_CERT_FILE=/run/cloud-ca.crt -e PIP_CERT=/run/cloud-ca.crt \
 -e NODE_EXTRA_CA_CERTS=/run/cloud-ca.crt \
 ubuntu@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852 sleep infinity

docker exec jarvis-builder bash -c 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-venv python3-pip gpgv ubuntu-keyring xorriso squashfs-tools rsync sudo ca-certificates curl git build-essential cmake pkg-config espeak-ng alsa-utils qemu-system-x86 ovmf'
```

Use an unused container name; inspect existing containers rather than deleting
someone else's build. The CA mount is test/build-only and is never copied into
the ISO. Prepare source/locks with the scripts above; the pinned Node runtime
is used for npm. The cloud's .venv/bin/uv is a standalone uv executable installed
at version 0.13.5. A clean Ubuntu build VM creates it through setup-build-vm.sh.
The production package's Python environment is freshly built against the
container's /usr/bin/python3.12, not copied from the Debian host.

```sh
docker exec -w /workspace/jarvis-os -e UV_CACHE_DIR=/workspace/.cache/uv jarvis-builder bash scripts/build-package.sh
docker exec -w /workspace/jarvis-os jarvis-builder bash scripts/build-iso.sh
```

Recoverable build findings are incorporated into the scripts: use a recursive
/dev bind so APT's unprivileged verifier sees the real /dev/null; retain proxy
variables through sudo; keep signature verification enabled and fail on update
errors. The base squashfs omits the kernel/initrd from /boot, so the signed
casper kernel is restored and a matching initramfs is generated with live hooks.
Rootless builders preserve original character-device entries through
config/live-devices.pseudo instead of creating host device nodes. The original
Ubuntu squashfs signature is removed after modification because it no longer
signs the remix; Ubuntu package repository signatures remain enabled.

For an interrupted, inspected build only, JARVIS_RESUME_EXTRACT=1 permits reuse
of a tree whose .verified-base marker matches the verified input checksum.
JARVIS_RESUME_CONFIGURE=1 additionally reuses the successful extracted root;
JARVIS_RESUME_INITRD=1 skips package/branding work already checked. Never use
these flags for an unknown or modified build tree. Normal clean builds use none.
Before deleting a build root, verify all nested mounts have been unmounted.

QEMU UEFI smoke test (software CPU emulation; no guest disk attached):

```sh
docker exec -w /workspace/jarvis-os jarvis-builder bash scripts/test-uefi.sh
```

This runs headlessly with a local Unix monitor socket under build/qemu. It does
not replace docs/VMWARE.md. Stop your test with `docker exec -w /workspace/jarvis-os jarvis-builder bash scripts/stop-uefi-test.sh`
before removing its socket or reusing the test directory. The PID guard prevents
concurrent sessions from sharing firmware/monitor files. Standard VGA and a
Nehalem CPU are the default smoke-test devices; set JARVIS_TEST_VGA and
JARVIS_TEST_CPU only for a deliberate alternate hardware test.


Dedicated QEMU installation check (supplemental to VMware):

```sh
docker exec -w /workspace/jarvis-os jarvis-builder bash scripts/test-installation.sh live
# Complete Calamares using only the new /dev/vda test disk, then shut down.
# Once QEMU has exited, stop-uefi-test.sh clears its stale socket/PID.
docker exec -w /workspace/jarvis-os jarvis-builder bash scripts/stop-uefi-test.sh
docker exec -w /workspace/jarvis-os jarvis-builder bash scripts/test-installation.sh installed
```

The first phase refuses existing test-disk/firmware files. It creates a new sparse
40 GiB QCOW2 with QEMU's QMP API and verifies its header; qemu-img is unnecessary.
The second phase attaches the same disk and firmware variables with no ISO.
Never terminate QEMU during installation writes; shut the guest down first.
No physical block devices are passed to either phase.
