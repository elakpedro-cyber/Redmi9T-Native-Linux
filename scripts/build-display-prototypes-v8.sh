#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux"
mkdir -p "$work/display-v8"
cp "$project/display-v8/"* "$work/display-v8/"
make -C "$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d" \
    O="$work/kernel-out-v8" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
    M="$work/display-v8" MO="$work/display-out-v8" td4330-profile.o modules
