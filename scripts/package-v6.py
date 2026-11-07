from pathlib import Path
import gzip
import hashlib
import json
import struct
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
art=root/'artifacts'
shim=(art/'bootshim-v6.Image').read_bytes()
assert shim[56:60]==b'ARM\x64'
assert struct.unpack_from('<Q',shim,8)[0]==0x80000
(art/'bootshim-v6.Image.gz').write_bytes(gzip.compress(shim,compresslevel=9,mtime=0))
cmdline=(root/'config/cmdline.txt').read_text().strip()
subprocess.run([sys.executable,str(root/'tools/mkbootimg.py'),
    '--header_version','2','--pagesize','4096','--base','0',
    '--kernel_offset','0x8000','--ramdisk_offset','0x01000000',
    '--tags_offset','0x100','--second_offset','0','--dtb_offset','0x01f00000',
    '--os_version','11.0.0','--os_patch_level','2023-03',
    '--kernel',str(art/'bootshim-v6.Image.gz'),'--ramdisk',str(art/'initramfs-v6.cpio.gz'),
    '--dtb',str(root/'reports/stock-boot/dtb'),'--cmdline',cmdline,
    '--output',str(art/'boot-linux-test-v6.img')],check=True)
proc=subprocess.run([sys.executable,str(root/'tools/unpack_bootimg.py'),'--boot_img',str(art/'boot-linux-test-v6.img'),'--out',str(root/'reports/v6-unpacked')],check=True,capture_output=True)
(root/'reports/v6-header.txt').write_bytes(proc.stdout)
for name,expected in [('kernel',art/'bootshim-v6.Image.gz'),('ramdisk',art/'initramfs-v6.cpio.gz'),('dtb',root/'reports/stock-boot/dtb')]:
    assert (root/'reports/v6-unpacked'/name).read_bytes()==expected.read_bytes()
assert (art/'boot-linux-test-v6.img').stat().st_size<134217728
manifest={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(art.iterdir()) if p.is_file()}
(root/'reports/artifact-manifest-v6.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(proc.stdout.decode())
