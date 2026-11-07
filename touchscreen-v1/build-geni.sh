#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
work=/home/hadirpc/Redmi9T-Native-Linux
kernel=$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d
stage=$(mktemp -d "$work/touch-v1-geni.XXXXXX")
cp "$kernel/drivers/spi/spi-geni-qcom.c" "$stage/"
cp touchscreen-v1/lemon-geni-delay.h "$stage/"
python3 touchscreen-v1/patch-geni.py "$stage/spi-geni-qcom.c"
printf 'obj-m := spi-geni-qcom.o\n' >"$stage/Makefile"
make -C "$kernel" O="$work/kernel-out-v8b" M="$stage" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- W=1 modules
cp "$stage/spi-geni-qcom.ko" artifacts/touchscreen-v1/
modinfo artifacts/touchscreen-v1/spi-geni-qcom.ko
