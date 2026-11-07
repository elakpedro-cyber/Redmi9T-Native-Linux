from pathlib import Path
import datetime
import json
import re
import sys
import time
import uuid

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/serial-deps'))
import serial

groups={
    'initial':[
        ('identity','uname -a; cat /run/init-reached; cat /sys/firmware/devicetree/base/chosen/xiaomi,bootshim-info; cat /proc/cmdline; cat /proc/uptime'),
        ('applets','/bin/busybox --list; stty -a'),
        ('storage','cat /proc/partitions; ls -l /sys/block; ls -ld /sys/class/scsi_host; ls -l /sys/bus/platform/devices/4804000.ufshc/driver /sys/bus/platform/devices/4807000.phy/driver; cat /proc/mounts'),
        ('dmesg','dmesg'),
        ('memory','cat /proc/meminfo; cat /proc/iomem'),
    ],
    'hardware':[
        ('drivers','ls /sys/bus/platform/drivers; ls -l /sys/bus/platform/devices/4804000.ufshc; ls -l /sys/bus/platform/devices/4807000.phy'),
        ('ufs-dt','cat /sys/firmware/devicetree/base/soc@0/ufshc@4804000/compatible; cat /sys/firmware/devicetree/base/soc@0/ufshc@4804000/status; cat /sys/firmware/devicetree/base/soc@0/phy@4807000/compatible; cat /sys/firmware/devicetree/base/soc@0/phy@4807000/status; cat /sys/bus/platform/devices/4804000.ufshc/uevent; cat /sys/bus/platform/devices/4807000.phy/uevent'),
        ('deferred','ls -ld /sys/kernel/debug; cat /sys/kernel/debug/devices_deferred; cat /sys/kernel/debug/clk/clk_summary; cat /sys/kernel/debug/regulator/regulator_summary; ls /sys/kernel/debug/phy'),
        ('power','cat /sys/bus/platform/devices/4804000.ufshc/power/runtime_status; cat /sys/bus/platform/devices/4807000.phy/power/runtime_status; ls /sys/class/regulator; ls /sys/class/phy; ls /sys/bus/platform/devices/4804000.ufshc/supplier:*; ls /sys/bus/platform/devices/4807000.phy/supplier:*'),
        ('regulators','for d in /sys/class/regulator/regulator.*; do echo "$d"; cat "$d/name"; cat "$d/state"; cat "$d/microvolts"; cat "$d/num_users"; done'),
        ('config-access','ls -l /proc/config.gz /sys/firmware/fdt; command -v base64; command -v od; command -v hexdump; command -v gzip; command -v zcat; cat /proc/modules'),
    ],
    'verification':[
        ('suppliers','for d in /sys/bus/platform/devices/4804000.ufshc/supplier:* /sys/bus/platform/devices/4807000.phy/supplier:*; do echo "$d"; readlink "$d/supplier"; cat "$d/status"; done; ls -l /sys/bus/platform/devices/1400000.clock-controller/driver /sys/bus/platform/devices/c600000.iommu/driver'),
        ('runtime-proof','uname -r; cat /run/init-reached; cat /sys/firmware/devicetree/base/chosen/xiaomi,bootshim-info; cat /proc/fb; cat /sys/class/graphics/fb0/name; cat /sys/class/graphics/fb0/virtual_size; cat /sys/class/udc/*/state; cat /proc/uptime'),
        ('scsi-symbols','grep -i ufshcd /proc/kallsyms; grep -i qmp_ufs /proc/kallsyms; grep -i scsi_host_alloc /proc/kallsyms'),
    ],
}
group=sys.argv[1] if len(sys.argv)>1 else 'initial'
assert group in groups
logs=root/'logs/v3-live-diagnostics';logs.mkdir(parents=True,exist_ok=True)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
prefix=logs/(stamp+'-'+group)
try:
    port=serial.Serial(port=None,baudrate=115200,timeout=0.2,write_timeout=3,xonxoff=False,rtscts=False,dsrdtr=False)
    port.dtr=True;port.rts=False;port.port='COM3';port.open()
except serial.SerialException as error:
    message={'status':'COM3_UNAVAILABLE','error':str(error),'foreign_processes_terminated':False}
    prefix.with_suffix('.json').write_text(json.dumps(message,indent=2)+'\n')
    print(json.dumps(message));raise SystemExit(3)

results=[]
rawlog=bytearray()
try:
    port.write(b'\n')
    until=time.monotonic()+0.8
    while time.monotonic()<until:rawlog.extend(port.read(65536))
    for name,command in groups[group]:
        token=uuid.uuid4().hex
        begin='__READONLY_BEGIN_'+token+'__'
        end='__READONLY_END_'+token+'__'
        wire=f"printf '\\n{begin}\\n'; {command}; printf '\\n{end}:%s\\n' \"$?\"\n"
        port.write(wire.encode())
        data=bytearray();deadline=time.monotonic()+45
        marker=re.compile(rb'(?m)^'+end.encode()+rb':(\d+)\r?$')
        while time.monotonic()<deadline:
            data.extend(port.read(65536))
            match=marker.search(data)
            if match:break
        else:raise TimeoutError('No completion marker for '+name)
        rawlog.extend(data)
        start=re.search(rb'(?m)^'+begin.encode()+rb'\r?\n',data)
        assert start is not None,name
        output=bytes(data[start.end():match.start()])
        (logs/(stamp+'-'+name+'.txt')).write_bytes(output)
        results.append({'name':name,'command':command,'last_command_exit':int(match[1]),'bytes':len(output),'output_file':stamp+'-'+name+'.txt'})
        print(name+': '+str(len(output))+' bytes',flush=True)
finally:
    port.close()
    prefix.with_suffix('.raw').write_bytes(rawlog)
    prefix.with_suffix('.json').write_text(json.dumps({'port':'COM3','baudrate':115200,'flow_control':'none','read_only_commands':True,'results':results},indent=2)+'\n')
print('Closed COM3; logs:',logs)
