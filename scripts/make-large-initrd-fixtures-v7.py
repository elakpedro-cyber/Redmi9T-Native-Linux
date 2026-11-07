from pathlib import Path
import json,shutil,subprocess
root=Path(__file__).resolve().parents[1]
size=(root/'artifacts/initramfs-v7.cpio.gz').stat().st_size
for case in json.loads((root/'reports/abl-v7-placement-emulation.json').read_text())['cases']:
    name='large-initrd-'+case['scenario']
    path=root/'reports'/('shim-input-v7-'+name+'.dtb')
    shutil.copyfile(root/'reports/live-v4.dtb',path)
    rd=int(case['load_addresses']['ramdisk'],16)
    for prop,value in [('linux,initrd-start',rd),('linux,initrd-end',rd+size)]:
        subprocess.run(['fdtput','-t','x',str(path),'/chosen',prop,f'{value>>32:x}',f'{value&0xffffffff:x}'],check=True)
