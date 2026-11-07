#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=${LEMON_ROOTFS:-/home/hadirpc/Redmi9T-Native-Linux/rootfs-v7/root}
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
install -m644 "$project/config/modprobe-gpu-v7.conf" "$root/etc/modprobe.d/lemon-gpu-manual.conf"
firmware="$project/downloads/v7-personal/firmware"
mkdir -p "$root/lib/firmware/qcom/sm6115/xiaomi/lemon"
for name in a610_zap.mdt a610_zap.b00 a610_zap.b01 a610_zap.b02; do
    install -m644 "$firmware/$name" "$root/lib/firmware/qcom/sm6115/xiaomi/lemon/$name"
done
install -m644 "$firmware/a630_sqe.fw" "$root/lib/firmware/qcom/a630_sqe.fw"
dtc -@ -I dts -O dtb -o "$project/reports/gpu-firmware-v7.dtbo" "$project/config/gpu-firmware-v7.dts"
fdtoverlay -i "$project/artifacts/sm6115-xiaomi-lemon-v2.dtb" -o "$project/artifacts/sm6115-xiaomi-lemon-v7.dtb" "$project/reports/gpu-firmware-v7.dtbo"
dtc -I dtb -O dts -o "$project/reports/sm6115-xiaomi-lemon-v7.dts" "$project/artifacts/sm6115-xiaomi-lemon-v7.dtb"
for script in /init /usr/local/sbin/lemon-usb-gadget /usr/local/sbin/lemon-root-shell /etc/init.d/lemon-net /etc/init.d/lemon-sshd; do
    chroot "$root" /bin/sh -n "$script"
done
chroot "$root" /sbin/apk info -vv > "$project/reports/rootfs-v7-packages.txt"
chroot "$root" /sbin/apk info -v > "$project/config/rootfs-v7-packages.lock"
cp "$root/lib/apk/db/installed" "$project/reports/rootfs-v7-apk-installed.txt"
