from pathlib import Path
import base64,datetime,hashlib,json,re,shlex,subprocess,sys,time,uuid
root=Path(__file__).resolve().parents[1];logs=root/'logs/v7-authorized';logs.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'tools/serial-deps'))
import serial
latest=max((root/'logs/first-test-v6').glob('*-network-ssh.txt'),key=lambda p:p.stat().st_mtime)
keys=set(re.findall(r'(?m)^ssh-ed25519 ([A-Za-z0-9+/=]+)[^\r\n]*',latest.read_text(errors='replace')))
assert len(keys)==1
host=keys.pop();fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(host)).digest()).decode().rstrip('=')
(logs/'v6-host.pub').write_text('ssh-ed25519 '+host+'\n')
(logs/'v6-known_hosts').write_text('192.168.77.2 ssh-ed25519 '+host+'\n')
(logs/'v6-host-pin.json').write_text(json.dumps({'source':'trusted COM4 '+str(latest),'fingerprint':fingerprint},indent=2)+'\n')
identity=json.loads((root/'logs/v6-authorized/test-client-identity.json').read_text())['private_key_path']
public=Path(identity+'.pub').read_text().strip();assert public in (root/'config/ssh-authorized-keys-v7').read_text()
token=uuid.uuid4().hex;end='__V7_ACCESS_END_'+token
cmd='test "$(cat /run/init-reached)" = LEMON_INIT_V6_REACHED && test "$(/bin/busybox awk \'$2 == "/" {print $3}\' /proc/mounts)" = rootfs && test ! -L /root/.ssh/authorized_keys && { grep -Fqx '+shlex.quote(public)+' /root/.ssh/authorized_keys || printf \'%s\\n\' '+shlex.quote(public)+' >> /root/.ssh/authorized_keys; } && chmod 600 /root/.ssh/authorized_keys'
wire=cmd+f'; printf "\\n{end}:%s\\n" "$?"\n'
raw=bytearray()
with serial.Serial('COM4',115200,timeout=.2,write_timeout=3,rtscts=False,dsrdtr=False) as port:
    port.write(b'\n');time.sleep(.3);raw.extend(port.read(65536));port.write(wire.encode())
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        raw.extend(port.read(65536));match=re.search(rb'(?m)^'+end.encode()+rb':(\d+)\r?$',raw)
        if match:break
    else:raise TimeoutError('No serial completion marker')
(logs/'v6-ram-key-access.raw').write_bytes(raw);assert int(match[1])==0
ssh=['ssh.exe','-i',identity,'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','KexAlgorithms=curve25519-sha256','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(logs/'v6-known_hosts'),'root@192.168.77.2']
commands={
 'identity':'uname -a; cat /run/init-reached /run/openrc-reached /etc/alpine-release; apk --version; rc-status; cat /proc/uptime',
 'storage':'cat /proc/mounts /proc/swaps /proc/partitions; for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt"; done',
 'dmesg':'dmesg',
 'thermal-power':'for p in /sys/class/thermal/thermal_zone*; do echo "$p"; cat "$p/type" "$p/temp"; done; for p in /sys/class/power_supply/*; do echo "$p"; cat "$p/uevent"; done',
}
for name,command in commands.items():
    p=subprocess.run(ssh+[command],capture_output=True,timeout=20)
    (logs/('v6-ssh-'+name+'.txt')).write_bytes(p.stdout);(logs/('v6-ssh-'+name+'.stderr')).write_bytes(p.stderr)
    if name=='identity':assert p.returncode==0 and b'LEMON_INIT_V6_REACHED' in p.stdout,p.stderr
for name,remote in [('v6-live.dtb','/sys/firmware/fdt'),('v6-config.gz','/proc/config.gz')]:
    p=subprocess.run(ssh+['cat '+remote],capture_output=True,timeout=20);p.check_returncode();(logs/name).write_bytes(p.stdout)
print('PASS: v6 COM-pinned key-only SSH restored; fresh logs/config/DT saved. Public test key only added in RAM.')
