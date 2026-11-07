from pathlib import Path
import argparse,base64,datetime,hashlib,json,re
parser=argparse.ArgumentParser(description='Pin boot-specific host public key from trusted USB serial log; no network probing')
parser.add_argument('--serial-log',type=Path,required=True)
args=parser.parse_args()
raw=args.serial_log.read_text(errors='replace')
keys=set(re.findall(r'(?m)^ssh-ed25519 ([A-Za-z0-9+/=]+)(?:[^\r\n]*)$',raw))
assert len(keys)==1,'Expected exactly one unique Ed25519 host key in trusted COM log'
public=keys.pop();blob=base64.b64decode(public,validate=True)
assert blob[:15]==b'\0\0\0\x0bssh-ed25519' and len(blob)==51
fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('=')
root=Path(__file__).resolve().parents[1];out=root/'logs/v8-host-pin'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
(out/'host-ed25519.pub').write_text('ssh-ed25519 '+public+'\n',newline='\n')
(out/'known_hosts').write_text('192.168.77.2 ssh-ed25519 '+public+'\n',newline='\n')
(out/'pin.json').write_text(json.dumps({'fingerprint':fingerprint,'trusted_transport':'physical USB ACM','serial_log':str(args.serial_log.resolve()),'scope':'this boot only; host private key regenerates in RAM'},indent=2)+'\n')
print(fingerprint);print(out)
