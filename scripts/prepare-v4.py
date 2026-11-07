from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root/'config/init-v3').read_text()
text = text.replace('LEMON_INIT_V3_REACHED', 'LEMON_INIT_V4_REACHED')
text = text.replace("echo 'RAM-only system.", '/sbin/ufs-diagnostics >/run/ufs-diagnostics.log 2>&1 &\n\necho \'RAM-only system.')
(root/'config/init-v4').write_text(text, newline='\n')
text = (root/'scripts/build-shim-v3.sh').read_text().replace('v3', 'v4')
text = text.replace('artifacts/Image"', 'artifacts/Image-v4"')
(root/'scripts/build-shim-v4.sh').write_text(text, newline='\n')
text = (root/'scripts/emulate-shim-v3.py').read_text().replace('v3', 'v4')
text = text.replace("'artifacts/Image'", "'artifacts/Image-v4'")
(root/'scripts/emulate-shim-v4.py').write_text(text, newline='\n')
text = (root/'scripts/package-v3.py').read_text().replace('v3', 'v4')
start = text.index('# Keep the verified original')
end = text.index("shim=(art/")
text = text[:start] + '''# Preserve original newc metadata, including /dev/console; replace userspace.
old=gzip.decompress((art/'initramfs.cpio.gz').read_bytes())
out=bytearray();offset=0;entries=[];names=set()
while old[offset:offset+6]==b'070701':
    fields=[int(old[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
    size,namesize=fields[6],fields[11];start=offset+110
    name=old[start:start+namesize].rstrip(b'\\0').decode().removeprefix('./')
    start=(start+namesize+3)&~3;payload=old[start:start+size]
    offset=(start+size+3)&~3
    if name=='TRAILER!!!':break
    if name=='init':payload=(root/'config/init-v4').read_bytes()
    if name=='bin/busybox':payload=(art/'BusyBox-v4').read_bytes()
    fields[6]=len(payload);entries.append((name,fields,payload));names.add(name)
def add(name,mode,payload):
    assert name not in names,name
    fields=[len(entries)+1000,mode,0,0,1,0,len(payload),0,0,0,0,0,0]
    entries.append((name,fields,payload));names.add(name)
for app in (root/'reports/busybox-v4-applets.txt').read_text().splitlines():
    if app!='busybox' and 'bin/'+app not in names:add('bin/'+app,0o120777,b'busybox')
add('sbin/ufs-diagnostics',0o100755,(root/'config/ufs-diagnostics-v4').read_bytes())
add('TRAILER!!!',0,b'')
for name,fields,payload in entries:
    name=name.encode()+b'\\0';fields[11]=len(name)
    out+=b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)+name
    out+=bytes((-len(out))%4);out+=payload;out+=bytes((-len(out))%4)
out+=bytes((-len(out))%512)
(art/'initramfs-v4.cpio.gz').write_bytes(gzip.compress(bytes(out),compresslevel=9,mtime=0))
''' + text[end:]
(root/'scripts/package-v4.py').write_text(text, newline='\n')
