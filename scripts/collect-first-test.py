from pathlib import Path
import argparse,datetime,json,re,sys,time,uuid
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/serial-deps'))
import serial
from serial.tools import list_ports

parser=argparse.ArgumentParser(description='Read-only v4/v5 serial diagnostics; never reboots or writes block devices')
parser.add_argument('--expect',choices=['v4','v5'],required=True)
parser.add_argument('--port',default='COM3')
parser.add_argument('--wait',type=int,default=0,help='Wait for absent port, in seconds; busy ports fail immediately')
args=parser.parse_args()
logs=root/'logs'/('first-test-'+args.expect)
logs.mkdir(parents=True,exist_ok=True)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
prefix=logs/stamp
commands=[
('identity','uname -a; cat /run/init-reached; cat /sys/firmware/devicetree/base/chosen/xiaomi,bootshim-info; cat /proc/uptime'),
('mounts-swaps','cat /proc/mounts; cat /proc/swaps; cat /proc/cmdline'),
('ufs-before','for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt" "$d/device/state" "$d/queue/logical_block_size"; done; cat /proc/partitions'),
('drivers','ls -l /sys/class/scsi_host /sys/class/scsi_disk; readlink /sys/bus/platform/devices/4804000.ufshc/driver; readlink /sys/bus/platform/devices/4807000.phy/driver; cat /proc/fb; cat /sys/class/udc/*/state'),
('dmesg-before','dmesg'),
]
if args.expect=='v5':
    commands.extend([
    ('alpine-openrc','cat /etc/os-release; /sbin/openrc --version; /sbin/apk --version; cat /proc/1/comm; readlink /proc/1/exe; ps; cat /run/openrc-reached; ls -l /run/openrc/started /run/openrc/softlevel; cat /run/openrc/softlevel'),
    ('startup-logs','cat /run/ufs-stat-initial.txt; cat /run/usb-setup.log; cat /run/lemon-diagnostics.log; cat /var/log/rc.log'),
    ])
commands.extend([
('interval','sleep 15; cat /proc/uptime'),
('ufs-after','for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt" "$d/device/state"; done; cat /proc/mounts; cat /proc/swaps'),
('dmesg-after','dmesg'),
])
raw=bytearray();results=[];status='INCOMPLETE';port=None
try:
    deadline=time.monotonic()+args.wait
    while args.port.upper() not in {p.device.upper() for p in list_ports.comports()}:
        if time.monotonic()>=deadline:raise serial.SerialException('Port absent: '+args.port)
        time.sleep(1)
    port=serial.Serial(port=None,baudrate=115200,timeout=.2,write_timeout=3,xonxoff=False,rtscts=False,dsrdtr=False)
    port.dtr=True;port.rts=False;port.port=args.port;port.open()
    port.write(b'\n');time.sleep(.5);raw.extend(port.read(65536))
    for name,command in commands:
        token=uuid.uuid4().hex;begin='__BEGIN_'+token;end='__END_'+token
        wire=f"printf '\\n{begin}\\n'; {command}; printf '\\n{end}:%s\\n' \"$?\"\n"
        port.write(wire.encode());data=bytearray();deadline=time.monotonic()+45
        marker=re.compile(rb'(?m)^'+end.encode()+rb':(\d+)\r?$')
        while time.monotonic()<deadline:
            data.extend(port.read(65536));match=marker.search(data)
            if match:break
        else:
            raw.extend(data);raise TimeoutError('No completion marker: '+name)
        raw.extend(data)
        start=re.search(rb'(?m)^'+begin.encode()+rb'\r?\n',data)
        if start is None:raise RuntimeError('Missing begin marker: '+name)
        output=bytes(data[start.end():match.start()])
        (logs/(stamp+'-'+name+'.txt')).write_bytes(output)
        results.append({'name':name,'command':command,'last_command_exit':int(match[1]),'bytes':len(output)})
        print(name,len(output),'bytes',flush=True)
        if name=='identity' and ('lemon-bringup-'+args.expect).encode() not in output:
            raise RuntimeError('Kernel does not match expected '+args.expect+'; identity retained')
    status='COLLECTED_NOT_HARDWARE_PASS'
except Exception as error:
    status='ERROR: '+str(error)
    print(status,flush=True)
finally:
    if port is not None:port.close()
    prefix.with_suffix('.raw').write_bytes(raw)
    prefix.with_suffix('.json').write_text(json.dumps({'status':status,'port':args.port,'expect':args.expect,'read_only_commands':True,'results':results},indent=2)+'\n')
if status!='COLLECTED_NOT_HARDWARE_PASS':raise SystemExit(3)
print('Closed port. Logs:',logs)
