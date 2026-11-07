"""Offline string xrefs in the saved uncompressed ARM64 TWRP Image; no execution."""
from pathlib import Path
import hashlib,json,struct,sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/uefi-deps'))
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM

image=root/'reports/stock-recovery/kernel'
data=image.read_bytes()
assert hashlib.sha256(data).hexdigest()=='4e9946d0160031469fe1d664e75d1e282539ca92dddd21349bd34188154ccdba', 'Saved Image changed; do not reuse file-offset attribution'
needle=b'mode=%d, max_speed_hz=%d'
position=data.index(needle)
string_start=data.rfind(b'\0',0,position)+1
target_page=string_start&~4095
hits=[]
for offset,(word,) in enumerate(struct.iter_unpack('<I',data[:len(data)&~3])):
    pc=offset*4
    if word&0x9f000000!=0x90000000:continue
    immediate=((word>>5)&0x7ffff)<<2 | ((word>>29)&3)
    if immediate&(1<<20):immediate-=1<<21
    if (pc&~4095)+(immediate<<12)!=target_page:continue
    register=word&31
    for addr in range(pc+4,min(pc+64,len(data)-3),4):
        add=struct.unpack_from('<I',data,addr)[0]
        if add&0xffc00000==0x91000000 and (add>>5)&31==register:
            if target_page+((add>>10)&4095)==string_start:hits.append((pc,addr))
out=root/'logs/touchscreen-stage1-final'
out.mkdir(exist_ok=True)
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
lines=['Raw Image file offsets; no asserted virtual base or recovered symbol names.']
for pc,addr in hits:
    lines.append(f'\nXREF string={string_start:#x} ADRP={pc:#x} ADD={addr:#x}')
    for ins in md.disasm(data[max(0,pc-0x240):pc+0x90],max(0,pc-0x240)):
        lines.append(f'{ins.address:#010x}: {ins.mnemonic:8} {ins.op_str}')
(out/'probe-string-xrefs.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
result={'image':str(image.relative_to(root)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
        'literal_offset':hex(string_start),'xrefs':[[hex(a),hex(b)] for a,b in hits],
        'scope':'static disassembly only; register field attribution requires separate evidence'}
expected={0x7f98b4:('strb','wzr, [x23, #0x35c]'),0x7f98d8:('strb','w10, [x9, #0x35d]'),0x7f98e0:('strh','wzr, [x9, #0x35e]')}
for address,want in expected.items():
    ins=next(md.disasm(data[address:address+4],address))
    assert (ins.mnemonic,ins.op_str)==want
result['verified_zero_store_file_offset']='0x7f98b4'
result['field_attribution']='CS0 follows stock spi_device u32 speed/u8 CS/u8 bits/u16 mode layout, nearby mode print and Xiaomi probe source; not an electrical measurement'
(out/'stock-binary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
