from pathlib import Path
import datetime,gzip,json,subprocess
root=Path(__file__).resolve().parents[1]
key=json.loads((root/'logs/v6-authorized/test-client-identity.json').read_text())['private_key_path']
known=root/'logs/hardware-v6/20261105T193940984/usb/known_hosts'
ssh=['ssh.exe','-i',key,'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','KexAlgorithms=curve25519-sha256','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known),'-o','ConnectTimeout=10','root@192.168.77.2']
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=root/'logs/v7-research'/stamp;out.mkdir(parents=True)
commands={
 'identity':'uname -a; cat /run/init-reached /run/openrc-reached /etc/alpine-release; cat /proc/mounts /proc/swaps; rc-status; cat /proc/uptime',
 'drm-graphics':'ls -l /sys/class/drm /sys/class/graphics /dev/dri; cat /proc/fb; for p in /sys/class/graphics/fb*; do echo "$p"; cat "$p/name" "$p/virtual_size" "$p/bits_per_pixel"; done; for p in /sys/class/drm/card*/device/driver; do readlink "$p"; done',
 'backlight-input':'ls -l /sys/class/backlight /sys/class/input; cat /proc/bus/input/devices; for p in /sys/class/backlight/*; do echo "$p"; cat "$p/type" "$p/max_brightness" "$p/actual_brightness"; done',
 'platform':'ls -l /sys/bus/platform/devices; ls /sys/bus/platform/drivers; for p in /sys/bus/platform/devices/5900000.gpu /sys/bus/platform/devices/596a000.gmu /sys/bus/platform/devices/59a0000.iommu /sys/bus/platform/devices/5e00000.display-subsystem; do echo "$p"; ls -l "$p"; readlink "$p/driver"; cat "$p/uevent"; done',
 'buses':'ls -l /sys/bus/i2c/devices /sys/bus/spi/devices; for p in /sys/bus/i2c/devices/*/name; do echo "$p"; cat "$p"; done',
 'firmware':'ls -l /lib/firmware /usr/lib/firmware; cat /proc/cmdline; cat /sys/firmware/devicetree/base/chosen/xiaomi,bootshim-info',
 'power':'for p in /sys/class/regulator/regulator.*; do echo "$p"; cat "$p/name" "$p/state" "$p/microvolts" "$p/num_users"; done; ls -l /sys/kernel/debug',
 'dmesg':'dmesg',
 'storage':'cat /proc/partitions; for p in /sys/block/sd*; do echo "$p"; cat "$p/stat" "$p/device/ioerr_cnt"; done',
}
results=[]
for name,command in commands.items():
    p=subprocess.run(ssh+[command],capture_output=True,timeout=45)
    (out/(name+'.txt')).write_bytes(p.stdout);(out/(name+'.stderr')).write_bytes(p.stderr)
    results.append({'name':name,'command':command,'last_command_exit':p.returncode})
for name,remote in [('live-v6.dtb','/sys/firmware/fdt'),('live-v6.config.gz','/proc/config.gz')]:
    p=subprocess.run(ssh+['cat '+remote],capture_output=True,timeout=30);p.check_returncode()
    (out/name).write_bytes(p.stdout)
(out/'live-v6.config').write_bytes(gzip.decompress((out/'live-v6.config.gz').read_bytes()))
(out/'commands.json').write_text(json.dumps(results,indent=2)+'\n')
(root/'reports/v7-live-research-location.txt').write_text(str(out)+'\n')
print(out)
