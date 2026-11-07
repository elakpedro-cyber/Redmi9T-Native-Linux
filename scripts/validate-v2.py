from pathlib import Path
import gzip
import hashlib
import json
import re
import struct
import subprocess
from fdt_audit import Fdt

root=Path(__file__).resolve().parents[1]
art=root/'artifacts'
results=[]
def check(ok,text):
    assert ok,text
    results.append('PASS: '+text)

baseline=json.loads((root/'reports/artifact-manifest.json').read_text())
for name,info in baseline.items():
    check(hashlib.sha256((art/name).read_bytes()).hexdigest()==info['sha256'],'v1 artifact unchanged: '+name)
backup=json.loads((root/'reports/backup-sha256-before.json').read_text())
for name,info in backup.items():
    check(hashlib.sha256((root.parent/'platform-tools/Redmi9T_Backup'/name).read_bytes()).hexdigest()==info['sha256'],'backup unchanged: '+name)
check((root/'reports/v2-unpacked/dtb').read_bytes()==(root/'reports/stock-boot/dtb').read_bytes(),'ABL-facing v2 DTB is the actual stock DTB')
proc=subprocess.run(['fdtoverlay','-i',str(root/'reports/v2-unpacked/dtb'),'-o',str(root/'reports/v2-abl-merged.dtb'),str(root/'reports/stock-overlay-0.dtbo')],capture_output=True)
check(proc.returncode==0,'stock overlay #0 applies to the exact DTB packaged in v2')
for name in ['v2-abl-merged','emulated-mainline-v2']:
    proc=subprocess.run(['dtc','-I','dtb','-O','dts',str(root/'reports'/f'{name}.dtb')],capture_output=True)
    (root/'reports'/f'{name}.dts').write_bytes(proc.stdout)
    (root/'reports'/f'{name}-dtc-warnings.txt').write_bytes(proc.stderr)
    check(proc.returncode==0,'dtc reads '+name+' (warnings retained, not schema validation)')

dt=Fdt(root/'reports/emulated-mainline-v2.dtb')
spec={'clocks':'#clock-cells','resets':'#reset-cells','power-domains':'#power-domain-cells','phys':'#phy-cells','iommus':'#iommu-cells','interconnects':'#interconnect-cells','thermal-sensors':'#thermal-sensor-cells','cooling-device':'#cooling-cells','interrupts-extended':'#interrupt-cells','sound-dai':'#sound-dai-cells'}
singles={'interrupt-parent','remote-endpoint','memory-region','nvmem-cells','operating-points-v2'}
references=0
for node,props in dt.nodes.items():
    for name,raw in props.items():
        cellprop=spec.get(name)
        if name=='gpios' or name.endswith('-gpios'):cellprop='#gpio-cells'
        single=name in singles or name.endswith('-supply') or re.fullmatch(r'pinctrl-\d+',name)
        if not cellprop and not single:continue
        assert len(raw)%4==0,(node,name)
        cells=dt.cells(raw);i=0
        while i<len(cells):
            handle=cells[i];i+=1
            assert handle in dt.phandles,(node,name,hex(handle))
            provider=dt.nodes[dt.phandles[handle]]
            args=dt.cells(provider[cellprop])[0] if cellprop else 0
            assert i+args<=len(cells),(node,name)
            i+=args;references+=1
check(references>0,f'{references} standard mainline phandle/provider references resolve')
ramoops=dt.nodes['/reserved-memory/ramoops@64000000']
check('ecc-size' not in ramoops,'ramoops ECC matches existing TWRP (disabled)')
emulation=json.loads((root/'reports/bootshim-emulation.json').read_text())
check(emulation['status']=='PASS_OFFLINE_ONLY','ARM64 shim emulation including guarded failure cases')
check((root/'reports/bootshim-relocations.txt').read_text().strip()=='There are no relocations in this file.','shim has no unresolved relocations')
cpio=gzip.decompress((art/'initramfs-v2.cpio.gz').read_bytes())
offset=0;init=None
while cpio[offset:offset+6]==b'070701':
    fields=[int(cpio[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
    start=offset+110;name=cpio[start:start+fields[11]-1].decode();start=(start+fields[11]+3)&~3
    payload=cpio[start:start+fields[6]]
    if name in ['init','./init']:init=payload;check(bool(fields[1]&0o111),'/init executable')
    if name=='TRAILER!!!':break
    offset=(start+fields[6]+3)&~3
check(init==(root/'config/init-v2').read_bytes(),'/init-v2 matches cpio content')
check(b'LEMON_INIT_V2_REACHED' in init,'unique /init marker included')
binary=Path.home()/'Redmi9T-Native-Linux/initramfs/bin/busybox'
proc=subprocess.run(['qemu-aarch64-static',str(binary),'sh','-n',str(root/'config/init-v2')])
check(proc.returncode==0,'v2 init parsed by actual ARM64 BusyBox ash')
check((art/'boot-linux-test-v2.img').stat().st_size<134217728,'v2 image fits boot partition')
results.append('NOT TESTED: ABL acceptance/AVB, actual entry EL/cache state, kernel execution, /init, USB, display, pstore retention')
text='\n'.join(results)+'\n'
(root/'reports/v2-validation.txt').write_text(text)
(root/'reports/v2-status.json').write_text(json.dumps({'status':'OFFLINE_VALIDATED_EXPERIMENTAL_SHIM_NOT_DEVICE_TESTED','phone_write_authorized':False,'phone_test_run':False,'temporary_boot':'unavailable in current ABL; TWRP KEXEC disabled','kernel_unchanged':True,'dtbo_original_unchanged':True,'checks':results},indent=2)+'\n')
print(text)
