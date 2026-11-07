from pathlib import Path
import hashlib,json,shutil
root=Path(__file__).resolve().parents[1]
def entry(p):return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
supplement=root/'snapshots/v4-live-supplement'
assert not supplement.exists(),'Refusing to overwrite sealed live supplement'
supplement.mkdir(parents=True)
shutil.copytree(root/'logs/v4-live-diagnostics',supplement/'logs')
for name in ['live-v4.dtb','v4-live-read-audit.json','v4-live-config-proof.json']:
    shutil.copy2(root/'reports'/name,supplement/name)
shutil.copy2(root/'scripts/serial-readonly-v4.py',supplement/'serial-readonly-v4.py')
shutil.copy2(root/'V4_CONTROL.md',supplement/'V4_CONTROL.md')
manifest={p.relative_to(supplement).as_posix():entry(p) for p in sorted(supplement.rglob('*')) if p.is_file()}
(supplement/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
files=list(root.glob('*.md'))+list((root/'bootshim').glob('*'))
for directory in ['config','scripts','pmaports']:
    files.extend(p for p in (root/directory).rglob('*') if '__pycache__' not in p.parts)
files.extend(p for p in (root/'artifacts').iterdir() if 'v5' in p.name or p.name=='sm6115-xiaomi-lemon-v2.dtb')
files.extend(p for p in (root/'reports').iterdir() if 'v5' in p.name)
files.extend(p for p in (root/'downloads/v5').iterdir())
manifest={p.relative_to(root).as_posix():entry(p) for p in sorted(set(files)) if p.is_file()}
(root/'reports/v5-delivery-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name,info in manifest.items():assert entry(root/name)==info,name
print(len(manifest),'delivery files verified; v4 supplement sealed')
