from pathlib import Path
import hashlib,json,os,stat,subprocess
root=Path(__file__).resolve().parents[1]
work=Path('/home/hadirpc/Redmi9T-Native-Linux/rootfs-v7')
full=work/'root';base=work/'boot-root';files=[];manifest={}
for path in sorted(full.rglob('*')):
    name=path.relative_to(full).as_posix()
    if path.is_dir() or name.startswith(('usr/include/','var/log/','tmp/','run/','proc/','sys/','dev/')):continue
    if name in ['lib/apk/db/lock']:continue
    old=base/name
    if path.is_symlink():
        payload=os.readlink(path).encode()
        if old.is_symlink() and os.readlink(old)==os.readlink(path):continue
    else:
        payload=path.read_bytes()
        if old.is_file() and not old.is_symlink() and old.read_bytes()==payload:continue
        assert not payload.startswith(b'-----BEGIN OPENSSH PRIVATE KEY-----'),name
    files.append(name);manifest[name]={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'mode':oct(stat.S_IMODE(path.lstat().st_mode)),'symlink':path.is_symlink()}
assert 'usr/local/bin/gpu-render-v7' in files
assert any('libgallium' in name for name in files)
assert not any(n.startswith(('root/','rescue/','etc/init.d/','etc/runlevels/','lib/modules/')) or n=='init' for n in files)
filelist=work/'gpu-addon-files.list';filelist.write_bytes(b''.join(n.encode()+b'\0' for n in files))
output=root/'artifacts/gpu-userspace-v7.tar.gz'
subprocess.run(['tar','--sort=name','--numeric-owner','--owner=0','--group=0','--mtime=2026-11-05 00:00:00Z','-I','gzip -n -9','-C',str(full),'--null','-T',str(filelist),'-cf',str(output)],check=True)
(root/'reports/gpu-userspace-v7-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(root/'reports/gpu-userspace-v7.json').write_text(json.dumps({'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'files':len(files),'base':'Alpine v7 boot-root; RAM-only additive userspace bundle; not auto-loaded'},indent=2)+'\n')
print('GPU addon:',output.stat().st_size,'bytes;',len(files),'files')
