# JARVIS OS 1.0 — installable-image release candidate

An x86-64 UEFI Kubuntu 24.04 LTS desktop with a separately pinned JARVIS assistant,
CPU voice, and a native offline command center. **An ISO and assistant DEB have been built. Offline installation, disk boot and saved-data persistence passed in QEMU; VMware certification remains pending.** See [observed results](reports/RELEASE.md).

The assistant is pinned to `3a1a06ad6d57d91460665af4a3a9ace816485630` in
[config/assistant.json](config/assistant.json); it is fetched into ignored
`vendor/jarvis`, not copied into this project's source history. A reviewable
[Linux/container portability patch](patches/0001-missing-power-supply.patch)
handles missing battery sysfs. No dependency lockfile changes are required.

- [Build and input verification](docs/BUILD.md)
- [VMware installation and release checklist](docs/VMWARE.md)
- [Desktop, privacy, updates and recovery](docs/DESKTOP.md)
- [CPU voice and missing model input](docs/VOICE.md)
- [Assistant inspection and installer evidence](docs/INSPECTION.md)

For cloud development, run `./scripts/setup-cloud.sh`. For release builds, use a
separate Ubuntu 24.04 VM and follow BUILD.md. A cloud development setup does not
validate boot, installation, guest audio or VMware hardware integration.

Artifacts are in `dist/`: the ISO and SHA-256 file, the assistant DEB and checksum,
and boot-layout evidence. Check reports/RELEASE.md before treating a check as
passed. Use a dedicated blank VMware virtual disk for the installation test.
