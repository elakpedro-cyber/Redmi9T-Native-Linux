"""Create and verify the review bundle on the PC; never connects to the phone."""
from pathlib import Path
import argparse,hashlib,io,json,re,tarfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--with-dtb',action='store_true',help='Create a separate DTB-review release; preserve the initial review archive')
args=parser.parse_args()

root=Path(__file__).resolve().parents[1]
out=root/'artifacts/touchscreen-v1'
out.mkdir(parents=True,exist_ok=True)
files=[]
for directory in ['touchscreen-v1','logs/touchscreen-v1']:
    files += [p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
for name in ['lemon_nt36672a.ko','spi-geni-qcom.ko','wlfreerdp3-touch','libuwac0.so.0','touch-pointer.so','touch-events','calibration-candidate.json']:
    files.append(out/name)
if args.with_dtb:
    files += [p for p in (out/'dtb-review').rglob('*') if p.is_file()]
for name in ['TOUCHSCREEN_V1_RESULTS.md','TOUCHSCREEN_STAGE1.md','PROJECT_CHECKPOINT.md','GNOME_PHYSICAL_V21_HARDWARE_RESULTS.md',
             'snapshots/gnome-physical-lcd-v2.1/MANIFEST.json','scripts/fdt_audit.py']:
    files.append(root/name)
rows=[]
for p in sorted(set(files)):
    data=p.read_bytes()
    if p.suffix not in ['.gz','.ko','.so','.png'] and re.search(b'-'*5+b'BEGIN (?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY'+b'-'*5,data):
        raise RuntimeError('Unexpected private key material in '+str(p))
    if p.suffix in ['.pem','.key','.bin'] or p.name in ['known_hosts','id_ed25519','id_rsa']:
        raise RuntimeError('Unexpected credential/firmware file '+str(p))
    rows.append({'path':p.relative_to(root).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
manifest=json.dumps({'scope':'offline review supplement; no automatic device actions','files':rows},indent=2).encode()+b'\n'
manifest_name='MANIFEST-dtb-review.json' if args.with_dtb else 'MANIFEST.json'
(out/manifest_name).write_bytes(manifest)
archive=root/('artifacts/lemon-touchscreen-v1-dtb-review-aarch64.tar.gz' if args.with_dtb else 'artifacts/lemon-touchscreen-v1-aarch64-review.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
    for row in rows:
        p=root/row['path']
        info=tar.gettarinfo(str(p),arcname=row['path'])
        info.uid=info.gid=0;info.uname=info.gname=''
        info.mode=0o755 if p.suffix=='.sh' or p.name in ['touch-events','wlfreerdp3-touch'] else 0o644
        with p.open('rb') as stream:tar.addfile(info,stream)
    info=tarfile.TarInfo('artifacts/touchscreen-v1/'+manifest_name);info.size=len(manifest);info.mode=0o644
    tar.addfile(info,io.BytesIO(manifest))
with tarfile.open(archive) as tar:
    names=tar.getnames()
    assert len(names)==len(rows)+1 and len(names)==len(set(names))
    for row in rows:
        data=tar.extractfile(row['path']).read()
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],row['path']
    assert tar.extractfile('artifacts/touchscreen-v1/'+manifest_name).read()==manifest
release={'archive':archive.relative_to(root).as_posix(),'bytes':archive.stat().st_size,
         'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'verified_payload_files':len(rows),
         'hardware_status':'not loaded or tested; Stage1 gates remain NO-GO',
         'base':'GNOME Physical LCD v2.1 unchanged; full RAM rootfs must be supplied separately'}
(out/('release-dtb-review.json' if args.with_dtb else 'release.json')).write_text(json.dumps(release,indent=2)+'\n',encoding='utf-8')
print(json.dumps(release,indent=2))
