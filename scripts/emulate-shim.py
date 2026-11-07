from pathlib import Path
import json
import struct
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/uefi-deps'))
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from fdt_audit import Fdt

symbols={}
for line in (root/'reports/bootshim-symbols.txt').read_text().splitlines():
    parts=line.split()
    if len(parts)==3:symbols[parts[2]]=int(parts[0],16)
image=(root/'artifacts/bootshim.Image').read_bytes()
native=(root/'artifacts/Image').read_bytes()
incoming=(root/'reports/live.dtb').read_bytes()
base=0x40080000
results=[]
for test in ['live-twrp-dtb','invalid-fdt','initrd-overlap']:
    uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    uc.mem_map(0x40000000,0x6000000)
    uc.mem_map(0x80000000,0x2400000)
    uc.mem_write(base,image)
    blob=incoming if test!='invalid-fdt' else bytes(len(incoming))
    if test=='initrd-overlap':blob=(root/'reports/shim-input-overlap.dtb').read_bytes()
    uc.mem_write(0x43000000,blob)
    uc.reg_write(UC_ARM64_REG_X0,0x43000000)
    uc.reg_write(UC_ARM64_REG_PSTATE,0x3c5)
    uc.cpr_write(3,0,1,0,0,0)
    assert uc.cpr_read(3,0,1,0,0)==0
    outcome={}
    def reached(uc,pc,size,data):
        outcome['native_entry']=hex(pc)
        outcome['x0_dtb']=hex(uc.reg_read(UC_ARM64_REG_X0))
        outcome['x1_x2_x3']=[uc.reg_read(reg) for reg in [UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3]]
        uc.emu_stop()
    def halted(uc,pc,size,data):
        outcome['halt_reason']=uc.reg_read(UC_ARM64_REG_X0)
        uc.emu_stop()
    uc.hook_add(UC_HOOK_CODE,reached,begin=0x80000000,end=0x80000000)
    uc.hook_add(UC_HOOK_CODE,halted,begin=base+symbols['halt'],end=base+symbols['halt'])
    uc.emu_start(base,0,count=400000000)
    if test=='live-twrp-dtb':
        assert outcome.get('native_entry')=='0x80000000',outcome
        assert outcome['x0_dtb']=='0x82000000' and outcome['x1_x2_x3']==[0,0,0]
        assert bytes(uc.mem_read(0x80000000,len(native)))==native
        image_size=struct.unpack_from('<Q',native,16)[0]
        assert not any(uc.mem_read(0x80000000+len(native),image_size-len(native)))
        hdr=bytes(uc.mem_read(0x82000000,8));length=struct.unpack_from('>I',hdr,4)[0]
        path=root/'reports/emulated-mainline-v2.dtb'
        path.write_bytes(uc.mem_read(0x82000000,length))
        old,new=Fdt(root/'reports/live.dtb'),Fdt(path)
        oldmem=next(p for p,v in old.nodes.items() if v.get('device_type')==b'memory\0')
        newmem=next(p for p,v in new.nodes.items() if v.get('device_type')==b'memory\0')
        assert old.nodes[oldmem]['reg']==new.nodes[newmem]['reg']
        for prop in ['linux,initrd-start','linux,initrd-end']:
            assert old.nodes['/chosen'][prop]==new.nodes['/chosen'][prop]
        raw=path.read_bytes();rsv=struct.unpack_from('>I',raw,16)[0]
        reservations=[]
        while True:
            addr,size=struct.unpack_from('>QQ',raw,rsv);rsv+=16
            if not addr and not size:break
            reservations.append((addr,size))
        count=0
        nomap_count=0
        nomap_ranges=[]
        for node,props in new.nodes.items():
            if node.startswith('/reserved-memory/') and 'reg' in props and 'no-map' in props:
                cells=new.cells(props['reg'])
                nomap_ranges.extend((((cells[i]<<32)|cells[i+1]),((cells[i+2]<<32)|cells[i+3])) for i in range(0,len(cells),4))
        for node,props in old.nodes.items():
            if node.startswith('/reserved-memory/') and 'reg' in props:
                cells=old.cells(props['reg'])
                for i in range(0,len(cells),4):
                    addr=(cells[i]<<32)|cells[i+1];size=(cells[i+2]<<32)|cells[i+3]
                    if size:
                        assert (addr,size) in reservations;count+=1
                        if 'no-map' in props:
                            assert any(addr>=a and addr+size<=a+n for a,n in nomap_ranges),(node,hex(addr))
                            nomap_count+=1
        assert new.nodes['/']['compatible']==Fdt(root/'artifacts/sm6115-xiaomi-lemon-v2.dtb').nodes['/']['compatible']
        outcome['payload_comparison']='kernel copied byte-for-byte; BSS tail zero; RAM and initrd fixups preserved'
        outcome['firmware_reserved_ranges_preserved']=count
        outcome['firmware_no_map_ranges_preserved']=nomap_count
    else:
        assert outcome.get('halt_reason')==({'invalid-fdt':13,'initrd-overlap':10}[test]),outcome
    results.append({'test':test,**outcome})
(root/'reports/bootshim-emulation.json').write_text(json.dumps({'status':'PASS_OFFLINE_ONLY','kernel_not_executed':True,'cases':results},indent=2)+'\n')
print(json.dumps(results,indent=2))
