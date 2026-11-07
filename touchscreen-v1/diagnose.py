"""Read-only inventory. Never opens event nodes, SPI/I2C devices or debugfs controls."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import argparse,importlib.util,json
r=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--known-hosts',type=Path,required=True)
a=p.parse_args()
spec=importlib.util.spec_from_file_location('control',r/'userspace/gnome-physical-v2.1/control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
s=m.Session(SimpleNamespace(known_hosts=str(a.known_hosts)))
out=r/'logs/touchscreen-v1'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
commands={
'identity':'uname -a; cat /sys/class/tty/tty0/active /proc/uptime; cat /proc/sys/kernel/random/boot_id',
'input':'cat /proc/bus/input/devices; ls -l /sys/class/input /dev/input; for p in /sys/class/input/event*; do echo EVENT=$p; cat "$p/device/name" "$p/device/phys" "$p/device/properties" "$p/device/capabilities/ev" "$p/device/capabilities/abs"; readlink -f "$p/device"; done',
'buses':'ls -l /sys/bus/spi/devices /sys/class/spi_master; ls -l /sys/bus/spi/drivers; lsmod; cat /proc/interrupts',
'device-tree':'find /sys/firmware/devicetree/base -name "*spi*" -o -name "*qup*" -o -name "*novatek*"; for p in /proc/device-tree/aliases/spi*; do [ ! -f "$p" ] || { echo ALIAS=$p; cat "$p"; echo; }; done',
'dt-status':'for p in $(find /sys/firmware/devicetree/base -name "spi@4a88000" -o -name "i2c@4a88000" -o -name "geniqup@4ac0000"); do echo NODE=$p; for n in status compatible reg pinctrl-0; do if [ -f "$p/$n" ]; then echo PROPERTY=$n; od -An -tx1 "$p/$n"; fi; done; done',
'safety':'cat /proc/mounts /proc/swaps; for p in /sys/block/sd?; do echo DISK=$p; cat "$p/stat"; done; cat /sys/bus/platform/devices/5e00000.display-subsystem/driver_override; cat /sys/bus/platform/devices/5900000.gpu/power/runtime_status',
'dmesg':'dmesg'}
for name,command in commands.items():
 data=s.remote(command,timeout=15);(out/(name+'.txt')).write_bytes(data);print(name,len(data))
(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
(r/'logs/touchscreen-v1/latest-diagnostic.txt').write_text(str(out),encoding='utf-8')
print('READ_ONLY_COMPLETE',out)
