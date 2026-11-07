from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/uefi-deps'))
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from capstone.arm64 import ARM64_OP_IMM,ARM64_OP_REG
blob=next((root/'reports/abl-extracted').rglob('*.pe')).read_bytes()
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);md.detail=True;md.skipdata=True
instructions=list(md.disasm(blob[0x1000:0x42000],0x1000))
targets={}
for label in ['KernelBaseAddr','KernelSize','QueryBootParams Failed: ','Kernel Load Address: 0x%x','calculating dynamic offsets','Shutting Down UEFI Boot Services: %lu ms','DTB header can get corrupted due to runtime kernel size']:
    for encoding in ['ascii','utf-16le']:
        value=label.encode(encoding)
        if value in blob:targets[blob.index(value)]=label+' ('+encoding+')'
registers={};hits=[]
for i,ins in enumerate(instructions):
    if ins.id==0:continue
    ops=ins.operands
    if ins.mnemonic in ['adrp','adr'] and len(ops)==2:
        registers[ops[0].reg]=(ops[1].imm,i)
    elif ins.mnemonic in ['add','sub'] and len(ops)==3 and ops[2].type==ARM64_OP_IMM:
        if ops[1].reg in registers:
            value,age=registers[ops[1].reg]
            delta=ops[2].imm<<ops[2].shift.value
            value=value+delta if ins.mnemonic=='add' else value-delta
            registers[ops[0].reg]=(value,age)
            if i-age<8 and value in targets:hits.append((i,value,targets[value]))
    elif ins.mnemonic=='mov' and len(ops)==2 and ops[1].type==ARM64_OP_REG:
        if ops[1].reg in registers:registers[ops[0].reg]=registers[ops[1].reg]
    elif ops and ops[0].type==ARM64_OP_REG and ins.mnemonic not in ['str','stp','cmp','tst','cbz','cbnz','tbz','tbnz']:
        registers.pop(ops[0].reg,None)
lines=[]
for i,value,name in hits:
    lines.append(f'XREF {name!r} -> {value:#x} at {instructions[i].address:#x}')
    for ins in instructions[max(0,i-24):i+40]:lines.append(f'{ins.address:#x}: {ins.mnemonic} {ins.op_str}')
(root/'reports/abl-v3-placement-xrefs.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(line for line in lines if line.startswith('XREF')))
