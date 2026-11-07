#!/bin/bash
set -euo pipefail
log=logs/v8b-labwc-offline
root=$(cat "$log/root.txt")
src=userspace/labwc-v8b
archive=${1:-artifacts/lemon-labwc-v8b-aarch64.tar.gz}
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
mkdir -p "$stage/runtime"/{usr,lib,etc}
cp -a "$root"/usr/{lib,bin,libexec,share} "$stage/runtime/usr/"
cp -a "$root/etc/fonts" "$stage/runtime/etc/"
cp -a "$root/lib/ld-musl-aarch64.so.1" "$stage/runtime/lib/"
cp -a "$src/config" "$src/session.sh" "$stage/runtime/"
sed -i 's|<dir>/usr/share/fonts</dir>|<dir prefix="xdg">fonts</dir>|g' "$stage/runtime/etc/fonts/fonts.conf"
tar --sort=name --numeric-owner --owner=0 --group=0 --mtime=2026-11-06T00:00:00Z -C "$stage" -cf - runtime |
    gzip -n -5 > "$archive"
sha256sum "$archive"
stat -c %s "$archive"
