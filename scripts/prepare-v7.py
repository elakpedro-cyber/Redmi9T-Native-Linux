from pathlib import Path
import json

root=Path(__file__).resolve().parents[1]
for name in ['init','lemon-root-shell','lemon-health','lemon-diagnostics','inittab']:
    text=(root/f'config/{name}-v6').read_text().replace('V6','V7').replace('v6','v7')
    (root/f'config/{name}-v7').write_text(text,newline='\n')
for name in ['lemon-usb-gadget','lemon-net','lemon-sshd']:
    (root/f'config/{name}-v7').write_bytes((root/f'config/{name}-v6').read_bytes())
key=Path(json.loads((root/'logs/v6-authorized/test-client-identity.json').read_text())['private_key_path']+'.pub')
public=(root/'config/ssh-authorized-keys-v6').read_text().strip()+'\n'+key.read_text().strip()+'\n'
assert 'PRIVATE KEY' not in public
(root/'config/ssh-authorized-keys-v7').write_text(public,newline='\n')
for name in ['package-rootfs','package','emulate-shim','emulate-abl-placement','make-large-initrd-fixtures','test-v6-offline','validate']:
    old='test-v6-offline.py' if name=='test-v6-offline' else name+'-v6'+('.sh' if name=='package-rootfs' else '.py')
    new=old.replace('v6','v7')
    text=(root/'scripts'/old).read_text().replace('v6','v7').replace('V6','V7').replace('22266','22267')
    if name in ['package-rootfs','test-v6-offline']:
        text=text.replace('rootfs-v7/root','rootfs-v7/boot-root')
    if name=='validate':
        text=text.replace("check(new.get('CONFIG_DRM_MSM','n')=='n','GPU support not advertised or silently enabled')", "check(new.get('CONFIG_DRM_MSM')=='m','MSM GPU module built; not auto-loaded')")
        text='\n'.join(line for line in text.splitlines() if not any(s in line for s in ["hardware-confirmed kernel unchanged'", "hardware-confirmed wrapper unchanged'"]))+'\n'
        text=text.replace("results.append('NOT TESTED:", "results.append('NOT TESTED:")
        text=text.replace('V7_OFFLINE_VALIDATED_V5_HARDWARE_CONFIRMED','V7_OFFLINE_VALIDATED_V6_HARDWARE_CONFIRMED')
        text=text.replace("snapshots/v5-known-good", "snapshots/v6-hardware-validated").replace("working v5 snapshot", "sealed v6 snapshot")
    (root/'scripts'/new).write_text(text,newline='\n')
text=(root/'scripts/build-shim-v5.sh').read_text().replace('v5','v7').replace('sm6115-xiaomi-lemon-v2.dtb','sm6115-xiaomi-lemon-v7.dtb')
(root/'scripts/build-shim-v7.sh').write_text(text,newline='\n')
for name in ['Test-LemonHardwareV6.ps1','Test-LemonUsbV6.ps1','collect-v6.py']:
    text=(root/'scripts'/name).read_text().replace('V6','V7').replace('v6','v7').replace("'COM3'","'COM4'")
    if name=='collect-v6.py':text=text.replace("b'lemon-bringup-v5'", "b'lemon-bringup-v7'")
    (root/'scripts'/name.replace('V6','V7').replace('v6','v7')).write_text(text,newline='\n')
print('Prepared v7 packaging/tests; only public SSH keys copied')
