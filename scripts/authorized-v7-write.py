from pathlib import Path
import hashlib,json,subprocess,time
root=Path(__file__).resolve().parents[1]
adb=root.parent/'platform-tools/adb.exe';serial='35a1d5bf0221'
log=root/'logs/v7-authorized';log.mkdir(parents=True,exist_ok=True)
journal=log/'boot-write-journal.json'
assert not journal.exists(),'Write journal already exists; no automatic repeat'
expected='0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746'
image=root/'artifacts/boot-linux-test-v7.img'
assert image.stat().st_size==24428544 and hashlib.sha256(image.read_bytes()).hexdigest()==expected
assert hashlib.sha256((root/'artifacts/boot-linux-test-v6.img').read_bytes()).hexdigest()=='1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63'
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
mounts=shell('cat /proc/mounts')
assert not any(' /data ' in line or ' /cache ' in line or line.startswith('/dev/block/') for line in mounts.splitlines())
assert shell('wc -c < /tmp/boot-linux-test-v7.img').strip()=='24428544'
assert shell('sha256sum /tmp/boot-linux-test-v7.img').split()[0]==expected
assert shell('head -c 23670784 /dev/block/bootdevice/by-name/boot | sha256sum').split()[0]=='1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63'
protected={'recovery':'1737005c5d9452d3238fcd0a2430956e7232937b35e9df427edc114f0dacd2eb','dtbo':'6fd8b752c9a64bc77ccb43a43834b38a2a61e0499c44de01c6d1a349d73ce9a6','vbmeta':'e1bd96f8e0ffe1a71cf41074aa46d3786fda7831b7395efa6205d166b1506ad5'}
for name,digest in protected.items():assert shell('sha256sum /dev/block/bootdevice/by-name/'+name).split()[0]==digest,name
record('preconditions_verified',image_bytes=24428544,sha256=expected)
record('single_boot_write_started')
output=shell('dd if=/tmp/boot-linux-test-v7.img of=/dev/block/bootdevice/by-name/boot bs=4194304 conv=fsync')
record('boot_write_returned_success',output=output)
readback=shell('head -c 24428544 /dev/block/bootdevice/by-name/boot | sha256sum').split()[0]
assert readback==expected,readback
for name,digest in protected.items():assert shell('sha256sum /dev/block/bootdevice/by-name/'+name).split()[0]==digest,name
record('readback_and_protected_hashes_verified',sha256=readback)
print('PASS: single boot write, exact-prefix readback SHA, recovery/dtbo/vbmeta hashes unchanged. No reboot performed by this script.')
