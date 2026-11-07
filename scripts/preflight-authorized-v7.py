from pathlib import Path
import gzip,hashlib,json,struct,subprocess,sys
root=Path(__file__).resolve().parents[1];log=root/'logs/v7-authorized';checks=[]
expected={
 'boot-linux-test-v7.img':(24428544,'0ae797dbf092aaeb6fee4cb7a6d646a296f27c9f44ca9ead80fa57785f370746'),
 'boot-linux-test-v6.img':(23670784,'1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63'),
 'gpu-userspace-v7.tar.gz':(85770796,'b81dcac42177033382803779dd0ef1450a42e096a76b22fb260737bac6297620'),
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,(size,digest) in expected.items():
    p=root/'artifacts'/name;assert p.stat().st_size==size and sha(p)==digest,name;checks.append(name+' size/SHA verified')
snap=root/'snapshots/v6-hardware-validated'
for name,info in json.loads((snap/'MANIFEST.json').read_text()).items():assert sha(snap/name.replace('\\','/'))==info['sha256'],name
checks.append('All 356 sealed v6 snapshot files unchanged')
for name,info in json.loads((root/'reports/backup-sha256-before.json').read_text()).items():assert sha(root.parent/'platform-tools/Redmi9T_Backup'/name)==info['sha256'],name
checks.append('Original Android backups unchanged')
image=root/'artifacts/boot-linux-test-v7.img';header=image.read_bytes()[:1660]
assert header[:8]==b'ANDROID!' and struct.unpack_from('<II',header,36)==(4096,2)
out=log/'preflight-unpacked'
p=subprocess.run([sys.executable,str(root/'tools/unpack_bootimg.py'),'--boot_img',str(image),'--out',str(out)],capture_output=True,check=True)
(log/'boot-header.txt').write_bytes(p.stdout)
for name,target in [('kernel',root/'artifacts/bootshim-v7.Image.gz'),('ramdisk',root/'artifacts/initramfs-v7.cpio.gz'),('dtb',root/'reports/stock-boot/dtb')]:assert (out/name).read_bytes()==target.read_bytes(),name
assert gzip.decompress((out/'kernel').read_bytes())==(root/'artifacts/bootshim-v7.Image').read_bytes()
checks.append('AOSP header v2/page4096, exact kernel/initramfs/stock DTB verified')
sys.path.insert(0,str(root/'scripts'));from fdt_audit import Fdt
dt=Fdt(root/'artifacts/sm6115-xiaomi-lemon-v7.dtb')
for path,props in dt.nodes.items():
    if b'sm6115-mdss' in props.get('compatible',b'') or b'sm6115-dsi-ctrl' in props.get('compatible',b''):assert props.get('status')==b'disabled\0'
checks.append('DSI/MDSS disabled; no touch node enabled by v7 changes')
param=(root/'config/modprobe-gpu-v7.conf').read_text();assert 'blacklist msm' in param and 'options msm separate_gpu_kms=1' in param
checks.append('msm module parameter separate_gpu_kms=1; alias autoload blacklisted')
(log/'preflight.json').write_text(json.dumps({'status':'PASS','scope':'User authorized one boot-only v7 flash + one GPU driver/render attempt, fallback v6 if necessary','checks':checks},indent=2)+'\n')
print('\n'.join(checks))
