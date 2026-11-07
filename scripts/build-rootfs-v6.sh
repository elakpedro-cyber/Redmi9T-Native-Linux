#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || exit 1
project=$(cd "$(dirname "$0")/.." && pwd)
root=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v6/root
[ ! -e "$root" ] || { echo 'Refusing to replace v6 root'; exit 1; }
mkdir -p "$root"
tar xpf "$project/artifacts/alpine-rootfs-v5.tar.gz" -C "$root"
for name in init lemon-root-shell lemon-health lemon-diagnostics; do
    case "$name" in
        init) target=/init ;;
        lemon-health) target=/etc/init.d/lemon-health ;;
        *) target=/usr/local/sbin/$name ;;
    esac
    install -m755 "$project/config/$name-v6" "$root$target"
done
install -m755 "$project/config/lemon-usb-gadget-v6" "$root/usr/local/sbin/lemon-usb-gadget"
for name in lemon-net lemon-sshd; do
    install -m755 "$project/config/$name-v6" "$root/etc/init.d/$name"
    ln -s "/etc/init.d/$name" "$root/etc/runlevels/default/$name"
done
install -m644 "$project/config/inittab-v6" "$root/etc/inittab"
install -m600 "$project/config/ssh-authorized-keys-v6" "$root/root/.ssh/authorized_keys"
chmod 700 "$root/root/.ssh"
echo ncm > "$root/etc/lemon/usbnet-mode"
echo lemon-v6 > "$root/etc/hostname"
for script in /init /usr/local/sbin/lemon-usb-gadget /usr/local/sbin/lemon-root-shell /etc/init.d/lemon-net /etc/init.d/lemon-sshd; do
    chroot "$root" /bin/sh -n "$script"
done
chroot "$root" /sbin/apk info -vv > "$project/reports/rootfs-v6-packages.txt"
bash "$project/scripts/add-sftp-v6.sh"
echo 'v6 root ready; use package-rootfs-v6.sh after offline tests'
