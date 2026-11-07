#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v5/root
test "$(id -u)" = 0
for path in /init /usr/local/sbin/lemon-root-shell /usr/local/sbin/lemon-diagnostics /etc/init.d/lemon-health; do
    chroot "$root" /bin/sh -n "$path"
done
test "$(cat "$root/etc/lemon/usbnet-mode")" = off
test -z "$(grep -vE '^[[:space:]]*(#|$)' "$root/etc/fstab")"
chroot "$root" /bin/busybox true
chroot "$root" /rescue/busybox true
chroot "$root" /sbin/openrc --version
chroot "$root" /sbin/apk --version
chroot "$root" /sbin/ip -Version
chroot "$root" /bin/lsblk --version
chroot "$root" /sbin/blkid --version
chroot "$root" /usr/bin/strace --version
chroot "$root" /usr/sbin/dropbear -V
echo 'PASS: packaged init/root-shell/diagnostics/OpenRC shell syntax and ARM64 program execution'
