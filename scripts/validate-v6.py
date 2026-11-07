from pathlib import Path
import gzip,hashlib,json,re,struct,subprocess
from fdt_audit import Fdt

root=Path(__file__).resolve().parents[1];art=root/'artifacts';results=[]
def check(ok,name):
    assert ok,name
    results.append('PASS: '+name)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def config(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if line.startswith('CONFIG_'))
for version in ['', '-v2','-v3','-v4','-v5']:
    for name,info in json.loads((root/f'reports/artifact-manifest{version}.json').read_text()).items():
        check(sha(art/name)==info['sha256'],'prior artifact unchanged: '+name)
for name,info in json.loads((root/'reports/backup-sha256-before.json').read_text()).items():
    check(sha(root.parent/'platform-tools/Redmi9T_Backup'/name)==info['sha256'],'original backup unchanged: '+name)
snap=root/'snapshots/v4-known-good'
for name,info in json.loads((snap/'MANIFEST.json').read_text()).items():
    check(sha(snap/name.replace('\\','/'))==info['sha256'],'sealed v4 snapshot unchanged: '+name)
old=config(root/'config/linux-v4.config');new=config(root/'config/linux-v6.config')
check(all(new.get(k)=='y' for k,v in old.items() if v=='y'),'all v4 built-in kernel features retained')
for key in ['SCSI','BLK_DEV_SD','SCSI_UFSHCD','SCSI_UFSHCD_PLATFORM','SCSI_UFS_QCOM','PHY_QCOM_QMP_UFS','USB_CONFIGFS_ACM','DRM_SIMPLEDRM','NET','UNIX','INET','PACKET','USB_CONFIGFS_ECM','USB_CONFIGFS_NCM','USB_CONFIGFS_RNDIS']:
    check(new.get('CONFIG_'+key)=='y','v6 builtin: '+key)
check(new.get('CONFIG_DRM_MSM','n')=='n','GPU support not advertised or silently enabled')
diff=['# Kernel configuration v4 to v6','','| Option | v4 | v6 |','|---|---|---|']
for key in sorted(old.keys()|new.keys()):
    a,b=old.get(key,'n'),new.get(key,'n')
    if a!=b:diff.append(f'| {key} | {a} | {b} |')
(root/'CONFIG_DIFF_V4_V6.md').write_text('\n'.join(diff)+'\n')
image=(art/'Image-v6').read_bytes();image_size=struct.unpack_from('<Q',image,16)[0]
check(image[56:60]==b'ARM\x64' and struct.unpack_from('<Q',image,8)[0]==0,'native ARM64 header / text_offset=0')
check(len(image)<=image_size<=0x2000000,'native kernel including BSS fits unchanged destination window')
check((root/'reports/bootshim-v6-relocations.txt').read_text().strip()=='There are no relocations in this file.','shim ELF has no relocations')
shim=(art/'bootshim-v6.Image').read_bytes()
check(shim[56:60]==b'ARM\x64' and struct.unpack_from('<Q',shim,8)[0]==0x80000,'wrapper ARM64 header retained')
check(struct.unpack_from('<Q',shim,16)[0]>=len(shim)+16384,'wrapper memory_size covers NOBITS/stack')
em=json.loads((root/'reports/bootshim-v6-emulation.json').read_text())
check(em['status']=='PASS_OFFLINE_ONLY' and len(em['cases'])==15,'15 ARM64 handoff and guarded-failure cases')
success=[c for c in em['cases'] if 'native_entry' in c]
check(len(success)==8 and all(int(c['entry_pstate'],16)&0x3c0==0x3c0 for c in success),'eight entries at Linux with DAIF masked')
check(all(c['cache_operations']['civac']==c['cache_operations']['cvac']>0 for c in success),'Image/DTB cache maintenance instruction coverage')
large=[c for c in success if 'large_initramfs_preserved_bytes' in c]
check(len(large)==3 and all(c['large_initramfs_preserved_bytes']==(art/'initramfs-v6.cpio.gz').stat().st_size for c in large),'full large initramfs preserved at three ABL-modeled layouts with live-v4 DT input')
check((root/'reports/v6-unpacked/dtb').read_bytes()==(root/'reports/stock-boot/dtb').read_bytes(),'ABL-facing DTB remains exact stock')
p=subprocess.run(['fdtoverlay','-i',str(root/'reports/v6-unpacked/dtb'),'-o',str(root/'reports/v6-abl-merged.dtb'),str(root/'reports/stock-overlay-0.dtbo')],capture_output=True)
check(p.returncode==0,'original stock overlay #0 applies without DTBO changes')
for name in ['v6-abl-merged','emulated-mainline-v6','live-v4']:
    p=subprocess.run(['dtc','-I','dtb','-O','dts',str(root/f'reports/{name}.dtb')],capture_output=True)
    (root/f'reports/{name}.dts').write_bytes(p.stdout);(root/f'reports/{name}-dtc-warnings.txt').write_bytes(p.stderr)
    check(p.returncode==0,'dtc reads '+name+' (warnings retained)')
dt=Fdt(root/'reports/emulated-mainline-v6.dtb')
spec={'clocks':'#clock-cells','resets':'#reset-cells','phys':'#phy-cells','iommus':'#iommu-cells','power-domains':'#power-domain-cells','interconnects':'#interconnect-cells','thermal-sensors':'#thermal-sensor-cells','cooling-device':'#cooling-cells','interrupts-extended':'#interrupt-cells','sound-dai':'#sound-dai-cells'}
count=0
for path,props in dt.nodes.items():
    for key,data in props.items():
        cp=spec.get(key)
        if key=='gpios' or key.endswith('-gpios'):cp='#gpio-cells'
        single=key in ['interrupt-parent','remote-endpoint','memory-region','nvmem-cells','operating-points-v2'] or key.endswith('-supply') or re.fullmatch(r'pinctrl-\d+',key)
        if not cp and not single:continue
        cells=dt.cells(data);i=0
        while i<len(cells):
            handle=cells[i];i+=1;check(handle in dt.phandles,'phandle resolves '+path+':'+key)
            n=dt.cells(dt.nodes[dt.phandles[handle]][cp])[0] if cp else 0
            assert i+n<=len(cells);i+=n;count+=1
check(count>0,f'{count} standard DT provider references checked')
cpio=gzip.decompress((art/'initramfs-v6.cpio.gz').read_bytes());entries={};off=0
while cpio[off:off+6]==b'070701':
    fields=[int(cpio[off+6+i*8:off+14+i*8],16) for i in range(13)]
    start=off+110;name=cpio[start:start+fields[11]-1].decode().removeprefix('./');start=(start+fields[11]+3)&~3
    assert name not in entries,name
    entries[name]=(fields,cpio[start:start+fields[6]]);off=(start+fields[6]+3)&~3
    if name=='TRAILER!!!':break
check('TRAILER!!!' in entries,'newc archive complete')
check(not any(f[1]&0o170000==0o060000 for f,p in entries.values()),'no block devices packaged in RAM rootfs')
for path,source in [('init','init-v6'),('etc/inittab','inittab-v6'),('usr/local/sbin/lemon-root-shell','lemon-root-shell-v6'),('usr/local/sbin/lemon-diagnostics','lemon-diagnostics-v6'),('etc/init.d/lemon-health','lemon-health-v6')]:
    check(entries[path][1]==(root/'config'/source).read_bytes(),'packaged file matches source: '+path)
    if path!='etc/inittab':check(bool(entries[path][0][1]&0o111),'executable '+path)
check(entries['rescue/busybox'][1]==(art/'BusyBox-v4').read_bytes(),'known-good static v4 BusyBox preserved as rescue')
check(entries['dev/console'][0][9:11]==[5,1],'console character device 5:1')
check(entries['etc/lemon/usbnet-mode'][1].strip()==b'ncm','v6 USB mode NCM with ACM')
check(not any(line.strip() and not line.startswith(b'#') for line in entries['etc/fstab'][1].splitlines()),'fstab contains no mounts or swap')
runlevels=[n for n in entries if n.startswith('etc/runlevels/') and entries[n][0][1]&0o170000!=0o040000]
check(set(runlevels)=={'etc/runlevels/default/lemon-health','etc/runlevels/default/lemon-net','etc/runlevels/default/lemon-sshd'},'only health, USB IP and SSH services enabled')
check(entries['root/.ssh/authorized_keys'][1]==(root/'config/ssh-authorized-keys-v6').read_bytes(),'authorized public key matches intended Windows user key')
check(not any('dropbear_' in n and n.endswith('_host_key') for n in entries),'no shared SSH host private keys')
check(b'LEMON_INIT_V6_REACHED' in entries['init'][1] and b'exec /sbin/init' in entries['init'][1],'early marker and PID1 handoff to Alpine init present')
init=entries['init'][1].decode()
shell=entries['usr/local/sbin/lemon-root-shell'][1].decode()
check(init.index(') >/run/usb-setup.log 2>&1 &')<init.index('exec /sbin/init'),'USB getty starts independently before Alpine init/OpenRC')
check(shell.startswith('#!/rescue/busybox sh\n') and 'exec /rescue/busybox sh -i' in shell and '/bin/ash' not in shell,'USB root shell has no Alpine loader or profile dependency')
check('/run/ufs-stat-initial.txt' in init and init.index('/run/ufs-stat-initial.txt')<init.index('exec /sbin/init'),'block counters captured before OpenRC')
check(set(re.findall(r'^mount -t (\S+)',init,re.M))<={'devtmpfs','proc','sysfs','tmpfs','devpts','configfs','pstore'},'early init mounts only virtual filesystems')
startup='\n'.join(entries[p][1].decode() for p in ['init','etc/inittab','usr/local/sbin/lemon-root-shell','usr/local/sbin/lemon-diagnostics','etc/init.d/lemon-health','etc/init.d/lemon-net','etc/init.d/lemon-sshd','usr/local/sbin/lemon-usb-gadget'])
check(re.search(r'(?m)^\s*(?:/\S*/)?(?:swapon|mkswap|mkfs(?:\.\w+)?|sfdisk|sgdisk|parted|dd)\b',startup) is None,'reviewed startup has no swap, partition or raw-write commands')
functional=json.loads((root/'reports/v6-functional-tests.json').read_text())
check(functional['status']=='PASS' and len(functional['cases'])==7,'NCM model, static shell, ARM64 SSH auth and SCP tests')
check(entries['usr/lib/ssh/sftp-server'][1][:4]==b'ELF','SFTP server packaged for modern Windows SCP')
for path,source in [('usr/local/sbin/lemon-usb-gadget','lemon-usb-gadget-v6'),('etc/init.d/lemon-net','lemon-net-v6'),('etc/init.d/lemon-sshd','lemon-sshd-v6')]:
    check(entries[path][1]==(root/'config'/source).read_bytes(),'packaged v6 service: '+path)
    check(bool(entries[path][0][1]&0o111),'executable v6 service: '+path)
sshd=entries['etc/init.d/lemon-sshd'][1].decode()
check('-F -E -s -j -k' in sshd and '-p 192.168.77.2:22' in sshd and 'need lemon-net' in sshd,'SSH password disabled, USB-address-only bind and network dependency')
check('run/dropbear/host_ed25519' not in entries,'runtime SSH private key not packaged')
check('/run/dropbear/host_ed25519' in sshd and '/run/ssh-hostkey.txt' in sshd,'unique runtime RAM host key and COM fingerprint path')
check(entries['root/.ssh/authorized_keys'][0][1]&0o777==0o600 and entries['root/.ssh'][0][1]&0o777==0o700,'SSH key directory/file permissions')
check((art/'Image-v6').read_bytes()==(art/'Image-v5').read_bytes(),'v5 hardware-confirmed kernel unchanged')
check((art/'bootshim-v6.Image').read_bytes()==(art/'bootshim-v5.Image').read_bytes(),'v5 hardware-confirmed wrapper unchanged')
for name,info in json.loads((root/'snapshots/v5-known-good/MANIFEST.json').read_text()).items():
    check(sha(root/'snapshots/v5-known-good'/name)==info['sha256'],'working v5 snapshot unchanged: '+name)
for path in ['bin/busybox','sbin/openrc','sbin/apk','sbin/ip','bin/lsblk','usr/sbin/dropbear','usr/bin/curl']:
    payload=entries[path][1]
    check(payload[:4]==b'\x7fELF' and struct.unpack_from('<H',payload,18)[0]==183,'ARM64 ELF '+path)
check('PASS' in (root/'reports/v6-functional-tests.log').read_text(),'actual ARM64 SSH functional execution recorded')
check(json.loads((root/'reports/pmaports-v5-check.json').read_text())['schema']=='PASS','device package schema/parser/helper checks')
header=(art/'boot-linux-test-v6.img').read_bytes()[:1660]
check(header[:8]==b'ANDROID!' and struct.unpack_from('<I',header,36)[0]==4096 and struct.unpack_from('<I',header,40)[0]==2,'Android header v2/page4096')
check(struct.unpack_from('<I',header,1644)[0]==1660 and struct.unpack_from('<Q',header,1652)[0]==0x1f00000,'original header length and DTB address field')
check((art/'boot-linux-test-v6.img').stat().st_size<134217728,'v6 fits existing 128 MiB boot partition')
for name,expected in [('kernel','bootshim-v6.Image.gz'),('ramdisk','initramfs-v6.cpio.gz')]:
    check((root/'reports/v6-unpacked'/name).read_bytes()==(art/expected).read_bytes(),'AOSP unpack exact '+name)
for name,info in json.loads((root/'reports/artifact-manifest-v6.json').read_text()).items():
    check(sha(art/name)==info['sha256'],'artifact manifest SHA '+name)
results.append('NOT TESTED: v6 physical boot, Windows UsbNcm binding, exact COM number, NCM traffic, regression UFS/ACM, SSH over real USB. Offline SSH used WSL loopback only.')
(root/'reports/v6-validation.txt').write_text('\n'.join(results)+'\n')
(root/'reports/v6-status.json').write_text(json.dumps({'status':'V6_OFFLINE_VALIDATED_V5_HARDWARE_CONFIRMED','v6_phone_boot_run':False,'phone_reboot_or_flash_run':False,'usb_network_default':'CDC NCM + ACM','rootfs':'Alpine 3.24.4 ARM64 in initramfs; initial local pmaports port, not full postmarketOS distribution','checks':results},indent=2)+'\n')
print('\n'.join(results[-12:]))
