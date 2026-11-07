#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
cd /home/hadirpc/Redmi9T-Native-Linux/rootfs-v7/root
# Count only: no oversized boot image is created.
find . -print0 | LC_ALL=C sort -z | cpio --null -o --format=newc --owner=0:0 --reproducible | gzip -n -9 | wc -c > "$project/reports/v7-full-initramfs-bytecount.txt"
