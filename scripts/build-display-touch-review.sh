set -euo pipefail
work=/home/hadirpc/Redmi9T-Native-Linux
src=$(echo "$work"/linux-054*)
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
out="$work/kernel-out-v8b"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/prototypes" "$tmp/patch"
cp display-v8/{qcom-lcdb-regulator-lemon.c,td4330-profile.c,td4330-packets.h,novatek-lemon-frame.c} "$tmp/prototypes/"
printf 'obj-m := qcom-lcdb-regulator-lemon.o\n' > "$tmp/prototypes/Kbuild"
make -C "$src" O="$out" M="$tmp/prototypes" W=1 td4330-profile.o novatek-lemon-frame.o modules
file "$tmp/prototypes/"*.o "$tmp/prototypes/"*.ko
mkdir -p "$tmp/patch/drivers/gpu/drm"
cp -a "$src/drivers/gpu/drm/msm" "$tmp/patch/drivers/gpu/drm/"
cp "$src/drivers/gpu/drm/"*.h "$tmp/patch/drivers/gpu/drm/"
for p in display-v8/{sm6115-refgen-required,dsi-14nm-pll-rollback}.patch; do
    patch --batch --fuzz=0 -d "$tmp/patch" -p1 < "$p"
done
m="$tmp/patch/drivers/gpu/drm/msm"
make -C "$src" O="$out" M="$m" W=1 dsi/dsi_host.o dsi/phy/dsi_phy_14nm.o
file "$m/dsi/dsi_host.o" "$m/dsi/phy/dsi_phy_14nm.o"
python3 scripts/test-sm6115-refgen-guard.py "$m/dsi/dsi_host.c"
python3 scripts/test-dsi-pll-rollback.py "$m/dsi/phy/dsi_phy_14nm.c"
mkdir -p "$tmp/patch/drivers/leds"
cp "$src/drivers/leds/leds-lm3692x.c" "$tmp/patch/drivers/leds/"
patch --batch --fuzz=0 -d "$tmp/patch" -p1 < display-v8/lm36923-defer-boost.patch
led="$tmp/patch/drivers/leds"
printf 'obj-m := leds-lm3692x.o\n' > "$led/Kbuild"
make -C "$src" O="$out" M="$led" W=1 leds-lm3692x.o
file "$led/leds-lm3692x.o"
