from pathlib import Path
import subprocess
import sys


def test_explicit_live_mode_and_noswap_preserve_menu(tmp_path):
    cfg=tmp_path/'boot/grub/grub.cfg';cfg.parent.mkdir(parents=True)
    cfg.write_text('menuentry "Try Kubuntu" {\n linux /casper/vmlinuz --- quiet splash\n initrd /casper/initrd\n}\ngrub_platform\n')
    tool=Path(__file__).resolve().parents[1]/'scripts/configure-live-boot.py'
    subprocess.run([sys.executable,str(tool),str(tmp_path)],check=True)
    first=cfg.read_text()
    subprocess.run([sys.executable,str(tool),str(tmp_path)],check=True)
    assert first==cfg.read_text()
    assert 'linux /casper/vmlinuz boot=casper noswap --- quiet splash' in first
    assert 'initrd /casper/initrd' in first and 'Try Kubuntu' in first
    assert '\ngrub_platform\n' not in first
