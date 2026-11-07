from pathlib import Path
import hashlib,json,shutil
root=Path(__file__).resolve().parents[1];target=root/'snapshots/v6-hardware-validated'
assert not target.exists(),'Do not overwrite hardware-validated snapshot'
target.mkdir(parents=True)
for folder in ['bootshim','config','scripts']:
    shutil.copytree(root/folder,target/folder,ignore=shutil.ignore_patterns('__pycache__'))
for folder in ['logs/v6-authorized','logs/first-test-v6','logs/hardware-v6']:
    shutil.copytree(root/folder,target/folder)
(target/'artifacts').mkdir();(target/'reports').mkdir()
for p in (root/'artifacts').iterdir():
    if 'v6' in p.name or p.name=='sm6115-xiaomi-lemon-v2.dtb':shutil.copy2(p,target/'artifacts'/p.name)
for p in (root/'reports').iterdir():
    if p.is_file() and ('v6' in p.name or p.name=='first-test-v6-assessment.json'):shutil.copy2(p,target/'reports'/p.name)
for p in root.glob('*.md'):shutil.copy2(p,target/p.name)
(target/'RUNTIME_AUTH_NOTE.txt').write_text('Image SHA 1eade4d8208905703286d01883e76b71728cc36b301f28563b58a0e53d4c8d63 unchanged. Hardware SSH/SCP used a separately approved public key added only to running RAM authorized_keys. Its private key is outside this snapshot in the user .ssh directory and is not copied. Runtime host key likewise not copied. The image still embeds the original user public key. See V6_HARDWARE_RESULTS.md.\n')
files={p.relative_to(target).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(target.rglob('*')) if p.is_file()}
(target/'MANIFEST.json').write_text(json.dumps(files,indent=2)+'\n')
for name,info in files.items():assert hashlib.sha256((target/name).read_bytes()).hexdigest()==info['sha256'],name
print(target,len(files),'files verified; private keys not copied')
