from pathlib import Path
import hashlib,shutil
root=Path(__file__).resolve().parents[1]
device=root/'pmaports/device/testing/device-xiaomi-lemon'
kernel=root/'pmaports/device/testing/linux-xiaomi-lemon'
shutil.copyfile(root/'config/linux-v5.config',kernel/'config-xiaomi-lemon.aarch64')
shutil.copyfile(root/'config/cmdline.txt',device/'kernel-cmdline.conf')
for directory,files in [(device,['deviceinfo','kernel-cmdline.conf']),(kernel,['config-xiaomi-lemon.aarch64','lemon-runtime.dts'])]:
    p=directory/'APKBUILD';text=p.read_text().split('\nsha512sums=')[0].rstrip()
    sums=[]
    if directory==kernel:
        sums.append(hashlib.sha512((root/'downloads/linux.tar.gz').read_bytes()).hexdigest()+'  linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d.tar.gz')
    sums.extend(hashlib.sha512((directory/f).read_bytes()).hexdigest()+'  '+f for f in files)
    p.write_text(text+'\n\nsha512sums="\n'+'\n'.join(sums)+'\n"\n',newline='\n')
