#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || exit 1
project=$(cd "$(dirname "$0")/.." && pwd)
work=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v7
root="$work/root"
[ ! -e "$root" ] || { echo 'Refusing to replace v7 root'; exit 1; }
mkdir -p "$root"
tar xpf "$project/artifacts/alpine-rootfs-v6.tar.gz" -C "$root"
for name in init lemon-root-shell lemon-health lemon-diagnostics; do
    case "$name" in
        init) target=/init ;;
        lemon-health) target=/etc/init.d/lemon-health ;;
        *) target=/usr/local/sbin/$name ;;
    esac
    install -m755 "$project/config/$name-v7" "$root$target"
done
install -m644 "$project/config/inittab-v7" "$root/etc/inittab"
install -m600 "$project/config/ssh-authorized-keys-v7" "$root/root/.ssh/authorized_keys"
echo lemon-v7 > "$root/etc/hostname"
cp "$root/etc/resolv.conf" "$work/resolv-before"
trap 'cp "$work/resolv-before" "$root/etc/resolv.conf"' EXIT
cp /etc/resolv.conf "$root/etc/resolv.conf"
/home/hadirpc/Redmi9T-Native-Linux/rootfs-v5/sbin/apk.static --arch aarch64 --root "$root" add --no-cache mesa-dri-gallium mesa-egl mesa-gbm mesa-gles libdrm evtest
cp -a /home/hadirpc/Redmi9T-Native-Linux/modules-v7/lib "$root/"
find "$root/lib/modules" -type l \( -name build -o -name source \) -delete
chroot "$root" /sbin/depmod -a 7.4.0-rc1-lemon-bringup-v7
# Manual GPU bring-up only: there is no modules/udev/mdev boot service.
mkdir -p "$root/etc/modprobe.d"
install -m644 "$project/config/modprobe-gpu-v7.conf" "$root/etc/modprobe.d/lemon-gpu-manual.conf"
for script in /init /usr/local/sbin/lemon-usb-gadget /usr/local/sbin/lemon-root-shell /etc/init.d/lemon-net /etc/init.d/lemon-sshd; do
    chroot "$root" /bin/sh -n "$script"
done
chroot "$root" /sbin/apk info -vv > "$project/reports/rootfs-v7-packages.txt"
chroot "$root" /sbin/apk info -v > "$project/config/rootfs-v7-packages.lock"
cp "$root/lib/apk/db/installed" "$project/reports/rootfs-v7-apk-installed.txt"
