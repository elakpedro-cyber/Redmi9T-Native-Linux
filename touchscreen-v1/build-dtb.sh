#!/bin/bash
# Offline only: no kernel build, device access, flashing or source-tree changes.
set -euo pipefail
if [ "${LEMON_TOUCH_DTB_SCRIPT_FROZEN:-0}" != 1 ]; then
    export LEMON_TOUCH_DTB_SCRIPT_FROZEN=1
    exec /bin/bash -c "$(cat "$0")" "$0" "$@"
fi
cd "$(dirname "$0")/.."
project=$PWD
work=/home/hadirpc/Redmi9T-Native-Linux
kernel=$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d
tools=$work/v7-python/bin
out=$project/artifacts/touchscreen-v1/dtb-review
log=$project/logs/touchscreen-v1/dtb-review
mkdir -p "$out" "$log"
sha256sum artifacts/{sm6115-xiaomi-lemon-v8b.dtb,Image-v8b,boot-linux-test-v8b.img,lemon-gnome-physical-lcd-v2.1-aarch64.tar.gz} \
    userspace/gnome-physical-v2.1/session.sh >"$log/baseline-before.sha256"
python3 - "$kernel" "$out/touchscreen-handoff-review-overlay.dts" <<'PY'
from pathlib import Path
import re,sys
kernel,out=map(Path,sys.argv[1:])
text=(kernel/'include/dt-bindings/interrupt-controller/irq.h').read_text()
flag=re.search(r'^#define\s+IRQ_TYPE_EDGE_RISING\s+(0x[0-9a-fA-F]+|[0-9]+)\s*$',text,re.M)
assert flag and int(flag[1],0)==1
review=Path('touchscreen-v1/touch-handoff-review.dtsi').read_text()
review=review.replace('&spi2','&{/soc@0/geniqup@4ac0000/spi@4a88000}')
review=review.replace('IRQ_TYPE_EDGE_RISING',flag[1])
review=review.replace('not applied or compiled into a DTB','offline candidate only; never applied to the phone')
out.write_text('/dts-v1/;\n/plugin/;\n\n'+review)
PY
cp artifacts/sm6115-xiaomi-lemon-v8b.dtb "$log/base-with-symbols.dtb"
# Temporary aliases let fdtoverlay resolve real base phandles, without a
# lossy decompile/recompile or transplanting numbers from another DT.
fdtput -p -t s "$log/base-with-symbols.dtb" /__symbols__ tlmm /soc@0/pinctrl@500000
dtc -@ -I dts -O dtb -o "$out/touchscreen-handoff-review.dtbo" "$out/touchscreen-handoff-review-overlay.dts" 2>"$log/overlay-dtc.txt"
fdtoverlay -i "$log/base-with-symbols.dtb" -o "$out/touchscreen-handoff-review.dtb" "$out/touchscreen-handoff-review.dtbo"
fdtput -r "$out/touchscreen-handoff-review.dtb" /__symbols__
dtc -I dtb -O dts -o "$log/candidate-inspection.dts" "$out/touchscreen-handoff-review.dtb" 2>"$log/candidate-inspection-dtc.txt"
dtc -I dtb -O dts -o "$log/base-inspection.dts" artifacts/sm6115-xiaomi-lemon-v8b.dtb 2>"$log/base-inspection-dtc.txt"
python3 touchscreen-v1/validate-dtb.py
python3 touchscreen-v1/test-dtb.py | tee "$log/negative-tests.txt"
stage=$(mktemp -d "$work/touch-v1-schema.XXXXXX")
cp -a "$kernel/Documentation/devicetree/bindings" "$stage/"
cp touchscreen-v1/bindings/xiaomi,lemon-nt36672a-handoff.yaml "$stage/bindings/input/touchscreen/"
"$tools/dt-doc-validate" "$stage/bindings/input/touchscreen/xiaomi,lemon-nt36672a-handoff.yaml" >"$log/local-binding.txt" 2>&1
test ! -s "$log/local-binding.txt"
"$tools/dt-mk-schema" -j -o "$stage/processed.json" "$stage/bindings" >"$log/schema-build.txt" 2>&1
"$tools/dt-validate" -s "$stage/processed.json" artifacts/sm6115-xiaomi-lemon-v8b.dtb >"$log/base-schema.txt" 2>&1
"$tools/dt-validate" -s "$stage/processed.json" "$out/touchscreen-handoff-review.dtb" >"$log/candidate-schema.txt" 2>&1
test ! -s "$log/base-schema.txt"
test ! -s "$log/candidate-schema.txt"
sha256sum -c "$log/baseline-before.sha256" | tee "$log/baseline-after.txt"
printf '%s\n' "$stage" >"$log/schema-stage.txt"
printf '%s\n' OFFLINE_TOUCH_DTB_BUILD_AND_SCHEMA_PASS | tee "$log/result.txt"
