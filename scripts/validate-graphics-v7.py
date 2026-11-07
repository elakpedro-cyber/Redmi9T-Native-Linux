from pathlib import Path
import gzip,hashlib,json,struct,tarfile
from fdt_audit import Fdt
root=Path(__file__).resolve().parents[1];checks=[]
def check(ok,label):
    assert ok,label
    checks.append(label)
old=Fdt(root/'artifacts/sm6115-xiaomi-lemon-v2.dtb');new=Fdt(root/'artifacts/sm6115-xiaomi-lemon-v7.dtb')
changes=[]
for p in old.nodes.keys()|new.nodes.keys():
    a=old.nodes.get(p,{});b=new.nodes.get(p,{})
    for k in a.keys()|b.keys():
        if a.get(k)!=b.get(k):changes.append((p,k,b.get(k)))
check(len(changes)==1 and changes[0][1]=='firmware-name' and changes[0][2]==b'qcom/sm6115/xiaomi/lemon/a610_zap.mdt\0','only DT change is device-specific firmware path')
check(new.nodes['/soc@0/gpu@5900000']['status']==b'okay\0','native GPU enabled in DT')
for p,props in new.nodes.items():
    compat=props.get('compatible',b'')
    if any(c in compat for c in [b'sm6115-mdss',b'sm6115-dsi-ctrl',b'sm6115-dispcc']):check(props.get('status')==b'disabled\0','display remains disabled: '+p)
cfg=(root/'config/linux-v7.config').read_text()
check('CONFIG_DRM_MSM=m\n' in cfg and 'CONFIG_DRM_MSM_DSI=y' not in cfg and '# CONFIG_DRM_MSM_DPU is not set' in cfg,'GPU module without DPU/DSI')
blob=(root/'downloads/v7-personal/firmware/a610_zap.mdt').read_bytes()
check(blob[:5]==b'\x7fELF\x01','ZAP is ELF32 MDT')
phoff=struct.unpack_from('<I',blob,28)[0];ents,n=struct.unpack_from('<HH',blob,42)
ph=[struct.unpack_from('<8I',blob,phoff+i*ents) for i in range(n)]
check(ents==32 and n==3,'MDT program header table valid')
headerlen=ph[0][4];hashlen=ph[1][4]
check((ph[1][6]&0x7000000)==0x2000000 and len(blob)==headerlen+hashlen,'packed authentication metadata and hash segment valid')
check(blob[:headerlen]==(root/'downloads/v7-personal/firmware/a610_zap.b00').read_bytes(),'MDT header equals b00')
check(blob[headerlen:]==(root/'downloads/v7-personal/firmware/a610_zap.b01').read_bytes(),'MDT authentication data equals b01')
load=ph[2];check(load[0]==1 and load[6]&0x8000000,'ZAP PT_LOAD is relocatable; not a physical write to address 0x5000')
payload=(root/'downloads/v7-personal/firmware/a610_zap.b02').read_bytes()
check(len(payload)==load[4]<=load[5],'split b02 matches load segment size')
needed=((load[3]+load[5]+4095)&~4095)-load[3]
zap=next(p for p in new.nodes if p.endswith('/gpu@5900000/zap-shader'))
provider=new.phandles[new.cells(new.nodes[zap]['memory-region'])[0]]
reg=new.cells(new.nodes[provider]['reg']);address=(reg[0]<<32)|reg[1];size=(reg[2]<<32)|reg[3]
check(address==0xfa400000 and needed<=size==8192,'relocated ZAP 4096 bytes fits reserved RAM at 0xfa400000/8192')
cpio=gzip.decompress((root/'artifacts/initramfs-v7.cpio.gz').read_bytes());entries={};off=0
while cpio[off:off+6]==b'070701':
    f=[int(cpio[off+6+i*8:off+14+i*8],16) for i in range(13)];start=off+110
    name=cpio[start:start+f[11]-1].decode().removeprefix('./');start=(start+f[11]+3)&~3
    entries[name]=cpio[start:start+f[6]];off=(start+f[6]+3)&~3
    if name=='TRAILER!!!':break
for name in ['a610_zap.mdt','a610_zap.b00','a610_zap.b01','a610_zap.b02']:
    check(entries['lib/firmware/qcom/sm6115/xiaomi/lemon/'+name]==(root/'downloads/v7-personal/firmware'/name).read_bytes(),'device-owned firmware exact: '+name)
check(entries['lib/firmware/qcom/a630_sqe.fw']==(root/'downloads/v7-personal/firmware/a630_sqe.fw').read_bytes(),'SQE firmware exact')
module=next(n for n in entries if n.endswith('/msm.ko'))
check(b'vermagic=7.4.0-rc1-lemon-bringup-v7 ' in entries[module],'MSM module ABI matches kernel release')
check(entries['etc/modprobe.d/lemon-gpu-manual.conf']==(root/'config/modprobe-gpu-v7.conf').read_bytes(),'alias loading blacklisted; explicit GPU-only separate_gpu_kms=1')
check(b'modprobe' not in entries['init'] and b'mdev' not in entries['init'],'init has no module autoload daemon')
check(entries['usr/local/sbin/lemon-usb-gadget']==(root/'config/lemon-usb-gadget-v6').read_bytes(),'proven v6 ACM/NCM helper unchanged')
check(entries['etc/init.d/lemon-sshd']==(root/'config/lemon-sshd-v6').read_bytes(),'proven password-disabled Dropbear service unchanged')
check(entries['root/.ssh/authorized_keys'].splitlines()==(root/'config/ssh-authorized-keys-v7').read_bytes().splitlines(),'both intended public identities persist in initramfs')
check(len(entries['root/.ssh/authorized_keys'].splitlines())==2,'two authorized public keys only')
check(not any(v.startswith(b'-----BEGIN OPENSSH PRIVATE KEY-----') for v in entries.values()),'no OpenSSH private client key in initramfs')
emulated=Fdt(root/'reports/emulated-mainline-v7.dtb')
emulated_zap=next(p for p in emulated.nodes if p.endswith('/gpu@5900000/zap-shader'))
check(emulated.nodes[emulated_zap]['firmware-name']==new.nodes[zap]['firmware-name'],'firmware path survives actual emulated bootshim handoff')
previous=dict(line.split('=',1) for line in (root/'config/linux-v6.config').read_text().splitlines() if line.startswith('CONFIG_'))
current=dict(line.split('=',1) for line in cfg.splitlines() if line.startswith('CONFIG_'))
check(all(current.get(k)=='y' for k,v in previous.items() if v=='y'),'all proven v6 built-in features retained')
panel=json.loads((root/'reports/v7-panel-comparison.json').read_text())
check(len(panel['source_comparison'])==58 and all(v['equal'] for v in panel['source_comparison']),'58 selected panel properties match pinned Xiaomi source')
check((root/'reports/v7-native-schema.txt').stat().st_size==0,'native DT has no dt-validate diagnostics')
check((root/'reports/v7-gpu-schema.txt').stat().st_size==0,'GPU DT has no filtered schema diagnostics')
addon=root/'artifacts/gpu-userspace-v7.tar.gz';manifest=json.loads((root/'reports/gpu-userspace-v7-manifest.json').read_text())
with tarfile.open(addon) as tar:
    members={p.name:p for p in tar.getmembers()};check(members.keys()==manifest.keys(),'GPU addon complete; manifest file list exact')
    for name,m in members.items():
        check(not name.startswith('/') and '..' not in Path(name).parts,'addon path stays inside RAM root: '+name)
        payload=m.linkname.encode() if m.issym() else tar.extractfile(m).read()
        check(hashlib.sha256(payload).hexdigest()==manifest[name]['sha256'],'addon SHA256: '+name)
    binary=tar.extractfile('usr/local/bin/gpu-render-v7').read()
    check(binary[:4]==b'\x7fELF' and struct.unpack_from('<H',binary,18)[0]==183,'headless shader probe is ARM64 ELF')
summary={'status':'PASS_OFFLINE_ONLY','phone_reboot_or_flash':False,'GPU_executed':False,'checks':checks,'firmware_qualification':'same-device extraction and format checks; SCM signature acceptance not physically tested'}
(root/'reports/v7-graphics-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print('PASS:',len(checks),'graphics/package checks; no GPU execution')
