#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
work=/home/hadirpc/Redmi9T-Native-Linux
kernel=$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d
out=$work/kernel-out-v8b
stage=$(mktemp -d "$work/touch-v1-build.XXXXXX")
cp touchscreen-v1/{Makefile,nvt-spi.c,nvt-frame.c,nvt-frame.h} "$stage/"
sha256sum "$out/.config" "$out/arch/arm64/boot/Image" >logs/touchscreen-v1/kernel-before.sha256
make -C "$kernel" O="$out" M="$stage" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- W=1 modules
cp "$stage/lemon_nt36672a.ko" artifacts/touchscreen-v1/
file artifacts/touchscreen-v1/lemon_nt36672a.ko
modinfo artifacts/touchscreen-v1/lemon_nt36672a.ko
sha256sum -c logs/touchscreen-v1/kernel-before.sha256
printf '%s\n' "$stage" >logs/touchscreen-v1/build-stage.txt
