#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
export PATH="/home/hadirpc/Redmi9T-Native-Linux/v7-python/bin:$PATH"
source=/home/hadirpc/Redmi9T-Native-Linux/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d
out=/home/hadirpc/Redmi9T-Native-Linux/kernel-out-v7
cd "$source"
make O="$out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dt_binding_schemas
dt-validate -s "$out/Documentation/devicetree/bindings/processed-schema.json" "$project/artifacts/sm6115-xiaomi-lemon-v2.dtb" > "$project/reports/v7-native-baseline-schema.txt" 2>&1
dt-validate -s "$out/Documentation/devicetree/bindings/processed-schema.json" "$project/artifacts/sm6115-xiaomi-lemon-v7.dtb" > "$project/reports/v7-native-schema.txt" 2>&1
# Warnings may return zero: retain and compare diagnostics separately.
dt-validate -s "$out/Documentation/devicetree/bindings/processed-schema.json" -l 'gpu/qcom,adreno' "$project/artifacts/sm6115-xiaomi-lemon-v7.dtb" > "$project/reports/v7-gpu-schema.txt" 2>&1
