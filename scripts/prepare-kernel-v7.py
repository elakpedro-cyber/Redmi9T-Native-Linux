from pathlib import Path
root=Path(__file__).resolve().parents[1]
t=(root/'scripts/build-kernel-v5.sh').read_text().replace('v5','v7').replace('config/linux-v4.config','config/linux-v6.config').replace('bringup-v7.fragment','gpu-v7.fragment')
t=t.replace('make O="$out" -j12 Image.gz qcom/sm6115-xiaomi-lemon.dtb','make O="$out" -j12 Image.gz modules qcom/sm6115-xiaomi-lemon.dtb')
t+='\nmake O="$out" INSTALL_MOD_PATH="$work/modules-v7" modules_install\n'
(root/'scripts/build-kernel-v7.sh').write_text(t,newline='\n')
