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

groups={'audit':[
('identity','uname -a; cat /run/init-reached; cat /sys/firmware/devicetree/base/chosen/xiaomi,bootshim-info; cat /proc/uptime; cat /proc/mounts'),
('storage','cat /proc/partitions; ls -l /sys/class/scsi_host /sys/class/scsi_disk; readlink /sys/bus/platform/devices/4804000.ufshc/driver; readlink /sys/bus/platform/devices/4807000.phy/driver; for d in /sys/block/sd*; do echo "$d"; cat "$d/device/vendor" "$d/device/model" "$d/device/rev" "$d/size" "$d/queue/logical_block_size" "$d/queue/physical_block_size" "$d/ro" "$d/stat" "$d/device/ioerr_cnt" "$d/device/state"; done'),
('dmesg-before','dmesg'),
('graphics-input','cat /proc/fb; ls -l /dev/dri /sys/class/drm; cat /proc/bus/input/devices; ls -l /sys/class/input; for p in /sys/firmware/devicetree/base/soc@0/gpu@5000000 /sys/firmware/devicetree/base/soc@0/display-subsystem@5e00000; do echo "$p"; cat "$p/compatible" "$p/status"; done'),
('reads-a','for d in sda sdb sdc sdd sde sdf; do echo "BEGIN_READ_$d"; head -c 16384 /dev/$d | base64; echo "END_READ_$d"; done'),
('interval','sleep 20; cat /proc/uptime'),
('reads-b','for d in sda sdb sdc sdd sde sdf; do echo "BEGIN_READ_$d"; head -c 16384 /dev/$d | base64; echo "END_READ_$d"; done'),
('storage-after','for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt" "$d/device/state"; done; dmesg'),
]}
groups['bounded-reads']=[
    ('counters-before','for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt" "$d/device/iorequest_cnt" "$d/device/iodone_cnt"; done'),
    ('hex-a','for d in sda sdb sdc sdd sde sdf; do echo "BEGIN_READ_$d"; hexdump -v -n 16384 /dev/$d; echo "END_READ_$d"; done'),
    ('interval','sleep 20; cat /proc/uptime'),
    ('hex-b','for d in sda sdb sdc sdd sde sdf; do echo "BEGIN_READ_$d"; hexdump -v -n 16384 /dev/$d; echo "END_READ_$d"; done'),
    ('counters-after','for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt" "$d/device/iorequest_cnt" "$d/device/iodone_cnt"; done; dmesg'),
]
groups['fdt']=[('live-fdt-base64','base64 /sys/firmware/fdt')]
groups['config']=[('live-config-base64','base64 /proc/config.gz'),('gpu-driver','ls -l /sys/bus/platform/devices/5900000.gpu/driver; cat /sys/firmware/devicetree/base/soc@0/gpu@5900000/compatible; cat /sys/firmware/devicetree/base/soc@0/gpu@5900000/status; cat /proc/uptime')]
group=sys.argv[1] if len(sys.argv)>1 else 'audit'
assert group in groups
logs=root/'logs/v4-live-diagnostics';logs.mkdir(parents=True,exist_ok=True)
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
