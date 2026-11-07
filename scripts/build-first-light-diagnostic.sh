#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
cd "$project"
out="$project/artifacts/first-light-diagnostic"
logs="$project/logs/v8b-first-light"
lib="$HOME/Redmi9T-Native-Linux/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d/scripts/dtc/libfdt"
review=logs/refgen-sm6115/sm6115-dsi-phy-mx-review.dtb
mkdir -p "$out" "$logs"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

test "$(sha256sum "$review" | cut -d ' ' -f 1)" = 896b6f7bb0449885785a9be52f2f2c4e16c33db164bc13cd805d4e52e05aadc2
dtc -@ -I dts -O dtb -o "$tmp/fb.dtbo" display-v8/first-light-diagnostic.dts
fdtoverlay -i "$review" -o "$out/sm6115-xiaomi-lemon-first-light-diagnostic.dtb" "$tmp/fb.dtbo"
dtc -q -I dtb -O dts -o "$out/sm6115-xiaomi-lemon-first-light-diagnostic.dts" "$out/sm6115-xiaomi-lemon-first-light-diagnostic.dtb"
python3 scripts/audit-first-light-diagnostic.py "$out/sm6115-xiaomi-lemon-first-light-diagnostic.dtb"
python3 scripts/validate-stage-c-v8.py "$out/sm6115-xiaomi-lemon-first-light-diagnostic.dtb"

cp artifacts/Image-v8b "$out/Image-v8b-first-light-diagnostic"
(
    cd "$tmp"
    ln -s "$out/Image-v8b-first-light-diagnostic" Image
    ln -s "$out/sm6115-xiaomi-lemon-first-light-diagnostic.dtb" mainline.dtb
    flags=(-O2 -ffreestanding -fno-builtin -fno-stack-protector -fpie -fvisibility=hidden -mgeneral-regs-only -mstrict-align -ffunction-sections -fdata-sections -I"$lib" -Wall -Wextra)
    aarch64-linux-gnu-gcc -c "$project/bootshim/start.S" -o start.o
    objects=(start.o)
    for src in "$project"/bootshim/{bridge,fdt_check}.c "$lib"/{fdt,fdt_ro,fdt_rw,fdt_wip,fdt_sw,fdt_addresses}.c; do
        obj="$(basename "${src%.c}").o"
        aarch64-linux-gnu-gcc "${flags[@]}" -c "$src" -o "$obj"
        objects+=("$obj")
    done
    aarch64-linux-gnu-ld --gc-sections --build-id=none -T "$project/bootshim/link.ld" -o shim.elf "${objects[@]}"
    aarch64-linux-gnu-objcopy -O binary shim.elf "$logs/bootshim.Image"
    aarch64-linux-gnu-nm -n shim.elf > "$logs/bootshim-symbols.txt"
)
gzip -n -9 -c "$logs/bootshim.Image" > "$tmp/bootshim.Image.gz"
stock_args=$(python3 tools/unpack_bootimg.py --boot_img artifacts/boot-linux-test-v8b.img --out "$tmp/baseline" --format=mkbootimg)
# Use the verified baseline header arguments and replace only its extracted wrapper.
cp "$tmp/bootshim.Image.gz" "$tmp/baseline/kernel"
python3 - "$stock_args" "$out/boot-linux-v8b-first-light-diagnostic.img" <<'PY'
import shlex
import subprocess
import sys

subprocess.run([sys.executable, 'tools/mkbootimg.py', *shlex.split(sys.argv[1]),
                '--output', sys.argv[2]], check=True)
PY
python3 tools/unpack_bootimg.py --boot_img "$out/boot-linux-v8b-first-light-diagnostic.img" --out "$tmp/new" | tee "$logs/boot-header.txt"
cmp "$tmp/baseline/ramdisk" "$tmp/new/ramdisk"
cmp "$tmp/baseline/dtb" "$tmp/new/dtb"
cmp "$tmp/bootshim.Image.gz" "$tmp/new/kernel"
cmp artifacts/Image-v8b "$out/Image-v8b-first-light-diagnostic"
test "$(stat -c %s "$out/boot-linux-v8b-first-light-diagnostic.img")" -lt 134217728
echo 'PASS: AOSP header round trip, stock-facing DTB, v8b ramdisk and native kernel preserved'
(cd "$out" && sha256sum *.img *.dtb Image-v8b-first-light-diagnostic > SHA256SUMS)
