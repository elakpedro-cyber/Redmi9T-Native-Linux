#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux/bootshim"
lib="$HOME/Redmi9T-Native-Linux/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d/scripts/dtc/libfdt"
mkdir -p "$work"
cd "$work"
cp "$project/artifacts/Image" Image
cp "$project/artifacts/sm6115-xiaomi-lemon-boot.dtb" mainline-v2.dtb
fdtput -d mainline-v2.dtb /reserved-memory/ramoops@64000000 ecc-size
cp mainline-v2.dtb "$project/artifacts/sm6115-xiaomi-lemon-v2.dtb"
flags=(-O2 -ffreestanding -fno-builtin -fno-stack-protector -fpie -fvisibility=hidden -mgeneral-regs-only -mstrict-align -ffunction-sections -fdata-sections -I"$lib" -Wall -Wextra)
aarch64-linux-gnu-gcc "${flags[@]}" -c "$project/bootshim/v2/bridge.c" -o bridge.o
aarch64-linux-gnu-gcc -c "$project/bootshim/v2/start.S" -o start.o
objects=(start.o bridge.o)
for file in fdt fdt_ro fdt_rw fdt_wip fdt_sw fdt_addresses; do
    aarch64-linux-gnu-gcc "${flags[@]}" -c "$lib/$file.c" -o "$file.o"
    objects+=("$file.o")
done
aarch64-linux-gnu-gcc "${flags[@]}" -c "$project/bootshim/v2/fdt_check.c" -o fdt_check.o
objects+=(fdt_check.o)
aarch64-linux-gnu-ld --gc-sections --build-id=none -T "$project/bootshim/v2/link.ld" -o bootshim.elf "${objects[@]}"
aarch64-linux-gnu-objcopy -O binary bootshim.elf bootshim.Image
cp bootshim.elf "$project/artifacts/bootshim.elf"
cp bootshim.Image "$project/artifacts/bootshim.Image"
aarch64-linux-gnu-nm -n bootshim.elf > "$project/reports/bootshim-symbols.txt"
aarch64-linux-gnu-readelf -r bootshim.elf > "$project/reports/bootshim-relocations.txt"
python3 "$project/scripts/package-v2.py"
