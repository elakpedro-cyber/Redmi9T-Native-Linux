"""Offline Novatek normal firmware header audit. Never uploads firmware."""
import argparse,hashlib,json,struct
from pathlib import Path

def inspect(data):
    if len(data)<4096 or len(data)>1024*1024 or len(data)%4096:
        raise ValueError('Invalid firmware extent')
    end=next((n for n in range(len(data),4095,-4096) if data[n-3:n] in (b'NVT',b'MOD')),None)
    if end is None: raise ValueError('Missing sector end marker')
    version,inverse=data[end-4096:end-4096+2]
    if version+inverse!=255: raise ValueError('Version complement mismatch')
    u32=lambda n:struct.unpack_from('<I',data,n)[0]
    header_end=u32(0)
    if header_end<0x30 or header_end>min(len(data),65536) or (header_end-0x30)%16:
        raise ValueError('Invalid partition table extent')
    partitions=[]
    def add(name,offset,address,size,crc=None):
        count=size+1 if size else 0
        if offset>len(data) or count>len(data)-offset or address>0xffffff or count>0x1000000-address:
            raise ValueError('Partition range overflow')
        checksum=(-sum(data[offset:offset+count])-size)&0xffffffff if count else 0
        partitions.append(dict(name=name,offset=offset,address=address,size_inclusive=size,bytes=count,computed_checksum=checksum,header_crc=crc))
    for i,name in enumerate(('ILM','DLM')): add(name,u32(i*12),u32(i*12+4),u32(i*12+8),u32(0x18+i*4))
    for pos in range(0x30,header_end,16): add('INFO',u32(pos+8),u32(pos),u32(pos+4),u32(pos+12))
    overlays=data[0x28]&15 if data[0x28]&0x10 else 0
    base=partitions[1]['offset']
    if base+16*overlays>len(data): raise ValueError('Overlay header outside file')
    for i in range(overlays):
        pos=base+16*i;add('OVERLAY',u32(pos+8),u32(pos),u32(pos+4),u32(pos+12))
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),fw_need_write_size=end,version=version,partitions=partitions,
        warning='Structure audit only: PID, signature, SRAM allowlist, powered hardware and upload safety are not proven')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('file',type=Path);args=parser.parse_args()
    print(json.dumps(inspect(args.file.read_bytes()),indent=2))
