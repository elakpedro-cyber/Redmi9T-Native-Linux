from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parents[1]
out=root/'downloads/v7-personal';out.mkdir(parents=True,exist_ok=True)
path=out/'modem-sde52.img'
assert not path.exists(),'Do not replace firmware readback'
key=json.loads((root/'logs/v6-authorized/test-client-identity.json').read_text())['private_key_path']
ssh=['ssh.exe','-i',key,'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','KexAlgorithms=curve25519-sha256','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(root/'logs/hardware-v6/20261105T193940984/usb/known_hosts'),'root@192.168.77.2']
command='test "$(cat /sys/class/block/sde52/uevent | grep PARTNAME)" = PARTNAME=modem && test "$(cat /sys/class/block/sde52/size)" = 393216 && cat /dev/sde52'
with path.open('wb') as f:p=subprocess.run(ssh+[command],stdout=f,stderr=subprocess.PIPE,timeout=180)
p.check_returncode();assert path.stat().st_size==201326592,path.stat().st_size
(root/'reports/v7-modem-read-provenance.json').write_text(json.dumps({'method':'SSH guarded cat, no device mount or write','partition':'sde52 PARTNAME=modem','bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'purpose':'Extract device-owned GPU firmware locally; not a redistribution licence','excludes':'modemst/persist/calibration partitions not accessed'},indent=2)+'\n')
print('Read-only modem firmware copy complete:',path)
