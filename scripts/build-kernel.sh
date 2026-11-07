#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux"
commit=05441d697f7f9a927264f4058cbbc6a03dfcac9d
cd "$work"
[ -d "linux-$commit" ] || tar xf "$project/downloads/linux.tar.gz"
cd "linux-$commit"
out="$work/kernel-out"
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
export KBUILD_BUILD_USER=hadirpc KBUILD_BUILD_HOST=lemon-builder
export KBUILD_BUILD_TIMESTAMP='2026-11-05 00:00:00 +0000'
make O="$out" defconfig
python3 - "$out/.config" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]); text=p.read_text()
text=re.sub(r'^CONFIG_(\w+)=m$',r'# CONFIG_\1 is not set',text,flags=re.M)
for name in re.findall(r'^config (ARCH_\w+)',Path('arch/arm64/Kconfig.platforms').read_text(),re.M):
    if name != 'ARCH_QCOM':
        text=re.sub(r'^CONFIG_'+name+r'=.*$', '# CONFIG_'+name+' is not set',text,flags=re.M)
p.write_text(text)
PY
scripts/kconfig/merge_config.sh -m -O "$out" "$out/.config" "$project/config/bringup.fragment"
make O="$out" olddefconfig
make O="$out" -j12 Image.gz qcom/sm6115-xiaomi-lemon.dtb
cp "$out/arch/arm64/boot/Image" "$project/artifacts/Image"
cp "$out/arch/arm64/boot/Image.gz" "$project/artifacts/Image.gz"
cp "$out/arch/arm64/boot/dts/qcom/sm6115-xiaomi-lemon.dtb" "$project/artifacts/sm6115-xiaomi-lemon.dtb"
cp "$out/.config" "$project/config/linux.config"
cp arch/arm64/boot/dts/qcom/sm6115-xiaomi-lemon.dts "$project/config/sm6115-xiaomi-lemon.dts"
make O="$out" kernelrelease > "$project/reports/kernelrelease.txt"
dtc -I dtb -O dts "$project/artifacts/sm6115-xiaomi-lemon.dtb" > "$project/reports/lemon-compiled.dts" 2> "$project/reports/dtc-warnings.txt"
