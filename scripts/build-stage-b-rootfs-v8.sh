#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work=/home/hadirpc/Redmi9T-Native-Linux
release=$(cat "$project/reports/kernelrelease-v8b.txt")
test "$release" = 7.4.0-rc1-lemon-bringup-v8b

root="$work/rootfs-v8b/boot-root"
test ! -e "$root"
mkdir -p "$root"
tar --exclude='./lib/modules/*' -xpf "$project/artifacts/alpine-rootfs-v8.tar.gz" -C "$root"
cp -a "$work/modules-v8b/lib/modules/$release" "$root/lib/modules/"
if [[ -L "$root/lib/modules/$release/build" ]]; then
    unlink "$root/lib/modules/$release/build"
fi
printf 'blacklist dispcc_sm6115\n' > "$root/etc/modprobe.d/lemon-stage-b.conf"
test ! -e "$root/run/dropbear/host_ed25519"

probe="$work/dsi-check-v8b"
mkdir -p "$probe"
cp "$project/display-v8/dsi-host-check.c" "$probe/"
printf 'obj-m := dsi-host-check.o\n' > "$probe/Kbuild"
make -C "$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d" O="$work/kernel-out-v8b" \
    ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M="$probe" MO="$work/dsi-check-out-v8b" modules
install -Dm644 "$work/dsi-check-out-v8b/dsi-host-check.ko" "$root/lib/modules/$release/extra/dsi-host-check.ko"
depmod -b "$root" "$release"

cd "$root"
find . -print0 | LC_ALL=C sort -z | cpio --null -o --format=newc --owner=0:0 --reproducible | gzip -n -9 > "$project/artifacts/initramfs-v8b.cpio.gz"
