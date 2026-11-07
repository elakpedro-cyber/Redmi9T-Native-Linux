from pathlib import Path
import gzip
import hashlib
import json
import stat
import struct
import subprocess

root = Path(__file__).resolve().parents[1]
lines = []

def check(condition, description):
    assert condition, description
    lines.append('PASS: ' + description)

before = json.loads((root / 'reports/backup-sha256-before.json').read_text())
after = {}
for name, expected in before.items():
    path = root.parent / 'platform-tools/Redmi9T_Backup' / name
    after[name] = {'size': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    check(after[name] == expected, name + ' backup unchanged')
(root / 'reports/backup-sha256-after.json').write_text(json.dumps(after, indent=2) + '\n')

blob = gzip.decompress((root / 'artifacts/initramfs.cpio.gz').read_bytes())
offset = 0
entries = {}
while blob[offset:offset+6] == b'070701':
    fields = [int(blob[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
    mode, uid, gid, size, rmajor, rminor, namesize = fields[1],fields[2],fields[3],fields[6],fields[9],fields[10],fields[11]
    start = offset + 110
    name = blob[start:start+namesize-1].decode()
    start = (start+namesize+3)&~3
    data = blob[start:start+size]
    if name == 'TRAILER!!!':
        break
    entries[name.removeprefix('./')] = (mode,uid,gid,rmajor,rminor,data)
    offset = (start+size+3)&~3
check('init' in entries and entries['init'][0] & 0o111, 'executable /init in newc archive')
check(entries['init'][5] == (root/'config/init').read_bytes(), 'packaged /init matches source')
check(stat.S_ISCHR(entries['dev/console'][0]) and entries['dev/console'][3:5] == (5,1), '/dev/console is character device 5:1')
for name in ['sh','mount','mkdir','ls','head','sleep','getty','setsid','uname','dmesg']:
    entry=entries['bin/'+name]
    check(stat.S_ISLNK(entry[0]) and entry[5] == b'busybox', '/bin/'+name+' resolves to BusyBox')
check(all(entry[1:3] == (0,0) for entry in entries.values()), 'cpio files owned by root')
(root/'reports/initramfs-files.txt').write_text('\n'.join(sorted(entries))+'\n')

binary = Path.home()/'Redmi9T-Native-Linux/initramfs/bin/busybox'
elf = binary.read_bytes()
check(elf[:5] == b'\x7fELF\x02' and struct.unpack_from('<H',elf,18)[0] == 183, 'BusyBox ELF64 AArch64')
headers = subprocess.check_output(['aarch64-linux-gnu-readelf','-l',str(binary)],text=True)
check('INTERP' not in headers and 'DYNAMIC' not in headers, 'BusyBox has no dynamic interpreter or dynamic segment')
result=subprocess.check_output(['qemu-aarch64-static',str(binary),'uname','-m'],text=True).strip()
check(result=='aarch64', 'BusyBox runs under qemu-user as AArch64')
result=subprocess.run(['qemu-aarch64-static',str(binary),'sh','-n',str(root/'config/init')])
check(result.returncode==0, 'init parses with the actual BusyBox ash')

config=set((root/'config/linux.config').read_text().splitlines())
fragment=(root/'config/bringup.fragment').read_text().splitlines()
check(all(line in config for line in fragment if line.endswith('=y')), 'all requested built-in kernel features enabled')
for key in ['MODULES','SCSI','MMC','NET','QCOM_Q6V5_MSS','QCOM_Q6V5_PAS']:
    check('CONFIG_'+key+'=y' not in config, key+' disabled')
dtbo=json.loads((root/'reports/dtbo-compatibility.json').read_text())
check(dtbo['stock_overlay_0']['returncode']==0, 'stock DTBO control test succeeds on stock DTB')
lines.append('BLOCKER: vendor overlay #0 fails on mainline DTB: FDT_ERR_NOTFOUND')
abl=json.loads((root/'reports/abl-analysis.json').read_text())
lines.append('BLOCKER: boot absent from recovered ABL fastboot command table; protocol untested')
lines.append('NOT TESTED: phone boot, physical load placement, framebuffer, USB ACM, AVB acceptance')
text='\n'.join(lines)+'\n'
(root/'reports/final-checks.txt').write_text(text)
print(text)
