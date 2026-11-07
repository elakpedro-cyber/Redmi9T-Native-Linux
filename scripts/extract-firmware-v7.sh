#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
vendor="$project/downloads/v7-personal/vendor-slot1.img"
out="$project/downloads/v7-personal/firmware"
mkdir -p "$out"
debugfs -R 'ls -l /firmware' "$vendor" > "$project/reports/v7-vendor-firmware-list.txt" 2>&1
for file in a610_zap.elf a610_zap.mdt a610_zap.b00 a610_zap.b01 a610_zap.b02 a630_sqe.fw; do
    test ! -e "$out/$file"
    debugfs -R "dump /firmware/$file $out/$file" "$vendor"
done
file "$out"/*
readelf -l "$out/a610_zap.elf"
sha256sum "$out"/*
