#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux"
source="$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d"
out="$work/kernel-out-v8b"
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
export KBUILD_BUILD_USER=hadirpc KBUILD_BUILD_HOST=lemon-builder
export KBUILD_BUILD_TIMESTAMP='2026-11-05 00:00:00 +0000'
mkdir -p "$out"
cp "$project/config/linux-v8.config" "$out/.config"
cd "$source"
scripts/kconfig/merge_config.sh -m -O "$out" "$out/.config" "$project/config/gpu-v8b.fragment"
make O="$out" olddefconfig
cp "$out/.config" "$project/config/linux-v8b.config"
python3 - "$project" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
old=set((p/'config/linux-v8.config').read_text().splitlines())
new=set((p/'config/linux-v8b.config').read_text().splitlines())
missing=sorted(line for line in old if line.endswith('=y') and line not in new and line!='CONFIG_SM_DISPCC_6115=y')
assert not missing,missing
required=[line for line in (p/'config/gpu-v8b.fragment').read_text().splitlines() if line.endswith('=y')]
assert all(line in new for line in required),[line for line in required if line not in new]
print('Only the dormant SM6115 display clock provider changes from builtin to module.')
PY
make O="$out" -j12 Image.gz modules qcom/sm6115-xiaomi-lemon.dtb
cp "$out/arch/arm64/boot/Image" "$project/artifacts/Image-v8b"
cp "$out/arch/arm64/boot/Image.gz" "$project/artifacts/Image-v8b.gz"
cp "$out/arch/arm64/boot/dts/qcom/sm6115-xiaomi-lemon.dtb" "$project/reports/kernel-v8b-upstream.dtb"
make -s O="$out" kernelrelease > "$project/reports/kernelrelease-v8b.txt"
cp "$out/System.map" "$project/reports/System-v8b.map"

make O="$out" INSTALL_MOD_PATH="$work/modules-v8b" modules_install
