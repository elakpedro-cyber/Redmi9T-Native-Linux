#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v7
root="$work/root"
sdk="$work/musl-sdk"
mkdir -p "$sdk" "$work/musl-package"
/home/hadirpc/Redmi9T-Native-Linux/rootfs-v5/sbin/apk.static --arch aarch64 --root "$root" fetch --output "$work/musl-package" musl-dev
for archive in "$work/musl-package/"*.apk; do tar xzf "$archive" -C "$sdk"; done
cc=aarch64-linux-gnu-gcc
"$cc" -fPIE -O2 -Wall -Wextra -Werror -nostdinc -isystem "$sdk/usr/include" -isystem "$root/usr/include" -isystem "$("$cc" -print-file-name=include)" -I"$root/usr/include/libdrm" -nostdlib -pie -Wl,--dynamic-linker=/lib/ld-musl-aarch64.so.1 \
    "$sdk/usr/lib/Scrt1.o" "$sdk/usr/lib/crti.o" "$("$cc" -print-file-name=crtbeginS.o)" \
    "$project/userspace/gpu-render-v7.c" -o "$root/usr/local/bin/gpu-render-v7" \
    -L"$root/usr/lib" -L"$root/lib" -Wl,-rpath-link,"$root/usr/lib:$root/lib" \
    -l:libdrm.so.2 -l:libgbm.so.1 -l:libEGL.so.1 -l:libGLESv2.so.2 -l:libc.musl-aarch64.so.1 -lgcc \
    "$("$cc" -print-file-name=crtendS.o)" "$sdk/usr/lib/crtn.o"
cp "$root/usr/local/bin/gpu-render-v7" "$project/artifacts/gpu-render-v7"
chroot "$root" /lib/ld-musl-aarch64.so.1 --list /usr/local/bin/gpu-render-v7
if chroot "$root" /usr/local/bin/gpu-render-v7 /dev/dri/renderD128; then exit 1; fi
echo 'PASS: cross-built musl ARM64 surfaceless FBO probe; missing render node rejected'
