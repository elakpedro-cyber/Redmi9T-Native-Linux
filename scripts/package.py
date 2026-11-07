import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
art = root / 'artifacts'

def run(*args):
    result = subprocess.run([str(a) for a in args], capture_output=True, check=True)
    return result.stdout

# Preserve the upstream DTB. Only the bootloader-facing copy carries board IDs
# read from this phone and forces device mode for the serial-only experiment.
upstream = art / 'sm6115-xiaomi-lemon.dtb'
bootdtb = art / 'sm6115-xiaomi-lemon-boot.dtb'
bootdtb.write_bytes(upstream.read_bytes())
live = root / 'reports/live.dtb'
for prop in ['qcom,msm-id', 'qcom,board-id']:
    values = run('fdtget', '-t', 'x', live, '/', prop).decode().split()
    run('fdtput', '-t', 'x', bootdtb, '/', prop, *values)
usb = '/soc@0/usb@4ef8800/usb@4e00000'
# Resolve from the compiled tree instead of assuming whether the soc has @0.
tree = run('dtc', '-I', 'dtb', '-O', 'dts', bootdtb).decode()
soc = '/soc@0' if '\tsoc@0 {' in tree else '/soc'
usb = soc + '/usb@4ef8800/usb@4e00000'
run('fdtput', '-t', 's', bootdtb, usb, 'dr_mode', 'peripheral')
props = run('fdtget', '-p', bootdtb, usb).decode().splitlines()
if 'usb-role-switch' in props:
    run('fdtput', '-d', bootdtb, usb, 'usb-role-switch')
(root / 'reports/lemon-boot.dts').write_bytes(run('dtc', '-I', 'dtb', '-O', 'dts', bootdtb))

cmdline = 'rdinit=/init console=tty0 loglevel=8 ignore_loglevel printk.time=1 keep_bootcon clk_ignore_unused pd_ignore_unused panic=0'
(root / 'config/cmdline.txt').write_text(cmdline + '\n')
run(sys.executable, root / 'tools/mkbootimg.py',
    '--header_version', '2', '--pagesize', '4096', '--base', '0',
    '--kernel_offset', '0x8000', '--ramdisk_offset', '0x01000000',
    '--second_offset', '0', '--tags_offset', '0x100', '--dtb_offset', '0x01f00000',
    '--os_version', '11.0.0', '--os_patch_level', '2023-03',
    '--kernel', art / 'Image.gz', '--ramdisk', art / 'initramfs.cpio.gz',
    '--dtb', bootdtb, '--cmdline', cmdline, '--output', art / 'boot-linux-test.img')
unpack = root / 'reports/test-unpacked'
header = run(sys.executable, root / 'tools/unpack_bootimg.py', '--boot_img', art / 'boot-linux-test.img', '--out', unpack)
(root / 'reports/test-header.txt').write_bytes(header)
for extracted, original in [('kernel','Image.gz'), ('ramdisk','initramfs.cpio.gz'), ('dtb','sm6115-xiaomi-lemon-boot.dtb')]:
    assert (unpack / extracted).read_bytes() == (art / original).read_bytes(), extracted
image = (art / 'Image').read_bytes()
assert image[56:60] == b'ARM\x64'
assert gzip.decompress((art / 'Image.gz').read_bytes()) == image
assert gzip.decompress((art / 'initramfs.cpio.gz').read_bytes())[:6] == b'070701'
assert (art / 'boot-linux-test.img').stat().st_size < 128 * 1024 * 1024
report = {
    'status': 'STRUCTURE_VALIDATED_HARDWARE_COMPATIBILITY_UNRESOLVED',
    'kernel_commit': '05441d697f7f9a927264f4058cbbc6a03dfcac9d',
    'arm64_text_offset': hex(struct.unpack_from('<Q', image, 8)[0]),
    'arm64_image_size': struct.unpack_from('<Q', image, 16)[0],
    'header_roundtrip_payloads': 'identical',
    'fastboot_boot': 'boot absent from recovered ABL command table; runtime untested',
    'usb_acm': 'configured, not verified on hardware',
    'usb_network': 'not configured or claimed',
    'stock_dtbo_compatibility': 'not established; do not erase dtbo',
    'avb': 'no AVB changes, footer, bypass or signing added',
}
(root / 'reports/offline-validation.json').write_text(json.dumps(report, indent=2) + '\n')
manifest = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(art.iterdir()) if p.is_file()}
(root / 'reports/artifact-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(header.decode())
print(json.dumps(report, indent=2))
