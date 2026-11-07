#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v7/boot-root
test ! -e "$root"
mkdir -p "$root"
tar xpf "$project/artifacts/alpine-rootfs-v6.tar.gz" -C "$root"
cp -a /home/hadirpc/Redmi9T-Native-Linux/modules-v7/lib "$root/"
find "$root/lib/modules" -type l \( -name build -o -name source \) -delete
chroot "$root" /sbin/depmod -a 7.4.0-rc1-lemon-bringup-v7
mkdir -p "$root/etc/modprobe.d"
install -m644 "$project/config/modprobe-gpu-v7.conf" "$root/etc/modprobe.d/lemon-gpu-manual.conf"
echo lemon-v7 > "$root/etc/hostname"
LEMON_ROOTFS="$root" bash "$project/scripts/finish-rootfs-v7.sh"
