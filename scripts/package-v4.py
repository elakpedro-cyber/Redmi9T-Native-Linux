from pathlib import Path
import gzip
import hashlib
import json
import struct
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
art=root/'artifacts'
# Preserve original newc metadata, including /dev/console; replace userspace.
old=gzip.decompress((art/'initramfs.cpio.gz').read_bytes())
out=bytearray();offset=0;entries=[];names=set()
while old[offset:offset+6]==b'070701':
    fields=[int(old[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
    size,namesize=fields[6],fields[11];start=offset+110
    name=old[start:start+namesize].rstrip(b'\0').decode().removeprefix('./')
    start=(start+namesize+3)&~3;payload=old[start:start+size]
    offset=(start+size+3)&~3
    if name=='TRAILER!!!':break
    if name=='init':payload=(root/'config/init-v4').read_bytes()
    if name=='bin/busybox':payload=(art/'BusyBox-v4').read_bytes()
    fields[6]=len(payload);entries.append((name,fields,payload));names.add(name)
def add(name,mode,payload):
    assert name not in names,name
    fields=[len(entries)+1000,mode,0,0,1,0,len(payload),0,0,0,0,0,0]
    entries.append((name,fields,payload));names.add(name)
for app in (root/'reports/busybox-v4-applets.txt').read_text().splitlines():
    if app!='busybox' and 'bin/'+app not in names:add('bin/'+app,0o120777,b'busybox')
add('sbin/ufs-diagnostics',0o100755,(root/'config/ufs-diagnostics-v4').read_bytes())
add('TRAILER!!!',0,b'')
for name,fields,payload in entries:
    name=name.encode()+b'\0';fields[11]=len(name)
    out+=b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)+name
    out+=bytes((-len(out))%4);out+=payload;out+=bytes((-len(out))%4)
out+=bytes((-len(out))%512)
(art/'initramfs-v4.cpio.gz').write_bytes(gzip.compress(bytes(out),compresslevel=9,mtime=0))
shim=(art/'bootshim-v4.Image').read_bytes()
assert shim[56:60]==b'ARM\x64'
assert struct.unpack_from('<Q',shim,8)[0]==0x80000
(art/'bootshim-v4.Image.gz').write_bytes(gzip.compress(shim,compresslevel=9,mtime=0))
cmdline=(root/'config/cmdline.txt').read_text().strip()
subprocess.run([sys.executable,str(root/'tools/mkbootimg.py'),
    '--header_version','2','--pagesize','4096','--base','0',
    '--kernel_offset','0x8000','--ramdisk_offset','0x01000000',
    '--tags_offset','0x100','--second_offset','0','--dtb_offset','0x01f00000',
    '--os_version','11.0.0','--os_patch_level','2023-03',
    '--kernel',str(art/'bootshim-v4.Image.gz'),'--ramdisk',str(art/'initramfs-v4.cpio.gz'),
    '--dtb',str(root/'reports/stock-boot/dtb'),'--cmdline',cmdline,
    '--output',str(art/'boot-linux-test-v4.img')],check=True)
proc=subprocess.run([sys.executable,str(root/'tools/unpack_bootimg.py'),'--boot_img',str(art/'boot-linux-test-v4.img'),'--out',str(root/'reports/v4-unpacked')],check=True,capture_output=True)
(root/'reports/v4-header.txt').write_bytes(proc.stdout)
for name,expected in [('kernel',art/'bootshim-v4.Image.gz'),('ramdisk',art/'initramfs-v4.cpio.gz'),('dtb',root/'reports/stock-boot/dtb')]:
    assert (root/'reports/v4-unpacked'/name).read_bytes()==expected.read_bytes()
assert (art/'boot-linux-test-v4.img').stat().st_size<134217728
manifest={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(art.iterdir()) if p.is_file()}
(root/'reports/artifact-manifest-v4.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(proc.stdout.decode())
