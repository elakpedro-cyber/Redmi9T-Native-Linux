from pathlib import Path
root=Path(__file__).resolve().parents[1]
t=(root/'scripts/emulate-shim-v5.py').read_text()
t=t.replace('results=[]', '''placement=json.loads((root/'reports/abl-v5-placement-emulation.json').read_text())
live_cases={}
for case in placement['cases']:
    name='large-initrd-'+case['scenario']
    live_cases[name]=case['load_addresses']
    cases.append((name,int(case['load_addresses']['kernel'],16),0x005,None,None))
results=[]''')
t=t.replace('    uc.mem_write(0x43000000,blob)\n    uc.reg_write(UC_ARM64_REG_X0,0x43000000)', '''    incoming_addr=0x43000000
    if name in live_cases:
        addresses=live_cases[name]
        blob=(root/'reports'/('shim-input-v5-'+name+'.dtb')).read_bytes()
        incoming_addr=int(addresses['dtb'],16)
        rd=int(addresses['ramdisk'],16)
        ramdisk=(root/'artifacts/initramfs-v5.cpio.gz').read_bytes()
        uc.mem_write(rd,ramdisk)
    uc.mem_write(incoming_addr,blob)
    uc.reg_write(UC_ARM64_REG_X0,incoming_addr)''')
t=t.replace("    result={'test':name", "    if name in live_cases:\n        assert bytes(uc.mem_read(rd,len(ramdisk)))==ramdisk\n        outcome['large_initramfs_preserved_bytes']=len(ramdisk)\n    result={'test':name")
t=t.replace("old,new=Fdt(root/'reports/live.dtb'),Fdt(path)", "old,new=(Fdt(root/'reports'/('shim-input-v5-'+name+'.dtb')) if name in live_cases else Fdt(root/'reports/live.dtb')),Fdt(path)")
(root/'scripts/emulate-shim-v5.py').write_text(t,newline='\n')
