#!/bin/bash
# Run only in a disposable Ubuntu 24.04 build VM. Never pass a disk/device path.
set -euo pipefail
umask 022
cd "$(dirname "$0")/.."
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo 'Ubuntu 24.04 build VM required'; exit 1; }
[[ $(id -u) != 0 || -f /.dockerenv ]] || { echo 'Run as your ordinary build user; sudo is scoped to chroot/image operations'; exit 1; }
python3 - <<'PY'
import json
p=json.load(open('config/base.json'))
assert len(p.get('sha256',''))==64, 'Release requires a reviewed SHA256 in config/base.json. Run fetch-base.py first.'
PY
base=$(python3 scripts/fetch-base.py)
pkg="$PWD/dist/jarvis-os-desktop_1.0.0_amd64.deb"
[[ -f "$pkg" ]] || { echo 'Build the assistant package first'; exit 1; }
work="$PWD/build/iso"
if [[ -e "$work" ]]; then
 [[ ${JARVIS_RESUME_EXTRACT:-0} == 1 && -f "$work/.verified-base" ]] || { echo 'Existing build directory: explicit verified extraction resume required'; exit 1; }
 expected=$(python3 -c 'import json; print(json.load(open("config/base.json"))["sha256"])')
 [[ $(cat "$work/.verified-base") == "$expected" ]] || exit 1
else
 mkdir -p "$work/tree" dist
 xorriso -osirrox on -indev "$base" -extract / "$work/tree"
 python3 -c 'import json; print(json.load(open("config/base.json"))["sha256"])' > "$work/.verified-base"
fi
if [[ ${JARVIS_RESUME_CONFIGURE:-0} != 1 ]]; then
[[ -f "$work/tree/casper/filesystem.squashfs" ]] || { echo 'Unsupported casper layout: inspect the new base before adapting'; exit 1; }
# Exactly one root filesystem is supported; do not accidentally customize an unused layer.
[[ $(find "$work/tree/casper" -maxdepth 1 -name '*.squashfs' | wc -l) == 1 ]] || { echo 'Layered image requires explicit review'; exit 1; }
fi
# Rootless builders cannot mknod. Preserve these base device entries as squashfs
# pseudo metadata, not host devices; all other extraction errors remain fatal.
mapfile -t device_paths < <(cut -d' ' -f1 config/live-devices.pseudo)
if [[ ${JARVIS_RESUME_CONFIGURE:-0} == 1 ]]; then
 [[ -f "$work/.root-extracted" && $(cat "$work/.root-extracted") == $(cat "$work/.verified-base") ]] || exit 1
else
 sudo unsquashfs -f -excludes -d "$work/root" "$work/tree/casper/filesystem.squashfs" "${device_paths[@]}"
 cp "$work/.verified-base" "$work/.root-extracted"
fi
root="$work/root"
inroot() {
 sudo --preserve-env=http_proxy,https_proxy,HTTP_PROXY,HTTPS_PROXY,NO_PROXY,no_proxy chroot "$root" "$@"
}
[[ -f "$root/etc/calamares/settings.conf" ]] || { echo 'Kubuntu Calamares missing'; exit 1; }
for module in welcome locale keyboard partition users summary; do
 sudo grep -q -- "- $module" "$root/etc/calamares/settings.conf" || { echo "Missing installer step $module"; exit 1; }
done
sudo grep -q '/cdrom/casper/filesystem.squashfs' "$root/etc/calamares/modules/unpackfs.conf"
# Preserve the installer and all disk-confirmation/account/locale modules verbatim.
sudo cp "$pkg" "$root/tmp/jarvis.deb"
cleanup() {
 for point in proc sys; do
  if mountpoint -q "$root/$point"; then sudo umount "$root/$point"; fi
 done
 if mountpoint -q "$root/dev"; then sudo umount --recursive "$root/dev"; fi
}
trap cleanup EXIT
sudo mount -t proc proc "$root/proc"
sudo mount --rbind /dev "$root/dev"
sudo mount -t sysfs sys "$root/sys"
# Preserve base signed APT sources; no external PPAs, insecure flags or keys.
if [[ ${JARVIS_RESUME_INITRD:-0} != 1 ]]; then
inroot apt-get -o APT::Update::Error-Mode=any update
inroot env DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/jarvis.deb open-vm-tools-desktop
sudo rm "$root/tmp/jarvis.deb"
sudo mkdir -p "$root/usr/share/jarvis-os" "$root/etc/xdg" "$root/usr/share/polkit-1/rules.d"
sudo install -m644 packaging/branding/jarvis.svg "$root/usr/share/jarvis-os/wallpaper.svg"
sudo install -m644 packaging/branding/kdeglobals "$root/etc/xdg/kdeglobals"
sudo install -m644 packaging/branding/device_automounter_kcmrc "$root/etc/xdg/device_automounter_kcmrc"
sudo install -m755 packaging/jarvis-live-policy "$root/usr/bin/"
sudo install -m644 packaging/49-jarvis-live.rules "$root/usr/share/polkit-1/rules.d/"
# Use Breeze's maintained login UI with a branded background, not a fork of authentication code.
sudo mkdir -p "$root/etc/sddm.conf.d" "$root/usr/share/sddm/themes/breeze"
printf '[Theme]\nCurrent=breeze\n' | sudo tee "$root/etc/sddm.conf.d/zz-jarvis.conf" >/dev/null
printf '[General]\nbackground=/usr/share/jarvis-os/wallpaper.svg\n' | sudo tee "$root/usr/share/sddm/themes/breeze/theme.conf.user" >/dev/null
sudo mkdir -p "$root/usr/share/plymouth/themes/jarvis"
sudo install -m644 packaging/branding/jarvis.plymouth packaging/branding/jarvis.script "$root/usr/share/plymouth/themes/jarvis/"
inroot update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth /usr/share/plymouth/themes/jarvis/jarvis.plymouth 150
inroot update-alternatives --set default.plymouth /usr/share/plymouth/themes/jarvis/jarvis.plymouth
fi
sudo rm -f "$root/tmp/jarvis.deb"
# Kubuntu's squashfs deliberately omits kernel/initrd payloads kept in casper.
# Restore the original signed kernel and generate a live initramfs with casper hooks.
mapfile -t kernels < <(find "$root/usr/lib/modules" -mindepth 1 -maxdepth 1 -type d -printf '%f\n')
[[ ${#kernels[@]} == 1 ]] || { echo 'Ambiguous kernel/module layout'; exit 1; }
kernel_version=${kernels[0]}
sudo cp "$work/tree/casper/vmlinuz" "$root/boot/vmlinuz-$kernel_version"
if [[ -f "$root/boot/initrd.img-$kernel_version" ]]; then
 inroot update-initramfs -u -k "$kernel_version"
else
 inroot update-initramfs -c -k "$kernel_version"
fi
# Reuse the base kernel but include our splash in the live initrd too.
initrd=$(find "$root/boot" -maxdepth 1 -name 'initrd.img-*' | sort -V | tail -1)
[[ -n "$initrd" ]] || exit 1
sudo cp "$initrd" "$work/tree/casper/initrd"
inroot apt-get clean
sudo rm -f "$root/etc/machine-id" "$root/var/lib/dbus/machine-id"
sudo touch "$root/etc/machine-id"
sudo chmod 644 "$root/etc/machine-id"
sudo find "$root/var/log" -type f -exec truncate -s 0 {} +
inroot dpkg-query -W --showformat='${Package} ${Version}\n' > "$work/tree/casper/filesystem.manifest"
# Preserve filesystem.manifest-remove: it defines live-only packages removed by installer.
cleanup
trap - EXIT
sudo rm -f "$work/tree/casper/filesystem.squashfs"
# A remixed squashfs cannot retain Ubuntu's original detached signature.
sudo rm -f "$work/tree/casper/filesystem.squashfs.gpg"
sudo mksquashfs "$root" "$work/tree/casper/filesystem.squashfs" -noappend -comp zstd -Xcompression-level 8 -processors 2 -pf config/live-devices.pseudo
sudo du -sx --block-size=1 "$root" | cut -f1 > "$work/tree/casper/filesystem.size"
# Disable live swap activation; prevent desktop automount via the live-only polkit rule.
python3 scripts/configure-live-boot.py "$work/tree"

(cd "$work/tree" && find . -type f ! -name md5sum.txt ! -path './boot/grub/*' -print0 | sort -z | xargs -0 md5sum) > "$work/md5sum.txt"
cp "$work/md5sum.txt" "$work/tree/md5sum.txt"
out="$PWD/dist/jarvis-os-1.0.0-amd64.iso"
python3 scripts/assemble-iso.py
xorriso -indev "$out" -report_el_torito plain > dist/boot-layout.txt 2>&1
(cd dist && sha256sum jarvis-os-1.0.0-amd64.iso > jarvis-os-1.0.0-amd64.iso.sha256)
echo 'ISO built. Do not release before completing docs/VMWARE.md and reports/RELEASE.md.'
