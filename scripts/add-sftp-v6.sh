#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || exit 1
project=$(cd "$(dirname "$0")/.." && pwd)
work=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v6
root="$work/root"
cp "$root/etc/resolv.conf" "$work/resolv-before-sftp"
trap 'cp "$work/resolv-before-sftp" "$root/etc/resolv.conf"' EXIT
cp /etc/resolv.conf "$root/etc/resolv.conf"
/home/hadirpc/Redmi9T-Native-Linux/rootfs-v5/sbin/apk.static --arch aarch64 --root "$root" add --no-cache openssh-sftp-server
test -x "$root/usr/lib/ssh/sftp-server"
chroot "$root" /sbin/apk info -vv > "$project/reports/rootfs-v6-packages.txt"
chroot "$root" /sbin/apk info -v > "$project/config/rootfs-v6-packages.lock"
cp "$root/lib/apk/db/installed" "$project/reports/rootfs-v6-apk-installed.txt"
