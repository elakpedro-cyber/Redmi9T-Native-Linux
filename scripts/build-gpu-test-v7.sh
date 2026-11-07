#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v7/root
work=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v7
cp "$root/etc/resolv.conf" "$work/resolv-before-gpu"
trap 'cp "$work/resolv-before-gpu" "$root/etc/resolv.conf"' EXIT
cp /etc/resolv.conf "$root/etc/resolv.conf"
apk=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v5/sbin/apk.static
"$apk" --arch aarch64 --root "$root" add --no-cache --virtual .gpu-build gcc musl-dev
mkdir -p "$work/headers"
"$apk" --arch aarch64 --root "$root" fetch --output "$work/headers" mesa-dev libdrm-dev linux-headers
for archive in "$work/headers/"*.apk; do
    tar xzf "$archive" -C "$root" --wildcards 'usr/include/*'
done
cp "$project/userspace/gpu-render-v7.c" "$root/tmp/gpu-render-v7.c"
chroot "$root" /usr/bin/gcc -O2 -Wall -Wextra -Werror -I/usr/include/libdrm /tmp/gpu-render-v7.c -o /usr/local/bin/gpu-render-v7 -l:libdrm.so.2 -l:libgbm.so.1 -l:libEGL.so.1 -l:libGLESv2.so.2
cp "$root/usr/local/bin/gpu-render-v7" "$project/artifacts/gpu-render-v7"
# Negative execution test only, without a render node or DRM hardware.
if chroot "$root" /usr/local/bin/gpu-render-v7 /dev/dri/renderD128; then
    echo 'Unexpected render node in offline chroot'; exit 1
fi
rm "$root/tmp/gpu-render-v7.c"
"$apk" --arch aarch64 --root "$root" del .gpu-build
chroot "$root" /sbin/apk info -vv > "$project/reports/rootfs-v7-gpu-packages.txt"
