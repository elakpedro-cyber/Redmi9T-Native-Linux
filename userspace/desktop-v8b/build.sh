#!/bin/bash
set -euo pipefail
work=/home/hadirpc/Redmi9T-Native-Linux
log=logs/v8b-desktop-offline
root=$(cat "$log/build-root.txt")
src=userspace/desktop-v8b
cp "$src/desktop.c" "$root/tmp/desktop.c"
chroot "$root" /bin/sh -ec '
    cd /tmp
    protocol=/usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml
    wayland-scanner client-header "$protocol" xdg-shell.h
    wayland-scanner private-code "$protocol" xdg-shell.c
    gcc -O2 -Wall -Wextra -Werror -I/usr/include/cairo desktop.c xdg-shell.c -o /usr/local/bin/lemon-desktop -lwayland-client -lcairo
'
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
mkdir -p "$stage/runtime"/{usr,lib,etc}
base=$(cat logs/v8-blocker-resolution/headless-root.txt)
# Runtime libs are taken from the tested package set, before installing the build toolchain.
cp -a "$base/usr/lib" "$base/usr/bin" "$base/usr/libexec" "$base/usr/share" "$stage/runtime/usr/"
cp -a "$root/usr/share/fonts" "$stage/runtime/usr/share/"
cp -a "$base/etc/fonts" "$stage/runtime/etc/"
cp -a "$base/lib/ld-musl-aarch64.so.1" "$stage/runtime/lib/"
mkdir -p "$stage/runtime/usr/local/bin"
cp "$root/usr/local/bin/lemon-desktop" "$stage/runtime/usr/local/bin/"
cp "$src/desktop.sh" "$stage/runtime/"
sed -i 's|<dir>/usr/share/fonts</dir>|<dir prefix="xdg">fonts</dir>|g' "$stage/runtime/etc/fonts/fonts.conf"
find "$stage/runtime" -type f -printf '%P\n' | LC_ALL=C sort > "$log/bundle-files.txt"
tar --sort=name --numeric-owner --owner=0 --group=0 --mtime=2026-11-06T00:00:00Z -C "$stage" -cf - runtime |
    gzip -n -6 > artifacts/lemon-desktop-v8b-aarch64.tar.gz
sha256sum artifacts/lemon-desktop-v8b-aarch64.tar.gz
stat -c %s artifacts/lemon-desktop-v8b-aarch64.tar.gz
