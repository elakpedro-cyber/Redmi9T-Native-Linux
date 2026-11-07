#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux/bootshim-v4"
lib="$HOME/Redmi9T-Native-Linux/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d/scripts/dtc/libfdt"
mkdir -p "$work"
cd "$work"
cp "$project/artifacts/Image-v4" Image
cp "$project/artifacts/sm6115-xiaomi-lemon-v2.dtb" mainline.dtb
flags=(-O2 -ffreestanding -fno-builtin -fno-stack-protector -fpie -fvisibility=hidden -mgeneral-regs-only -mstrict-align -ffunction-sections -fdata-sections -I"$lib" -Wall -Wextra)
aarch64-linux-gnu-gcc "${flags[@]}" -c "$project/bootshim/bridge.c" -o bridge.o
aarch64-linux-gnu-gcc -c "$project/bootshim/start.S" -o start.o
objects=(start.o bridge.o)
for file in fdt fdt_ro fdt_rw fdt_wip fdt_sw fdt_addresses; do
    aarch64-linux-gnu-gcc "${flags[@]}" -c "$lib/$file.c" -o "$file.o"
    objects+=("$file.o")
done
aarch64-linux-gnu-gcc "${flags[@]}" -c "$project/bootshim/fdt_check.c" -o fdt_check.o
objects+=(fdt_check.o)
aarch64-linux-gnu-ld --gc-sections --build-id=none -T "$project/bootshim/link.ld" -o bootshim-v4.elf "${objects[@]}"
aarch64-linux-gnu-objcopy -O binary bootshim-v4.elf bootshim-v4.Image
cp bootshim-v4.elf "$project/artifacts/bootshim-v4.elf"
cp bootshim-v4.Image "$project/artifacts/bootshim-v4.Image"
aarch64-linux-gnu-nm -n bootshim-v4.elf > "$project/reports/bootshim-v4-symbols.txt"
aarch64-linux-gnu-readelf -r bootshim-v4.elf > "$project/reports/bootshim-v4-relocations.txt"
aarch64-linux-gnu-objdump -d bootshim-v4.elf > "$project/reports/bootshim-v4-disassembly.txt"
python3 "$project/scripts/package-v4.py"
