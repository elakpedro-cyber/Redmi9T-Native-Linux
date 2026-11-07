from pathlib import Path
import hashlib,json,subprocess,time
root=Path(__file__).resolve().parents[1]
adb=root.parent/'platform-tools/adb.exe';serial='35a1d5bf0221'
log=root/'logs/v8-authorized';log.mkdir(parents=True,exist_ok=True)
journal=log/'boot-write-journal.json'
assert not journal.exists(),'Write journal already exists; no automatic repeat'
expected='563296819c9e22da2ffcc38918b0761ca3d18eed7ae181123796fd6fb1033a29'
image=root/'artifacts/boot-linux-test-v8.img'
assert image.stat().st_size==24698880 and hashlib.sha256(image.read_bytes()).hexdigest()==expected
assert hashlib.sha256((root/'snapshots/v7-hardware-validated/artifacts/boot-linux-test-v7.img').read_bytes()).hexdigest()=='0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746'
events=[]
def record(stage,**data):
    events.append({'stage':stage,'time_unix':time.time(),**data});journal.write_text(json.dumps(events,indent=2)+'\n')
def shell(command):
    p=subprocess.run([str(adb),'-s',serial,'shell',command],capture_output=True,timeout=90)
    output=p.stdout.decode(errors='replace').strip()
    (log/'adb-write-commands.txt').open('a').write(command+'\n'+output+'\n'+p.stderr.decode(errors='replace')+'\n')
    assert p.returncode==0,(command,p.returncode,output,p.stderr)
    return output
assert 'uid=0(root)' in shell('id')
assert shell('getprop ro.product.device')=='lemon'
assert shell('uname -r').startswith('4.19.252')
assert shell('readlink -f /dev/block/bootdevice/by-name/boot')=='/dev/block/sde49'
assert shell('readlink -f /dev/block/bootdevice/by-name/recovery')=='/dev/block/sda9'
assert shell('blockdev --getsize64 /dev/block/bootdevice/by-name/boot')=='134217728'
initial_mounts=shell('cat /proc/mounts')
for mount in ('/data','/cache'):
    if any(line.split()[1]==mount for line in initial_mounts.splitlines()):
        shell('umount '+mount)
mounts=shell('cat /proc/mounts')
assert any(line.split()[1:3]==['/tmp','tmpfs'] for line in mounts.splitlines())
subprocess.run([str(adb),'-s',serial,'pull','/sys/fs/pstore',str(log/'pstore-before')],timeout=20,check=False)
(log/'twrp-dmesg-before.txt').write_text(shell('dmesg'),encoding='utf-8')
assert not any(' /data ' in line or ' /cache ' in line or line.startswith('/dev/block/') for line in mounts.splitlines())
subprocess.run([str(adb),'-s',serial,'push',str(image),'/tmp/boot-linux-test-v8.img'],timeout=40,check=True)
assert shell('wc -c < /tmp/boot-linux-test-v8.img').strip()=='24698880'
assert shell('sha256sum /tmp/boot-linux-test-v8.img').split()[0]==expected
assert shell('head -c 24428544 /dev/block/bootdevice/by-name/boot | sha256sum').split()[0]=='0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746'
protected={'recovery':'1737005c5d9452d3238fcd0a2430956e7232937b35e9df427edc114f0dacd2eb','dtbo':'6fd8b752c9a64bc77ccb43a43834b38a2a61e0499c44de01c6d1a349d73ce9a6','vbmeta':'e1bd96f8e0ffe1a71cf41074aa46d3786fda7831b7395efa6205d166b1506ad5'}
for name,digest in protected.items():assert shell('sha256sum /dev/block/bootdevice/by-name/'+name).split()[0]==digest,name
assert not any(line.split()[1] in ('/data','/cache') or line.startswith('/dev/block/') for line in shell('cat /proc/mounts').splitlines())
record('preconditions_verified',image_bytes=24698880,sha256=expected)
record('single_boot_write_started')
output=shell('dd if=/tmp/boot-linux-test-v8.img of=/dev/block/bootdevice/by-name/boot bs=4194304 conv=fsync')
record('boot_write_returned_success',output=output)
readback=shell('head -c 24698880 /dev/block/bootdevice/by-name/boot | sha256sum').split()[0]
assert readback==expected,readback
for name,digest in protected.items():assert shell('sha256sum /dev/block/bootdevice/by-name/'+name).split()[0]==digest,name
record('readback_and_protected_hashes_verified',sha256=readback)
print('PASS: single boot write, exact-prefix readback SHA, recovery/dtbo/vbmeta hashes unchanged. No reboot performed by this script.')
