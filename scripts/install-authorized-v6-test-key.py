from pathlib import Path
import base64,datetime,json,re,shlex,subprocess,sys,time,uuid
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/serial-deps'))
import serial
logs=root/'logs/v6-authorized'
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
private=Path.home()/'.ssh'/('redmi9t_v6_test_'+stamp)
assert not private.exists()
subprocess.run(['ssh-keygen.exe','-q','-t','ed25519','-N','','-C','redmi9t-v6-controlled-test','-f',str(private)],check=True)
public=private.with_suffix('.pub').read_text().strip()
assert public.split()[0]=='ssh-ed25519'
base64.b64decode(public.split()[1],validate=True)
token=uuid.uuid4().hex;begin='__KEY_BEGIN_'+token;end='__KEY_END_'+token
command='''test "$(/bin/busybox awk '$2 == "/" {print $3}' /proc/mounts)" = rootfs && test ! -L /root/.ssh && test ! -L /root/.ssh/authorized_keys && printf '\\n%s\\n' '''+shlex.quote(public)+''' >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys && echo RAM_TEST_PUBLIC_KEY_ADDED && ls -ld /root/.ssh /root/.ssh/authorized_keys'''
wire=f"printf '\\n{begin}\\n'; {command}; printf '\\n{end}:%s\\n' \"$?\"\n"
port=serial.Serial(port=None,baudrate=115200,timeout=.2,write_timeout=3,xonxoff=False,rtscts=False,dsrdtr=False)
port.dtr=True;port.rts=False;port.port='COM4'
raw=bytearray()
try:
    port.open();port.write(b'\n');time.sleep(.5);raw.extend(port.read(65536))
    port.write(wire.encode());deadline=time.monotonic()+20
    marker=re.compile(rb'(?m)^'+end.encode()+rb':(\d+)\r?$')
    while time.monotonic()<deadline:
        raw.extend(port.read(65536));match=marker.search(raw)
        if match:break
    else:raise TimeoutError('No completion marker')
    assert int(match[1])==0 and b'RAM_TEST_PUBLIC_KEY_ADDED' in raw,raw.decode(errors='replace')
finally:
    port.close();(logs/'ram-test-key-install.raw').write_bytes(raw)
fingerprint=subprocess.check_output(['ssh-keygen.exe','-lf',str(private.with_suffix('.pub'))]).decode().strip()
(logs/'test-client-identity.json').write_text(json.dumps({'private_key_path':str(private),'public_key_fingerprint':fingerprint,'phone_path':'/root/.ssh/authorized_keys','phone_storage':'RAM rootfs','original_public_key_preserved':True,'phone_reboot_or_flash_performed':False},indent=2)+'\n')
print('Public key added to RAM; private key remains only on PC:',private)
