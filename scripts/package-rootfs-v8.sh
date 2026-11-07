#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || exit 1
project=$(cd "$(dirname "$0")/.." && pwd)
cd /home/hadirpc/Redmi9T-Native-Linux/rootfs-v8/boot-root
test ! -e run/dropbear/host_ed25519
test ! -e etc/dropbear/dropbear_ed25519_host_key
find . -print0 | LC_ALL=C sort -z | cpio --null -o --format=newc --owner=0:0 --reproducible | gzip -n -9 > "$project/artifacts/initramfs-v8.cpio.gz"
tar --sort=name --numeric-owner -cpf - . | gzip -n -9 > "$project/artifacts/alpine-rootfs-v8.tar.gz"
