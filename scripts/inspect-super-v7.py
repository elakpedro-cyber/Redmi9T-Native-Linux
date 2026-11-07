from pathlib import Path
import hashlib,json,struct,subprocess

root=Path(__file__).resolve().parents[1]
out=root/'downloads/v7-personal';out.mkdir(parents=True,exist_ok=True)
key=json.loads((root/'logs/v6-authorized/test-client-identity.json').read_text())['private_key_path']
ssh=['ssh.exe','-i',key,'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','KexAlgorithms=curve25519-sha256','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(root/'logs/hardware-v6/20261105T193940984/usb/known_hosts'),'root@192.168.77.2']
path=out/'super-metadata.bin'
if not path.exists():
    p=subprocess.run(ssh+['test "$(grep PARTNAME /sys/class/block/sda10/uevent)" = PARTNAME=super && head -c 1048576 /dev/sda10'],capture_output=True,timeout=30)
    p.check_returncode();assert len(p.stdout)==1048576
    path.write_bytes(p.stdout)
data=path.read_bytes();g=data[4096:8192]
magic,size=struct.unpack_from('<II',g)
assert magic==0x616c4467 and 52<=size<=4096
assert hashlib.sha256(g[:8]+bytes(32)+g[40:size]).digest()==g[8:40]
max_size,slots,blocksize=struct.unpack_from('<III',g,40)
report={'method':'read-only first 1MiB /dev/sda10; no phone mount/write','metadata_max_size':max_size,'slots':slots,'logical_block_size':blocksize,'partitions':[]}
for slot in range(slots):
    base=12288+slot*max_size
    if base+128>len(data):continue
    h=data[base:];magic,major,minor,hs=struct.unpack_from('<IHHI',h)
    if magic!=0x414c5030:continue
    assert hashlib.sha256(h[:12]+bytes(32)+h[44:hs]).digest()==h[12:44]
    ts=struct.unpack_from('<I',h,44)[0];table=h[hs:hs+ts]
    assert hashlib.sha256(table).digest()==h[48:80]
    po,pc,ps=struct.unpack_from('<III',h,80);eo,ec,es=struct.unpack_from('<III',h,92)
    for i in range(pc):
        p=table[po+i*ps:po+(i+1)*ps]
        name=p[:36].split(b'\0')[0].decode();attr,first,count,group=struct.unpack_from('<IIII',p,36)
        extents=[]
        for j in range(first,first+count):
            sectors,kind,target,source=struct.unpack_from('<QIQI',table,eo+j*es)
            extents.append({'sectors':sectors,'type':kind,'target_sector':target,'source':source})
        report['partitions'].append({'slot':slot,'name':name,'attributes':attr,'extents':extents,'bytes':sum(e['sectors']*512 for e in extents)})
(root/'reports/v7-super-metadata.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
