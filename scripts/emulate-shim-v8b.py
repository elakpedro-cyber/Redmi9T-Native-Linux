from pathlib import Path
import argparse
import json
import struct
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/uefi-deps'))
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from fdt_audit import Fdt

parser = argparse.ArgumentParser()
parser.add_argument('--shim-image', type=Path, default=root/'artifacts/bootshim-v8b.Image')
parser.add_argument('--symbols', type=Path, default=root/'reports/bootshim-v8b-symbols.txt')
parser.add_argument('--output', type=Path, default=root/'reports')
parser.add_argument('--placement', type=Path, default=root/'reports/abl-v8b-placement-emulation.json')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
symbols={}
for line in args.symbols.read_text().splitlines():
    parts=line.split()
    if len(parts)==3:symbols[parts[2]]=int(parts[0],16)
image=args.shim_image.read_bytes()
native=(root/'artifacts/Image-v8b').read_bytes()
image_size=struct.unpack_from('<Q',native,16)[0]
incoming=(root/'reports/live.dtb').read_bytes()
instructions=list(Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(image[symbols['entry']:symbols['memcpy']],symbols['entry']))
cache_ops={i.address:(i.mnemonic,i.op_str) for i in instructions if i.mnemonic in ['dc','ic','dsb','isb']}
control_reads={i.address:i.op_str for i in instructions if i.mnemonic=='mrs' and i.op_str.startswith('x11, sctlr_el')}
cases=[
    ('el1-daif-clear',0x40080000,0x005,None,None),
    ('el1-relocated-partial-daif',0x40280000,0x085,None,None),
    ('el1-relocated-high',0x41080000,0x145,None,None),
    ('el2-daif-clear',0x40480000,0x009,None,None),
    ('el1-icache-enabled',0x40880000,0x005,None,None),
    ('invalid-fdt',0x40080000,0x005,None,13),
    ('initrd-overlap',0x40080000,0x005,None,10),
    ('source-overlap-fdt',0x42080000,0x005,None,34),
    ('source-overlap-native',0x80080000,0x005,None,10),
    ('source-unaligned',0x40080008,0x005,None,32),
    ('modeled-mmu-enabled',0x40080000,0x005,1,12),
    ('modeled-dcache-enabled',0x40080000,0x009,4,12),
]
placement=json.loads(args.placement.read_text())
live_cases={}
for case in placement['cases']:
    name='large-initrd-'+case['scenario']
    live_cases[name]=case['load_addresses']
    cases.append((name,int(case['load_addresses']['kernel'],16),0x005,None,None))
results=[]
for name,base,pstate,control_override,expected_halt in cases:
    uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    uc.mem_map(0x40000000,0x8000000)
    uc.mem_map(0x80000000,0x2400000)
    uc.mem_write(base,image)
    blob=incoming
    if name=='invalid-fdt':blob=bytes(len(incoming))
    if name=='initrd-overlap':blob=(root/'reports/shim-input-overlap.dtb').read_bytes()
    incoming_addr=0x43000000
    if name in live_cases:
        addresses=live_cases[name]
        blob=(root/'reports'/('shim-input-v8b-'+name+'.dtb')).read_bytes()
        incoming_addr=int(addresses['dtb'],16)
        rd=int(addresses['ramdisk'],16)
        ramdisk=(root/'artifacts/initramfs-v8b.cpio.gz').read_bytes()
        uc.mem_write(rd,ramdisk)
    uc.mem_write(incoming_addr,blob)
    uc.reg_write(UC_ARM64_REG_X0,incoming_addr)
    uc.reg_write(UC_ARM64_REG_PSTATE,pstate)
    initial_sctlr=0x1000 if name=='el1-icache-enabled' else 0
    uc.cpr_write(3,0,1,0,0,initial_sctlr)
    uc.cpr_write(3,4,1,0,0,0)
    assert uc.cpr_read(3,0,1,0,0)==initial_sctlr and uc.cpr_read(3,4,1,0,0)==0
    ctr=uc.cpr_read(3,3,0,0,1)
    line_size=4<<((ctr>>16)&15)
    expected_lines=[(0x80000000,image_size),(0x82000000,0x20000)]
    counts={'civac':0,'cvac':0}
    total=sum((size+line_size-1)//line_size for _,size in expected_lines)
    order=[];outcome={};first_write=[]
    def reached(uc,pc,size,data):
        outcome['native_entry']=hex(pc)
        outcome['x0_dtb']=hex(uc.reg_read(UC_ARM64_REG_X0))
        outcome['x1_x2_x3']=[uc.reg_read(reg) for reg in [UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3]]
        outcome['entry_pstate']=hex(uc.reg_read(UC_ARM64_REG_PSTATE))
        assert uc.reg_read(UC_ARM64_REG_PSTATE)&0x3c0==0x3c0
        assert uc.reg_read(UC_ARM64_REG_PSTATE)&0xf==pstate&0xf
        uc.emu_stop()
    def halted(uc,pc,size,data):
        outcome['halt_reason']=uc.reg_read(UC_ARM64_REG_X0);uc.emu_stop()
    def maintenance(uc,pc,size,data):
        mnemonic,operands=cache_ops[pc-base]
        if mnemonic=='dc':
            operation=operands.split(',')[0]
            assert operation in counts,operation
            count=counts[operation]
            left=count
            for address,extent in expected_lines:
                n=(extent+line_size-1)//line_size
                if left<n:
                    assert uc.reg_read(UC_ARM64_REG_X0)==address+left*line_size
                    break
                left-=n
            else:raise AssertionError('extra cache line operation')
            if operation=='cvac':assert counts['civac']==total
            if count==0:order.append('first-'+operation)
            counts[operation]+=1
        else:order.append((mnemonic+' '+operands).strip())
    def override_control(uc,pc,size,data):
        if control_override is not None:
            uc.reg_write(UC_ARM64_REG_X11,control_override)
            uc.reg_write(UC_ARM64_REG_PC,pc+4)
    uc.hook_add(UC_HOOK_CODE,reached,begin=0x80000000,end=0x80000000)
    uc.hook_add(UC_HOOK_CODE,halted,begin=base+symbols['halt'],end=base+symbols['halt'])
    for address in cache_ops:
        uc.hook_add(UC_HOOK_CODE,maintenance,begin=base+address,end=base+address)
    for address in control_reads:
        uc.hook_add(UC_HOOK_CODE,override_control,begin=base+address,end=base+address)
    uc.emu_start(base,0,count=450000000)
    if expected_halt is not None:
        assert outcome.get('halt_reason')==expected_halt,outcome
        assert counts=={'civac':0,'cvac':0},counts
    else:
        assert outcome.get('native_entry')=='0x80000000',outcome
        assert outcome['x0_dtb']=='0x82000000' and outcome['x1_x2_x3']==[0,0,0]
        assert counts=={'civac':total,'cvac':total},counts
        assert order[-4:]==['dsb sy','ic iallu','dsb sy','isb'],order[-8:]
        assert bytes(uc.mem_read(0x80000000,len(native)))==native
        assert not any(uc.mem_read(0x80000000+len(native),image_size-len(native)))
        hdr=bytes(uc.mem_read(0x82000000,8));length=struct.unpack_from('>I',hdr,4)[0]
        path=args.output/f'emulated-mainline-v8b-{name}.dtb'
        path.write_bytes(uc.mem_read(0x82000000,length))
        if name=='el1-daif-clear':(args.output/'emulated-mainline-v8b.dtb').write_bytes(path.read_bytes())
        old,new=(Fdt(root/'reports'/('shim-input-v8b-'+name+'.dtb')) if name in live_cases else Fdt(root/'reports/live.dtb')),Fdt(path)
        oldmem=next(p for p,v in old.nodes.items() if v.get('device_type')==b'memory\0')
        newmem=next(p for p,v in new.nodes.items() if v.get('device_type')==b'memory\0')
        assert old.nodes[oldmem]['reg']==new.nodes[newmem]['reg']
        for prop in ['linux,initrd-start','linux,initrd-end']:
            assert old.nodes['/chosen'][prop]==new.nodes['/chosen'][prop]
        trace=new.nodes['/chosen']['xiaomi,bootshim-info'].rstrip(b'\0').decode()
        assert f'base=0x{base:016x}' in trace and f'el=0x{(pstate>>2)&3:016x}' in trace
        assert 'daif=0x00000000000003c0' in trace
        raw=path.read_bytes();rsv=struct.unpack_from('>I',raw,16)[0];reservations=[]
        while True:
            address,size=struct.unpack_from('>QQ',raw,rsv);rsv+=16
            if not address and not size:break
            reservations.append((address,size))
        nomap=[];reserved_count=0;nomap_count=0
        for node,props in new.nodes.items():
            if node.startswith('/reserved-memory/') and 'reg' in props and 'no-map' in props:
                cells=new.cells(props['reg'])
                nomap.extend((((cells[i]<<32)|cells[i+1]),((cells[i+2]<<32)|cells[i+3])) for i in range(0,len(cells),4))
        for node,props in old.nodes.items():
            if node.startswith('/reserved-memory/') and 'reg' in props:
                cells=old.cells(props['reg'])
                for i in range(0,len(cells),4):
                    address=(cells[i]<<32)|cells[i+1];size=(cells[i+2]<<32)|cells[i+3]
                    if size:
                        assert (address,size) in reservations;reserved_count+=1
                        if 'no-map' in props:
                            assert any(address>=a and address+size<=a+n for a,n in nomap);nomap_count+=1
        outcome.update({'runtime_trace':trace,'cache_line_bytes':line_size,'cache_operations':counts,'cache_sequence':order,'firmware_reserved_ranges_preserved':reserved_count,'firmware_no_map_ranges_preserved':nomap_count,'kernel_copy':'byte-identical, BSS tail zero'})
    if name in live_cases:
        assert bytes(uc.mem_read(rd,len(ramdisk)))==ramdisk
        outcome['large_initramfs_preserved_bytes']=len(ramdisk)
    result={'test':name,'load_base':hex(base),'incoming_pstate':hex(pstate),**outcome}
    if control_override is not None:result['control_read']='modeled SCTLR read; actual emulated MMU stays off'
    results.append(result)
    print('PASS:',name,flush=True)
report={'status':'PASS_OFFLINE_ONLY','kernel_not_executed':True,'cache_model_limit':'Unicorn checks instruction execution/order/range coverage, not real cache contents, PoC or external coherent masters','cases':results}
(args.output/'bootshim-v8b-emulation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
