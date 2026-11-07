set -euo pipefail
d=logs/refgen-sm6115
k=$(echo /home/hadirpc/Redmi9T-Native-Linux/linux-054*)
base=logs/display-safety-gate/gnome-kms-review.dtb
test -f "$base"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp "$base" "$tmp/base.dtb"
# Supply the original DTS symbol names on a temporary copy of the stripped DTB.
fdtput -c "$tmp/base.dtb" /__symbols__
fdtput -t s "$tmp/base.dtb" /__symbols__ mdss_dsi0_phy /soc@0/display-subsystem@5e00000/phy@5e94400
fdtput -t s "$tmp/base.dtb" /__symbols__ rpmpd /remoteproc/glink-edge/rpm-requests/power-controller
fdtput -t s "$tmp/base.dtb" /__symbols__ rpmpd_opp_nom /remoteproc/glink-edge/rpm-requests/power-controller/opp-table/opp5
cpp -P -nostdinc -undef -x assembler-with-cpp -I "$k/include" \
    display-v8/sm6115-dsi-phy-mx-review.dts > "$tmp/overlay.dts"
dtc -@ -I dts -O dtb -o "$d/sm6115-dsi-phy-mx-review.dtbo" "$tmp/overlay.dts"
fdtoverlay -i "$tmp/base.dtb" -o "$d/sm6115-dsi-phy-mx-review.dtb" "$d/sm6115-dsi-phy-mx-review.dtbo"
fdtput -r "$d/sm6115-dsi-phy-mx-review.dtb" /__symbols__
python3 scripts/audit-dsi-phy-mx-review.py "$base" "$d/sm6115-dsi-phy-mx-review.dtb"
cp "$d/sm6115-dsi-phy-mx-review.dtb" "$tmp/negative.dtb"
fdtput -t s "$tmp/negative.dtb" /soc@0/display-subsystem@5e00000/phy@5e94400 status okay
if python3 scripts/audit-dsi-phy-mx-review.py "$base" "$tmp/negative.dtb" 2>"$tmp/negative.txt"; then
    echo 'Unsafe active fixture accepted' >&2
    exit 1
fi
echo 'PASS: active PHY rejected'
python3 scripts/validate-stage-c-v8.py "$d/sm6115-dsi-phy-mx-review.dtb"
sha256sum "$d/sm6115-dsi-phy-mx-review.dtb"
