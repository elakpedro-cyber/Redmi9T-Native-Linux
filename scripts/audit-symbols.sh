#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux"
cd "$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d"
make -s O="$work/kernel-out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- DTC_FLAGS=-@ qcom/sm6115-xiaomi-lemon.dtb
cp "$work/kernel-out/arch/arm64/boot/dts/qcom/sm6115-xiaomi-lemon.dtb" "$project/reports/mainline-symbols.dtb"
python3 "$project/scripts/fdt_audit.py"
