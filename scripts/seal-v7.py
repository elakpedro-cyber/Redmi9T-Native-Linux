from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
paths=set()
for folder in ['artifacts','config','scripts','reports']:
    for p in (root/folder).iterdir():
        if p.is_file() and 'v7' in p.name.lower() and p.name not in ['v7-final-manifest.json']:
            paths.add(p)
for pattern in ['V7_*.md','bootshim/*','userspace/*v7*','downloads/v7-personal/firmware/*']:
    paths.update(p for p in root.glob(pattern) if p.is_file())
for name in ['config/cmdline.txt','scripts/fdt_audit.py','tools/mkbootimg.py','tools/unpack_bootimg.py','STATUS.md']:
    paths.add(root/name)
for name in ['artifacts/sm6115-xiaomi-lemon-v2.dtb','reports/stock-boot/dtb','reports/stock-overlay-0.dtbo','reports/live.dtb','reports/live-v4.dtb']:
    paths.add(root/name)
for folder in ['downloads/v7-xiaomi-source','logs/v7-research']:
    paths.update(p for p in (root/folder).rglob('*') if p.is_file())
manifest={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)}
for name in ['artifacts/boot-linux-test-v7.img','artifacts/gpu-userspace-v7.tar.gz']:
    assert name in manifest
v6=root/'artifacts/boot-linux-test-v6.img'
assert v6.stat().st_size==23670784 and hashlib.sha256(v6.read_bytes()).hexdigest()=='1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63'
out=root/'reports/v7-final-manifest.json';out.write_text(json.dumps(manifest,indent=2)+'\n')
for name,entry in json.loads(out.read_text()).items():
    p=root/name;assert p.stat().st_size==entry['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],name
print('PASS: sealed and reread',len(manifest),'v7 audit files; v6 image unchanged')
