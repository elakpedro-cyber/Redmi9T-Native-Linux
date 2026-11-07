#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
work="$HOME/Redmi9T-Native-Linux"
source="$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d"
out="$work/kernel-out-v8b"
logs="$PWD/logs/v8b-first-light"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
mkdir -p "$tmp/drivers/gpu/drm" "$logs"
cp -a "$source/drivers/gpu/drm/msm" "$tmp/drivers/gpu/drm/"
cp "$source/drivers/gpu/drm/"*.h "$tmp/drivers/gpu/drm/"
for patch in display-v8/{sm6115-refgen-required,dsi-14nm-pll-rollback}.patch; do
    patch --batch --fuzz=0 -d "$tmp" -p1 < "$patch"
done
msm="$tmp/drivers/gpu/drm/msm"
python3 scripts/test-sm6115-refgen-guard.py "$msm/dsi/dsi_host.c"
python3 scripts/test-dsi-pll-rollback.py "$msm/dsi/phy/dsi_phy_14nm.c"
make -C "$source" O="$out" M="$msm" -j12 W=1 modules
ko="$msm/msm.ko"
file "$ko"
test "$(modinfo -F vermagic "$ko")" = "$(modinfo -F vermagic "$out/drivers/gpu/drm/msm/msm.ko")"
for symbol in dpu_kms_init msm_dsi_host_init msm_dsi_phy_disable; do
    aarch64-linux-gnu-nm --defined-only "$ko" | awk -v expected="$symbol" '
        $3 == expected { found=1 } END { exit !found }'
done
# Keep it in the offline evidence directory, out of the boot ramdisk.
cp "$ko" "$logs/msm-first-light-review.ko"
sha256sum "$logs/msm-first-light-review.ko"
echo 'PASS: ARM64 module links DPU, DSI Host and PHY; vermagic matches v8b'
