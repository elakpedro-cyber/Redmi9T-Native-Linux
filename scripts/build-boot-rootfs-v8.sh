#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work=/home/hadirpc/Redmi9T-Native-Linux
root="$work/rootfs-v8/boot-root"
test ! -e "$root"
mkdir -p "$root"
tar --exclude='./lib/modules/*' -xpf "$project/artifacts/alpine-rootfs-v7.tar.gz" -C "$root"
release=$(cat "$project/reports/kernelrelease-v8.txt")
test "$release" = 7.4.0-rc1-lemon-bringup-v8
cp -a "$work/modules-v8/lib/modules/$release" "$root/lib/modules/"
if [[ -L "$root/lib/modules/$release/build" ]]; then
    unlink "$root/lib/modules/$release/build"
fi
depmod -b "$root" "$release"
for file in init etc/init.d/lemon-health usr/local/sbin/lemon-diagnostics; do
    sed -i 's/LEMON_\([A-Z]*\)_V7_REACHED/LEMON_\1_V8_REACHED/g; s/lemon v7/lemon v8/g; s/=== v7/=== v8/g' "$root/$file"
done
test ! -e "$root/run/dropbear/host_ed25519"
cmp "$root/root/.ssh/authorized_keys" "$project/config/ssh-authorized-keys-v7"
bash "$project/scripts/package-rootfs-v8.sh"
