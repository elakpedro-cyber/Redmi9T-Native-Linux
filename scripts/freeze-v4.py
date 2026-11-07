from pathlib import Path
import hashlib,json,shutil
root=Path(__file__).resolve().parents[1]
dest=root/'snapshots/v4-known-good'
assert not dest.exists(),'Snapshot already exists; do not replace it'
dest.mkdir(parents=True)
for directory in ['bootshim','config','scripts','logs','reports']:
    shutil.copytree(root/directory,dest/directory,ignore=shutil.ignore_patterns('__pycache__'))
for p in root.glob('*.md'):shutil.copy2(p,dest/p.name)
(dest/'artifacts').mkdir()
for p in (root/'artifacts').iterdir():
    if p.is_file() and ('v4' in p.name or p.name=='sm6115-xiaomi-lemon-v2.dtb'):
        shutil.copy2(p,dest/'artifacts'/p.name)
(dest/'sources').mkdir()
for name in ['linux.tar.gz','busybox-1.37.0.tar.bz2']:
    shutil.copy2(root/'downloads'/name,dest/'sources'/name)
(dest/'PROVENANCE.txt').write_text('Hardware-confirmed v4. Linux source commit 05441d697f7f9a927264f4058cbbc6a03dfcac9d. Full original source tarball included. Local bootshim, DTS/config changes and build scripts included. Toolchains/WSL and generated kernel objects are not source and are not copied. Live evidence: logs/v4-live-diagnostics and reports/v4-live-read-audit.json. Snapshot is never rewritten by v5 scripts.\n')
manifest={str(p.relative_to(dest)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(dest.rglob('*')) if p.is_file()}
(dest/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name,info in manifest.items():
    assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==info['sha256'],name
print(dest,len(manifest),'files verified')
