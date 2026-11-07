#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d /home/hadirpc/Redmi9T-Native-Linux/v7-addon-test.XXXXXX)
root="$work/root"
cp -a /home/hadirpc/Redmi9T-Native-Linux/rootfs-v7/boot-root "$root"
tar xpf "$project/artifacts/gpu-userspace-v7.tar.gz" -C "$root"
chroot "$root" /lib/ld-musl-aarch64.so.1 --list /usr/local/bin/gpu-render-v7
gallium=$(find "$root/usr/lib" -maxdepth 1 -name 'libgallium*.so*' -type f | head -1)
test -n "$gallium"
chroot "$root" /lib/ld-musl-aarch64.so.1 --list "${gallium#"$root"}"
if chroot "$root" /usr/local/bin/gpu-render-v7 /dev/dri/renderD128; then exit 1; fi
chroot "$root" /sbin/apk info -vv > "$project/reports/v7-addon-installed-packages.txt"
test -x "$root/usr/bin/evtest"
echo 'PASS: addon extracted over boot root; ARM64 GLES/GBM/DRM/Gallium dependencies resolve; probe rejects missing render node'
echo "Offline test root retained: $root"
