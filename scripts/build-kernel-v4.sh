#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux"
source="$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d"
out="$work/kernel-out-v4"
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
export KBUILD_BUILD_USER=hadirpc KBUILD_BUILD_HOST=lemon-builder
export KBUILD_BUILD_TIMESTAMP='2026-11-05 00:00:00 +0000'
mkdir -p "$out"
cp "$project/config/linux.config" "$out/.config"
cd "$source"
scripts/kconfig/merge_config.sh -m -O "$out" "$out/.config" "$project/config/ufs-v4.fragment"
make O="$out" olddefconfig
cp "$out/.config" "$project/config/linux-v4.config"
python3 - "$project" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
old=set((p/'config/linux.config').read_text().splitlines())
new=set((p/'config/linux-v4.config').read_text().splitlines())
missing=sorted(line for line in old if line.endswith('=y') and line not in new)
assert not missing,missing
required=[line for line in (p/'config/ufs-v4.fragment').read_text().splitlines() if line.endswith('=y')]
assert all(line in new for line in required),[line for line in required if line not in new]
print('All v3 built-in features retained; required UFS/SCSI built-ins enabled.')
PY
make O="$out" -j12 Image.gz qcom/sm6115-xiaomi-lemon.dtb
cp "$out/arch/arm64/boot/Image" "$project/artifacts/Image-v4"
cp "$out/arch/arm64/boot/Image.gz" "$project/artifacts/Image-v4.gz"
cp "$out/arch/arm64/boot/dts/qcom/sm6115-xiaomi-lemon.dtb" "$project/reports/kernel-v4-upstream.dtb"
make -s O="$out" kernelrelease > "$project/reports/kernelrelease-v4.txt"
cp "$out/System.map" "$project/reports/System-v4.map"
