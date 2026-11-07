from pathlib import Path
import json,re,sys,time,uuid
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tools/serial-deps'))
import serial
log=root/'logs/v8b-authorized';end='__GPU_SERIAL_END_'+uuid.uuid4().hex
command='i=0; while test "$i" -lt 12; do echo GPU_SERIAL_HEARTBEAT; cat /proc/uptime; dmesg | tail -n 18; sleep 5; i=$((i+1)); done'
wire=command+f'; printf "\\n{end}:%s\\n" "$?"\n';raw=bytearray();complete=False
try:
    with serial.Serial('COM4',115200,timeout=.2,write_timeout=3,rtscts=False,dsrdtr=False) as port:
        port.write(b'\n');time.sleep(.3);raw.extend(port.read(65536));port.write(wire.encode())
        (log/'gpu-com-monitor-ready.json').write_text(json.dumps({'started':time.time(),'port':'COM4','read_only_commands':command})+'\n')
        with (log/'gpu-com-monitor.raw').open('wb') as output:
            output.write(raw);deadline=time.monotonic()+75
            while time.monotonic()<deadline:
                chunk=port.read(65536);raw.extend(chunk);output.write(chunk);output.flush()
                if re.search(rb'(?m)^'+end.encode()+rb':0\r?$',raw):complete=True;break
        if not complete:port.write(b'\x03')
finally:
    (log/'gpu-com-monitor-result.json').write_text(json.dumps({'completed':complete,'bytes':len(raw),'heartbeats':len(re.findall(rb'(?m)^GPU_SERIAL_HEARTBEAT\r?$',raw))},indent=2)+'\n')
print('COM4 read-only monitor completed:',complete)

