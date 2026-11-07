from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
files=list(root.glob('*.md'))+list((root/'bootshim').glob('*'))
for folder in ['config','scripts','logs/first-test-v5']:
    files.extend(p for p in (root/folder).rglob('*') if '__pycache__' not in p.parts)
files.extend(p for p in (root/'artifacts').iterdir() if 'v6' in p.name or p.name=='boot-linux-test-v5.img')
files.extend(p for p in (root/'reports').iterdir() if 'v6' in p.name or p.name=='first-test-v5-assessment.json')
files=[p for p in files if p.is_file() and p.name!='v6-delivery-manifest.json']
manifest={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(files))}
(root/'reports/v6-delivery-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name,info in manifest.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==info['sha256'],name
print(len(manifest),'v6 delivery files verified')
