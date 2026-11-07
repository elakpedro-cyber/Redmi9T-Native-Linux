from pathlib import Path
import json
import struct
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/uefi-deps'))
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from fdt_audit import Fdt
pe=next((root/'reports/abl-extracted').rglob('*.pe')).read_bytes()
MASK=0x35555555550000

def match(path,pmics=(0x2d,0x25),selection_bit=53):
    dt=Fdt(path)
    uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    uc.mem_map(0,0x200000); uc.mem_write(0,pe)
    uc.mem_map(0x1000000,0x400000)
    uc.reg_write(UC_ARM64_REG_SP,0x1200000)
    uc.reg_write(UC_ARM64_REG_CPACR_EL1,3<<20)
    def put64(addr,value):uc.mem_write(addr,struct.pack('<Q',value))
    cur,best,tls,safe=0x1000000,0x1001000,0x1002000,0x1100000
    put64(cur+0xa0,0x1300000); put64(tls,safe)
    put64(0xc0118,0x123456789)
    put64(0xc1870,0x1003000); put64(0x1003160,0x1004000)
    pointers={}; ptr=0x1310000
    for key,value in dt.nodes['/'].items():
        pointers[key]=(ptr,len(value)); uc.mem_write(ptr,value);ptr+=(len(value)+15)&~15
    def reg(i):return uc.reg_read(UC_ARM64_REG_X0+i)
    def ret(value=0):
        uc.reg_write(UC_ARM64_REG_X0,value)
        uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
    def string(addr):
        return bytes(uc.mem_read(addr,256)).split(b'\0',1)[0].decode()
    phase=[False]
    def hook(uc,address,size,user):
        if phase[0] and address in (0x19fd0,0x19fd4,0x19fe4):
            uc.emu_stop()
        elif address==0x2af18:ret(tls)
        elif address in (0x469c,0x46c4,0x4228):ret()
        elif address==0x3aa10 or address==0x1004000:
            uc.mem_write(reg(0),bytes(uc.mem_read(reg(1),reg(2))));ret(reg(0))
        elif address==0x3b16c:
            uc.mem_write(reg(0),bytes([reg(2)&255])*reg(1));ret(reg(0))
        elif address==0x3c390:ret(0 if string(reg(1))=='/' else 0xffffffff)
        elif address==0x3c8f8:
            name=string(reg(2)); ptr,size=pointers.get(name,(0,-1))
            uc.mem_write(reg(3),struct.pack('<i',size));ret(ptr)
        elif address==0x14e20:ret(444)
        elif address==0x14e30:ret(0x10000)
        elif address==0x14e40:ret(2)
        elif address==0x14e60:ret(0x22)
        elif address==0x14e70:ret(0)
        elif address==0x14e80:ret(0x10022)
        elif address==0x14fe8:ret(0)
        elif address==0x14118:ret(pmics[reg(0)] if reg(0)<len(pmics) else 0)
        elif address==0x14330:ret(0x10100 if reg(0)==0 else 0x20000 if reg(0)==1 else 0)
        elif address==0x130fc:raise RuntimeError('stack canary failure')
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.reg_write(UC_ARM64_REG_X0,cur);uc.reg_write(UC_ARM64_REG_X1,best);uc.reg_write(UC_ARM64_REG_X2,selection_bit)
    uc.reg_write(UC_ARM64_REG_LR,0x1005000)
    try:uc.emu_start(0x1a0e0,0x1005000,count=1000000)
    except Exception as error:
        raise RuntimeError(f'{path.name}: PC={uc.reg_read(UC_ARM64_REG_PC):#x}: {error}') from error
    flags=struct.unpack('<Q',uc.mem_read(cur+0x98,8))[0]
    selected=bool(uc.reg_read(UC_ARM64_REG_X0))
    # Execute the saved ABL's actual ALL_BITS test and flag-setting instructions.
    uc.reg_write(UC_ARM64_REG_X28,0x1006000)
    put64(0x1006000-0x18,flags)
    phase[0]=True
    uc.emu_start(0x19f7c,0x19fd0,count=10000)
    return {'file':path.name,'selected':selected,'selection_bit':selection_bit,'match_bits':hex(flags),'exact_mask':hex(MASK),'all_bits':flags&MASK==MASK,'actual_skip_dtbo_flag':bytes(uc.mem_read(0xc1910,1))[0],'limitations':'UEFI board APIs replaced with TWRP metadata; PMIC order and zero-valued absent UEFI slots assumed, not queried from running ABL'}

if __name__=='__main__':
    paths=[root/'reports/stock-boot/dtb',root/'artifacts/sm6115-xiaomi-lemon-boot.dtb',root/'reports/lemon-exact-match-candidate.dtb']
    result=[match(path) for path in paths if path.exists()]
    result.append(match(root/'reports/stock-overlay-0.dtbo',selection_bit=52))
    (root/'reports/abl-match-emulation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
