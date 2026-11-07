from pathlib import Path
import hashlib,json,re,struct,zlib
root=Path(__file__).resolve().parents[1]
logs=root/'logs/v4-live-diagnostics'
files=[sorted(logs.glob('*-hex-'+v+'.txt'))[-1] for v in ['a','b']]
samples=[]
for file in files:
    content=file.read_text();disks={}
    for disk,raw in re.findall(r'BEGIN_READ_(sd[a-f])\s+(.*?)END_READ_\1',content,re.S):
        data=bytearray()
        for line in raw.splitlines():
            fields=line.split()
            if len(fields)>1:
                assert int(fields[0],16)==len(data),(disk,line)
                data.extend(b''.join(struct.pack('<H',int(v,16)) for v in fields[1:]))
        assert len(data)==16384,(disk,len(data))
        assert data[4096:4104]==b'EFI PART',disk
        size=struct.unpack_from('<I',data,4096+12)[0]
        header=bytearray(data[4096:4096+size]);crc=struct.unpack_from('<I',header,16)[0];header[16:20]=bytes(4)
        assert zlib.crc32(header)==crc,disk
        disks[disk]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'gpt_header_crc_valid':True}
    assert len(disks)==6
    samples.append(disks)
assert samples[0]==samples[1]
def counters(path):
    t=path.read_text();out={}
    for name,raw in re.findall(r'/sys/block/(sd[a-f])\s+(.*?)(?=/sys/block/|<\d>|\Z)',t,re.S):
        lines=raw.strip().splitlines();values=lines[0].split()
        out[name]={'reads_completed':int(values[0]),'sectors_read_512':int(values[2]),'writes_completed':int(values[4]),'sectors_written_512':int(values[6]),'ioerr_cnt':int(lines[1],16)}
    return out
before=counters(sorted(logs.glob('*-counters-before.txt'))[-1]);after=counters(sorted(logs.glob('*-counters-after.txt'))[-1])
for disk in before:
    assert before[disk]['ioerr_cnt']==after[disk]['ioerr_cnt']
    assert before[disk]['writes_completed']==after[disk]['writes_completed']==0
    assert before[disk]['sectors_written_512']==after[disk]['sectors_written_512']==0
report={'status':'PASS_BOUNDED_READS_ONLY','read_size_per_lun_per_pass':16384,'passes':2,'interval_seconds':20,'samples':samples[0],'before':before,'after':after,'limits':'Small repeated buffered reads; second pass may hit page cache. Not a sustained/direct-I/O or power-management qualification. Existing ioerr_cnt=3 is nonzero but unchanged; cause not established. Initial head -c attempt unsupported and read no disk data.'}
(root/'reports/v4-live-read-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
