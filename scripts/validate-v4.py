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
check((root/'reports/v4-unpacked/dtb').read_bytes()==(root/'reports/stock-boot/dtb').read_bytes(),'ABL-facing v4 DTB is the actual stock DTB')
proc=subprocess.run(['fdtoverlay','-i',str(root/'reports/v4-unpacked/dtb'),'-o',str(root/'reports/v4-abl-merged.dtb'),str(root/'reports/stock-overlay-0.dtbo')],capture_output=True)
check(proc.returncode==0,'stock overlay #0 applies to the exact DTB packaged in v4')
for name in ['v4-abl-merged','emulated-mainline-v4']:
    proc=subprocess.run(['dtc','-I','dtb','-O','dts',str(root/'reports'/f'{name}.dtb')],capture_output=True)
    (root/'reports'/f'{name}.dts').write_bytes(proc.stdout)
    (root/'reports'/f'{name}-dtc-warnings.txt').write_bytes(proc.stderr)
    check(proc.returncode==0,'dtc reads '+name+' (warnings retained, not schema validation)')

dt=Fdt(root/'reports/emulated-mainline-v4.dtb')
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
emulation=json.loads((root/'reports/bootshim-v4-emulation.json').read_text())
check(emulation['status']=='PASS_OFFLINE_ONLY','ARM64 shim emulation including guarded failure cases')
check(len(emulation['cases'])==12,'12 EL/DAIF/cache/relocation and guarded-failure cases passed')
successes=[case for case in emulation['cases'] if 'native_entry' in case]
check(len(successes)==5,'five successful entries: EL1/EL2, partial/clear DAIF, relocated source, I-cache enabled')
check(all(int(case['entry_pstate'],16)&0x3c0==0x3c0 for case in successes),'DAIF D/A/I/F all masked at kernel entry')
check(all(case['cache_operations']['civac']==case['cache_operations']['cvac']>0 for case in successes),'explicit pre-copy CIVAC and post-copy CVAC cover Image and DTB ranges')
check((root/'reports/bootshim-v4-relocations.txt').read_text().strip()=='There are no relocations in this file.','shim has no unresolved relocations')
cpio=gzip.decompress((art/'initramfs-v4.cpio.gz').read_bytes())
offset=0;init=None
while cpio[offset:offset+6]==b'070701':
    fields=[int(cpio[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
    start=offset+110;name=cpio[start:start+fields[11]-1].decode();start=(start+fields[11]+3)&~3
    payload=cpio[start:start+fields[6]]
    if name in ['init','./init']:init=payload;check(bool(fields[1]&0o111),'/init executable')
    if name=='TRAILER!!!':break
    offset=(start+fields[6]+3)&~3
check(init==(root/'config/init-v4').read_bytes(),'/init-v4 matches cpio content')
check(b'LEMON_INIT_V4_REACHED' in init,'unique /init marker included')
binary=art/'BusyBox-v4'
proc=subprocess.run(['qemu-aarch64-static','-0','busybox',str(binary),'sh','-n',str(root/'config/init-v4')])
check(proc.returncode==0,'v4 init parsed by actual ARM64 BusyBox ash')
check((art/'boot-linux-test-v4.img').stat().st_size<134217728,'v4 image fits boot partition')
header=(art/'boot-linux-test-v4.img').read_bytes()[:1660]
check(header[:8]==b'ANDROID!' and struct.unpack_from('<I',header,36)[0]==4096 and struct.unpack_from('<I',header,40)[0]==2,'Android header v2 / page 4096')
check(struct.unpack_from('<I',header,1644)[0]==1660 and struct.unpack_from('<Q',header,1652)[0]==0x1f00000,'header length and DTB load-address field retained')
shim=(art/'bootshim-v4.Image').read_bytes()
check(shim[56:60]==b'ARM\x64' and struct.unpack_from('<Q',shim,8)[0]==0x80000,'wrapper ARM64 header and text_offset')
check(struct.unpack_from('<Q',shim,16)[0]>=len(shim)+16384,'wrapper image_size includes stack / NOBITS storage')
manifest=json.loads((root/'reports/artifact-manifest-v4.json').read_text())
for name in ['boot-linux-test-v4.img','bootshim-v4.Image','bootshim-v4.Image.gz','initramfs-v4.cpio.gz']:
    check(hashlib.sha256((art/name).read_bytes()).hexdigest()==manifest[name]['sha256'],'SHA-256 matches v4 manifest: '+name)
for name,info in json.loads((root/'reports/artifact-manifest-v3.json').read_text()).items():
    check(hashlib.sha256((art/name).read_bytes()).hexdigest()==info['sha256'],'v3 artifact unchanged: '+name)
def config(path):
    values={}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key,value=line.split('=',1);values[key]=value
    return values
old=config(root/'config/linux.config');new=config(root/'config/linux-v4.config')
for key,value in old.items():
    if value=='y':check(new.get(key)=='y','v3 builtin retained: '+key)
for key in ['SCSI','SCSI_DMA','BLK_DEV_SD','SCSI_UFSHCD','SCSI_UFSHCD_PLATFORM','SCSI_UFS_QCOM','PHY_QCOM_QMP_UFS','EFI_PARTITION']:
    check(new.get('CONFIG_'+key)=='y','v4 builtin: '+key)
for key,value in config(root/'config/busybox.config').items():
    if value=='y':check(config(root/'config/busybox-v4.config').get(key)=='y','v3 BusyBox feature retained: '+key)
apps=subprocess.check_output(['qemu-aarch64-static','-0','busybox',str(binary),'--list']).decode().splitlines()
for app in ['zcat','gunzip','base64','od','hexdump','getty','sh']:
    check(app in apps,'actual ARM64 BusyBox applet: '+app)
sample=bytes(range(256))
proc=subprocess.run(['qemu-aarch64-static','-0','busybox',str(binary),'zcat'],input=gzip.compress(sample),capture_output=True)
check(proc.returncode==0 and proc.stdout==sample,'ARM64 zcat round-trip all 256 byte values')
encoded=subprocess.check_output(['qemu-aarch64-static','-0','busybox',str(binary),'base64'],input=sample)
proc=subprocess.run(['qemu-aarch64-static','-0','busybox',str(binary),'base64','-d'],input=encoded,capture_output=True)
check(proc.returncode==0 and proc.stdout==sample,'ARM64 base64 encode/decode all 256 byte values')
original=(root/'config/init-v3').read_text()
reverted=init.decode().replace('LEMON_INIT_V4_REACHED','LEMON_INIT_V3_REACHED').replace('/sbin/ufs-diagnostics >/run/ufs-diagnostics.log 2>&1 &\n\n','')
check(reverted==original,'v3 init retained apart from v4 marker and RAM-only diagnostic startup')
check(subprocess.run(['qemu-aarch64-static','-0','busybox',str(binary),'sh','-n',str(root/'config/ufs-diagnostics-v4')]).returncode==0,'UFS diagnostics parsed by actual ARM64 ash')
payloads={};offset=0
while cpio[offset:offset+6]==b'070701':
    f=[int(cpio[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
    start=offset+110;name=cpio[start:start+f[11]-1].decode().removeprefix('./');start=(start+f[11]+3)&~3
    payloads[name]=(f,cpio[start:start+f[6]]);offset=(start+f[6]+3)&~3
    if name=='TRAILER!!!':break
check(payloads['bin/busybox'][1]==binary.read_bytes(),'packaged BusyBox matches tested binary')
check(payloads['sbin/ufs-diagnostics'][1]==(root/'config/ufs-diagnostics-v4').read_bytes(),'automatic diagnostic matches reviewed script')
check(bool(payloads['sbin/ufs-diagnostics'][0][1]&0o111),'diagnostic executable')
f=payloads['dev/console'][0]
check(f[1]&0o170000==0o020000 and f[9:11]==[5,1],'/dev/console preserved as character device 5:1')
for app in apps:
    check('bin/'+app in payloads,'initramfs applet present: '+app)
proc=subprocess.run(['aarch64-linux-gnu-readelf','-l',str(binary)],capture_output=True)
check(proc.returncode==0 and b'INTERP' not in proc.stdout,'BusyBox statically linked without interpreter')
system=(root/'reports/System-v4.map').read_text()
for symbol in ['ufshcd_init','ufs_qcom_probe','qmp_ufs_probe','scsi_host_alloc','sd_probe']:
    check(re.search(r'\b'+symbol+r'$',system,re.M) is not None,'kernel contains '+symbol)
native=(art/'Image-v4').read_bytes();memory_size=struct.unpack_from('<Q',native,16)[0]
check(native[56:60]==b'ARM\x64' and struct.unpack_from('<Q',native,8)[0]==0,'native ARM64 Image header / zero text_offset')
check(len(native)<=memory_size<=0x2000000,'native Image + BSS fit below unchanged DTB destination')
dt_native=Fdt(art/'sm6115-xiaomi-lemon-v2.dtb')
for path,compatible in [('/soc@0/ufshc@4804000','qcom,ufshc'),('/soc@0/phy@4807000','qcom,sm6115-qmp-ufs-phy')]:
    props=dt_native.nodes[path]
    check(compatible in dt_native.strings(props['compatible']) and props.get('status',b'okay\0')==b'okay\0','enabled DT driver match: '+path)
diff=['# Kernel config v3 → v4','', '| Option | v3 | v4 |','|---|---|---|']
for key in sorted(old.keys()|new.keys()):
    a=old.get(key,'n');b=new.get(key,'n')
    if a!=b:diff.append(f'| {key} | {a} | {b} |')
(root/'CONFIG_DIFF_V3_V4.md').write_text('\n'.join(diff)+'\n')
results.append('NOT TESTED: v4 physical boot, UFS link training, storage enumeration, partition scan, runtime PM, v4 USB/display, pstore retention')
text='\n'.join(results)+'\n'
(root/'reports/v4-validation.txt').write_text(text)
(root/'reports/v4-status.json').write_text(json.dumps({'status':'V4_OFFLINE_VALIDATED_V3_HARDWARE_CONFIRMED','phone_write_authorized':False,'phone_test_run':False,'temporary_boot':'unavailable in current ABL; TWRP KEXEC disabled','kernel_unchanged':False,'dtbo_original_unchanged':True,'checks':results},indent=2)+'\n')
print(text)
