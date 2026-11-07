#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux"
source="$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d"
out="$work/kernel-out-v8"
export PATH="$work/v7-python/bin:$PATH"
make -C "$source" O="$out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CHECK_DTBS=y qcom/sm6115-xiaomi-lemon.dtb
schema="$out/Documentation/devicetree/bindings/processed-schema.json"
test -s "$schema"
dt-validate -s "$schema" "$project/artifacts/sm6115-xiaomi-lemon-v7.dtb" > "$project/reports/v8-baseline-schema.txt" 2>&1
dt-validate -s "$schema" "$project/artifacts/sm6115-xiaomi-lemon-v8.dtb" > "$project/reports/v8-native-schema.txt" 2>&1
sed 's/lemon-v7\.dtb/lemon-v8.dtb/g' "$project/reports/v8-baseline-schema.txt" | diff - "$project/reports/v8-native-schema.txt"
dtc -@ -I dts -O dtb -o "$project/reports/v8-host-phy-review.dtbo" "$project/display-v8/host-phy-review.dts"
fdtoverlay -i "$project/artifacts/sm6115-xiaomi-lemon-v8.dtb" \
    -o "$project/reports/v8-host-phy-review.dtb" "$project/reports/v8-host-phy-review.dtbo"
dt-validate -s "$schema" "$project/reports/v8-host-phy-review.dtb" > "$project/reports/v8-host-phy-review-schema.txt" 2>&1
test ! -s "$project/reports/v8-host-phy-review-schema.txt"
