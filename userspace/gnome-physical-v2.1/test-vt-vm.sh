#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
root=$(mktemp -d)
trap 'rm -rf "$root"' EXIT
mkdir -p "$root"/{bin,dev,proc,sys}
cp /home/hadirpc/Redmi9T-Native-Linux/rootfs-v8b/boot-root/rescue/busybox "$root/bin/busybox"
aarch64-linux-gnu-gcc -O2 -static -Wall -Wextra -Werror userspace/gnome-physical-v2.1/vt-cleanup.c -o "$root/vt-cleanup"
aarch64-linux-gnu-gcc -O2 -static -Wall -Wextra -Werror userspace/gnome-physical-v2.1/test-vt.c -o "$root/test-vt"
cp artifacts/gnome-physical-v2.1/watchdog "$root/watchdog"
cp userspace/gnome-physical-v2.1/test-watchdog.sh "$root/test-watchdog.sh"
cat >"$root/init" <<'EOF'
#!/bin/busybox sh
export PATH=/bin
busybox mount -t devtmpfs devtmpfs /dev
busybox mount -t proc proc /proc
busybox mount -t sysfs sysfs /sys
/test-vt
result=$?
echo VT_VM_RESULT=$result
/bin/busybox sh /test-watchdog.sh
echo WATCHDOG_VM_RESULT=$?
busybox sleep 1
busybox poweroff -f
EOF
chmod 755 "$root/init"
(cd "$root"; find . -print0 | cpio --null -o -H newc 2>/dev/null) | gzip -1 > logs/gnome-physical-v2.1/vt-initramfs.cpio.gz
timeout 60 qemu-system-aarch64 -machine virt -cpu cortex-a57 -m 512 -nographic -no-reboot -nic none \
    -kernel "${VT_KERNEL:-/home/hadirpc/Redmi9T-Native-Linux/kernel-out-v8b/arch/arm64/boot/Image}" -initrd logs/gnome-physical-v2.1/vt-initramfs.cpio.gz \
    -append 'console=ttyAMA0 rdinit=/init loglevel=3'
