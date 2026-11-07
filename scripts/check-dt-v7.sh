#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
export PATH="/home/hadirpc/Redmi9T-Native-Linux/v7-python/bin:$PATH"
cd /home/hadirpc/Redmi9T-Native-Linux/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d
make O=/home/hadirpc/Redmi9T-Native-Linux/kernel-out-v7 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- DT_SCHEMA_FILES='gpu/qcom,adreno.yaml' CHECK_DTBS=y qcom/sm6115-xiaomi-lemon.dtb
