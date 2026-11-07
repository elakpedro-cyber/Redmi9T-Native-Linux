from pathlib import Path
import hashlib,json,shutil
root=Path(__file__).resolve().parents[1];out=root/'snapshots/v5-known-good'
assert not out.exists(),'Do not overwrite known-good v5'
out.mkdir(parents=True)
for name in ['bootshim','config','scripts','logs/first-test-v5']:
    shutil.copytree(root/name,out/name,ignore=shutil.ignore_patterns('__pycache__'))
(out/'artifacts').mkdir();(out/'reports').mkdir()
for p in (root/'artifacts').iterdir():
    if 'v5' in p.name or p.name=='sm6115-xiaomi-lemon-v2.dtb':shutil.copy2(p,out/'artifacts'/p.name)
for p in (root/'reports').iterdir():
    if p.is_file() and ('v5' in p.name):shutil.copy2(p,out/'reports'/p.name)
for p in root.glob('*.md'):shutil.copy2(p,out/p.name)
manifest={p.relative_to(out).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.rglob('*')) if p.is_file()}
(out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(out,len(manifest),'files')
