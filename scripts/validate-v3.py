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
for name,info in json.loads((root/'reports/artifact-manifest-v2.json').read_text()).items():
    check(hashlib.sha256((art/name).read_bytes()).hexdigest()==info['sha256'],'v2 artifact unchanged: '+name)
backup=json.loads((root/'reports/backup-sha256-before.json').read_text())
for name,info in backup.items():
    check(hashlib.sha256((root.parent/'platform-tools/Redmi9T_Backup'/name).read_bytes()).hexdigest()==info['sha256'],'backup unchanged: '+name)
check((root/'reports/v3-unpacked/dtb').read_bytes()==(root/'reports/stock-boot/dtb').read_bytes(),'ABL-facing v3 DTB is the actual stock DTB')
proc=subprocess.run(['fdtoverlay','-i',str(root/'reports/v3-unpacked/dtb'),'-o',str(root/'reports/v3-abl-merged.dtb'),str(root/'reports/stock-overlay-0.dtbo')],capture_output=True)
check(proc.returncode==0,'stock overlay #0 applies to the exact DTB packaged in v3')
for name in ['v3-abl-merged','emulated-mainline-v3']:
    proc=subprocess.run(['dtc','-I','dtb','-O','dts',str(root/'reports'/f'{name}.dtb')],capture_output=True)
    (root/'reports'/f'{name}.dts').write_bytes(proc.stdout)
    (root/'reports'/f'{name}-dtc-warnings.txt').write_bytes(proc.stderr)
    check(proc.returncode==0,'dtc reads '+name+' (warnings retained, not schema validation)')

dt=Fdt(root/'reports/emulated-mainline-v3.dtb')
spec={'clocks':'#clock-cells','resets':'#reset-cells','power-domains':'#power-domain-cells','phys':'#phy-cells','iommus':'#iommu-cells','interconnects':'#interconnect-cells','thermal-sensors':'#thermal-sensor-cells','cooling-device':'#cooling-cells','interrupts-extended':'#interrupt-cells','sound-dai':'#sound-dai-cells'}
singles={'interrupt-parent','remote-endpoint','memory-region','nvmem-cells','operating-points-v3'}
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
emulation=json.loads((root/'reports/bootshim-v3-emulation.json').read_text())
check(emulation['status']=='PASS_OFFLINE_ONLY','ARM64 shim emulation including guarded failure cases')
check(len(emulation['cases'])==12,'12 EL/DAIF/cache/relocation and guarded-failure cases passed')
successes=[case for case in emulation['cases'] if 'native_entry' in case]
check(len(successes)==5,'five successful entries: EL1/EL2, partial/clear DAIF, relocated source, I-cache enabled')
check(all(int(case['entry_pstate'],16)&0x3c0==0x3c0 for case in successes),'DAIF D/A/I/F all masked at kernel entry')
check(all(case['cache_operations']['civac']==case['cache_operations']['cvac']>0 for case in successes),'explicit pre-copy CIVAC and post-copy CVAC cover Image and DTB ranges')
placement=json.loads((root/'reports/abl-v3-placement-emulation.json').read_text())
check(len(placement['cases'])==3 and placement['runtime_uefi_values_known'] is False,'actual ABL address calculations checked for fallback and two modeled UEFI bases; real base remains unknown')
check((root/'reports/bootshim-v3-relocations.txt').read_text().strip()=='There are no relocations in this file.','shim has no unresolved relocations')
cpio=gzip.decompress((art/'initramfs-v3.cpio.gz').read_bytes())
offset=0;init=None
while cpio[offset:offset+6]==b'070701':
    fields=[int(cpio[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
    start=offset+110;name=cpio[start:start+fields[11]-1].decode();start=(start+fields[11]+3)&~3
    payload=cpio[start:start+fields[6]]
    if name in ['init','./init']:init=payload;check(bool(fields[1]&0o111),'/init executable')
    if name=='TRAILER!!!':break
    offset=(start+fields[6]+3)&~3
check(init==(root/'config/init-v3').read_bytes(),'/init-v3 matches cpio content')
check(b'LEMON_INIT_V3_REACHED' in init,'unique /init marker included')
binary=Path.home()/'Redmi9T-Native-Linux/initramfs/bin/busybox'
proc=subprocess.run(['qemu-aarch64-static',str(binary),'sh','-n',str(root/'config/init-v3')])
check(proc.returncode==0,'v3 init parsed by actual ARM64 BusyBox ash')
check((art/'boot-linux-test-v3.img').stat().st_size<134217728,'v3 image fits boot partition')
header=(art/'boot-linux-test-v3.img').read_bytes()[:1660]
check(header[:8]==b'ANDROID!' and struct.unpack_from('<I',header,36)[0]==4096 and struct.unpack_from('<I',header,40)[0]==2,'Android header v2 / page 4096')
check(struct.unpack_from('<I',header,1644)[0]==1660 and struct.unpack_from('<Q',header,1652)[0]==0x1f00000,'header length and DTB load-address field retained')
shim=(art/'bootshim-v3.Image').read_bytes()
check(shim[56:60]==b'ARM\x64' and struct.unpack_from('<Q',shim,8)[0]==0x80000,'wrapper ARM64 header and text_offset')
check(struct.unpack_from('<Q',shim,16)[0]>=len(shim)+16384,'wrapper image_size includes stack / NOBITS storage')
manifest=json.loads((root/'reports/artifact-manifest-v3.json').read_text())
for name in ['boot-linux-test-v3.img','bootshim-v3.Image','bootshim-v3.Image.gz','initramfs-v3.cpio.gz']:
    check(hashlib.sha256((art/name).read_bytes()).hexdigest()==manifest[name]['sha256'],'SHA-256 matches v3 manifest: '+name)
results.append('NOT TESTED: ABL acceptance/AVB, real KernelBaseAddr/KernelSize, real PoC/system-cache/coherency and higher-EL configuration, kernel execution, /init, USB, display, pstore retention')
text='\n'.join(results)+'\n'
(root/'reports/v3-validation.txt').write_text(text)
(root/'reports/v3-status.json').write_text(json.dumps({'status':'OFFLINE_VALIDATED_EXPERIMENTAL_SHIM_NOT_DEVICE_TESTED','phone_write_authorized':False,'phone_test_run':False,'temporary_boot':'unavailable in current ABL; TWRP KEXEC disabled','kernel_unchanged':True,'dtbo_original_unchanged':True,'checks':results},indent=2)+'\n')
print(text)
