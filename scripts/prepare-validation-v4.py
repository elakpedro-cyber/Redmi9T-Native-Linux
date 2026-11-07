from pathlib import Path

root=Path(__file__).resolve().parents[1]
t=(root/'scripts/validate-v3.py').read_text().replace('v3','v4').replace('V3','V4')
start=t.index("placement=json.loads")
end=t.index("check((root/'reports/bootshim-v4-relocations",start)
t=t[:start]+t[end:]
t=t.replace("binary=Path.home()/'Redmi9T-Native-Linux/initramfs/bin/busybox'", "binary=art/'BusyBox-v4'")
start=t.index("results.append('NOT TESTED:")
end=t.index("text='\\n'.join(results)",start)
t=t[:start]+'''for name,info in json.loads((root/'reports/artifact-manifest-v3.json').read_text()).items():
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
apps=subprocess.check_output(['qemu-aarch64-static',str(binary),'--list']).decode().splitlines()
for app in ['zcat','gunzip','base64','od','hexdump','getty','sh']:
    check(app in apps,'actual ARM64 BusyBox applet: '+app)
sample=bytes(range(256))
proc=subprocess.run(['qemu-aarch64-static','-0','busybox',str(binary),'zcat'],input=gzip.compress(sample),capture_output=True)
check(proc.returncode==0 and proc.stdout==sample,'ARM64 zcat round-trip all 256 byte values')
encoded=subprocess.check_output(['qemu-aarch64-static','-0','busybox',str(binary),'base64'],input=sample)
proc=subprocess.run(['qemu-aarch64-static','-0','busybox',str(binary),'base64','-d'],input=encoded,capture_output=True)
check(proc.returncode==0 and proc.stdout==sample,'ARM64 base64 encode/decode all 256 byte values')
original=(root/'config/init-v3').read_text()
reverted=init.decode().replace('LEMON_INIT_V4_REACHED','LEMON_INIT_V3_REACHED').replace('/sbin/ufs-diagnostics >/run/ufs-diagnostics.log 2>&1 &\\n\\n','')
check(reverted==original,'v3 init retained apart from v4 marker and RAM-only diagnostic startup')
check(subprocess.run(['qemu-aarch64-static',str(binary),'sh','-n',str(root/'config/ufs-diagnostics-v4')]).returncode==0,'UFS diagnostics parsed by actual ARM64 ash')
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
    check(re.search(r'\\b'+symbol+r'$',system,re.M) is not None,'kernel contains '+symbol)
native=(art/'Image-v4').read_bytes();memory_size=struct.unpack_from('<Q',native,16)[0]
check(native[56:60]==b'ARM\\x64' and struct.unpack_from('<Q',native,8)[0]==0,'native ARM64 Image header / zero text_offset')
check(len(native)<=memory_size<=0x2000000,'native Image + BSS fit below unchanged DTB destination')
dt_native=Fdt(art/'sm6115-xiaomi-lemon-v2.dtb')
for path,compatible in [('/soc@0/ufshc@4804000','qcom,ufshc'),('/soc@0/phy@4807000','qcom,sm6115-qmp-ufs-phy')]:
    props=dt_native.nodes[path]
    check(compatible in dt_native.strings(props['compatible']) and props.get('status',b'okay\\0')==b'okay\\0','enabled DT driver match: '+path)
diff=['# Kernel config v3 → v4','', '| Option | v3 | v4 |','|---|---|---|']
for key in sorted(old.keys()|new.keys()):
    a=old.get(key,'n');b=new.get(key,'n')
    if a!=b:diff.append(f'| {key} | {a} | {b} |')
(root/'CONFIG_DIFF_V3_V4.md').write_text('\\n'.join(diff)+'\\n')
results.append('NOT TESTED: v4 physical boot, UFS link training, storage enumeration, partition scan, runtime PM, v4 USB/display, pstore retention')
''' + t[end:]
t=t.replace("'kernel_unchanged':True", "'kernel_unchanged':False")
t=t.replace("'operating-points-v4'", "'operating-points-v2'")
t=t.replace('OFFLINE_VALIDATED_EXPERIMENTAL_SHIM_NOT_DEVICE_TESTED','V4_OFFLINE_VALIDATED_V3_HARDWARE_CONFIRMED')
t=t.replace("['qemu-aarch64-static',str(binary)", "['qemu-aarch64-static','-0','busybox',str(binary)")
(root/'scripts/validate-v4.py').write_text(t,encoding='utf-8',newline='\n')
