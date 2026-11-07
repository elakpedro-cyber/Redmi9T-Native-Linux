#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/home/hadirpc/Redmi9T-Native-Linux/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d
sed -n '1,220p' "$source/arch/arm64/boot/dts/qcom/sm6115-xiaomi-lemon.dts"
grep -n -A90 'gpu: gpu@' "$source/arch/arm64/boot/dts/qcom/sm6115.dtsi"
grep -n -A45 -B5 '610' "$source/drivers/gpu/drm/msm/adreno/a6xx_catalog.c"
grep -n -A30 -B5 'zap' "$source/drivers/gpu/drm/msm/adreno/adreno_gpu.c"
find "$source/drivers/input/touchscreen" -maxdepth 1 -iname '*nov*' -o -iname '*nt36*' -o -iname '*focal*' -o -iname '*edt*'
grep -n 'compatible.*qcom' "$source/drivers/regulator/qcom-labibb-regulator.c"
grep -n 'compatible.*qcom' "$source/drivers/video/backlight/qcom-wled.c"
