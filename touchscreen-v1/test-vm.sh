#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
work=/home/hadirpc/Redmi9T-Native-Linux
kernel=$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d
stage=$(mktemp -d "$work/touch-v1-vm.XXXXXX")
cp touchscreen-v1/{nvt-frame.c,nvt-frame.h,test-input-kernel.c} "$stage/"
printf 'obj-m := lemon_touch_test.o\nlemon_touch_test-y := test-input-kernel.o nvt-frame.o\n' >"$stage/Makefile"
make -C "$kernel" O="$work/kernel-out-v8b" M="$stage" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- W=1 modules
mkdir -p "$stage/root/"{bin,dev,proc,sys}
cp "$work/rootfs-v8b/boot-root/rescue/busybox" "$stage/root/bin/"
cp "$stage/lemon_touch_test.ko" "$stage/root/test-only.ko"
aarch64-linux-gnu-gcc -static -O2 -Wall -Wextra -Werror touchscreen-v1/test-evdev.c -o "$stage/root/read-test"
aarch64-linux-gnu-gcc -static -O2 -Wall -Wextra -Werror touchscreen-v1/test-module-loader.c -o "$stage/root/module-helper"
cat >"$stage/root/init" <<'EOF'
#!/bin/busybox sh
export PATH=/bin
busybox mount -t devtmpfs devtmpfs /dev
busybox mount -t proc proc /proc
busybox mount -t sysfs sysfs /sys
/module-helper load
result=99
for file in /sys/class/input/event*/device/name; do
 IFS= read -r name <"$file"
 if [ "$name" = lemon-nvt-offline-test ]; then
  device=${file%/device/name};device=${device##*/}
  /read-test "/dev/input/$device"
  result=$?
 fi
done
echo EVDEV_VM_RESULT=$result
/module-helper unload
busybox sleep 1
busybox poweroff -f
EOF
chmod 755 "$stage/root/init"
(cd "$stage/root"; find . -print0 | cpio --null -o -H newc 2>/dev/null) | gzip -1 >"$stage/initramfs.gz"
timeout 30 qemu-system-aarch64 -machine virt -cpu cortex-a57 -m 512 -nographic -no-reboot -nic none \
 -kernel "$work/kernel-out-v8b/arch/arm64/boot/Image" -initrd "$stage/initramfs.gz" -append 'console=ttyAMA0 rdinit=/init loglevel=3' </dev/null | tee logs/touchscreen-v1/evdev-vm-console.txt
grep -q REAL_ARM64_EVDEV_PASS logs/touchscreen-v1/evdev-vm-console.txt
grep -q EVDEV_VM_RESULT=0 logs/touchscreen-v1/evdev-vm-console.txt
