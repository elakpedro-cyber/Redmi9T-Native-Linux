from pathlib import Path
import json
import struct
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/uefi-deps'))
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
blob=next((root/'reports/abl-extracted').rglob('*.pe')).read_bytes()
ramdisk=(root/'artifacts/initramfs-v3.cpio.gz').stat().st_size
results=[]
for name,variables in [('pcd-fallback',None),('uefi-base-40000000',{'KernelBaseAddr':0x40000000,'KernelSize':0x5700000}),('uefi-base-40200000',{'KernelBaseAddr':0x40200000,'KernelSize':0x5700000})]:
    uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    uc.mem_map(0,0x200000);uc.mem_write(0,blob)
    uc.mem_map(0x1000000,0x200000)
    frame=0x1001000
    def put64(addr,value):uc.mem_write(addr,struct.pack('<Q',value))
    put64(0xc1878,0x1003000);put64(0x1003048,0x1f0000)
    put64(frame-0xa0,0x40000000)
    uc.mem_write(frame-0x38,struct.pack('<I',ramdisk))
    uc.mem_write(frame-0x44,struct.pack('<I',4096))
    uc.reg_write(UC_ARM64_REG_X23,frame)
    uc.reg_write(UC_ARM64_REG_SP,0x1100000)
    def hook(uc,pc,size,data):
        if pc in (0x469c,0x46c4,0x4228):value=0
        elif pc==0x1f0000:
            name=bytes(uc.mem_read(uc.reg_read(UC_ARM64_REG_X0),64)).decode('utf-16le').split('\0',1)[0]
            if variables is None:value=0x800000000000000e
            else:
                assert name in variables,name
                put64(uc.reg_read(UC_ARM64_REG_X4),variables[name]);value=0
        else:return
        uc.reg_write(UC_ARM64_REG_X0,value)
        uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.emu_start(0x16508,0x16694,count=10000)
    values={key:struct.unpack('<Q',uc.mem_read(frame+off,8))[0] for key,off in [('kernel',-0x70),('kernel_end',-0x68),('ramdisk',-0x60),('dtb',-0x58)]}
    expected_base=0x40000000 if variables is None else variables['KernelBaseAddr']
    assert values['kernel']==expected_base+0x80000,values
    expected_end=expected_base+(0x5600000 if variables is None else variables['KernelSize'])
    assert values['kernel_end']==expected_end
    assert values['ramdisk']==expected_end-(((ramdisk+4095)//4096)*4096+4096)
    assert values['dtb']==values['ramdisk']-(0x200000+4096)
    results.append({'scenario':name,'supplied_uefi_variables':variables,'input_base_memory':'0x40000000','load_addresses':{k:hex(v) for k,v in values.items()}})
report={'status':'PASS_ACTUAL_ABL_INSTRUCTIONS_WITH_MODELED_UEFI','span':'0x16508..0x16694','runtime_uefi_values_known':False,'cases':results}
(root/'reports/abl-v3-placement-emulation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
