#!/bin/bash
# PC-only external-module build. Never loads a module or connects to a phone.
set -euo pipefail
cd "$(dirname "$0")/.."
work=/home/hadirpc/Redmi9T-Native-Linux
kernel=$work/linux-05441d697f7f9a927264f4058cbbc6a03dfcac9d
stage=$(mktemp -d "$work/touch-stage1-r2.XXXXXX")
mkdir -p artifacts/touchscreen-stage1-final logs/touchscreen-stage1-final touchscreen-v1/stage1-r2
sha256sum "$work/kernel-out-v8b/.config" "$work/kernel-out-v8b/arch/arm64/boot/Image" >logs/touchscreen-stage1-final/kernel-before.sha256
cp touchscreen-v1/{nvt-frame.c,nvt-frame.h,lemon-geni-delay.h} "$stage/"
cp touchscreen-v1/sources/linux/spi-geni-qcom.c "$stage/spi-geni-qcom-stage1-r2.c"
python3 touchscreen-v1/patch-geni.py "$stage/spi-geni-qcom-stage1-r2.c"
python3 - "$stage" <<'PY'
from pathlib import Path
import sys
stage=Path(sys.argv[1])
s=Path('touchscreen-v1/nvt-spi.c').read_text()
s=s.replace('static bool stage1_authorized;', 'static bool stage1_authorized;\nstatic bool recording_authorized;\n'
    'module_param(recording_authorized, bool, 0600);\n'
    'MODULE_PARM_DESC(recording_authorized, "Explicit evdev-open permission; not an emergency stop switch");')
needle='''static int nvt_open(struct input_dev *input)
{
\tstruct lemon_nvt *ts = input_get_drvdata(input);
\tint ret = 0;
'''
assert s.count(needle)==1
s=s.replace(needle,needle+'\n\tif (!READ_ONCE(recording_authorized))\n\t\treturn -EPERM;\n')
assert s.count('spi_get_chipselect(spi, 0) != 1')==1
s=s.replace('spi_get_chipselect(spi, 0) != 1','spi_get_chipselect(spi, 0) != 0')
needle='\tif (spi_get_chipselect(spi, 0) != 0'
assert s.count(needle)==1
s=s.replace(needle,'\tif (!device_property_read_bool(dev, "xiaomi,stock-cs0-reviewed"))\n'
    '\t\treturn dev_err_probe(dev, -EPERM, "stock runtime CS0 review required\\n");\n'+needle)
(stage/'nvt-spi.c').write_text(s)
p=stage/'spi-geni-qcom-stage1-r2.c';s=p.read_text()
old='''\t\tret = geni_load_se_firmware(se, GENI_SE_SPI);
\t\tif (ret) {
\t\t\tdev_err(mas->dev, "spi master firmware load failed ret: %d\\n", ret);
\t\t\treturn ret;
\t\t}'''
assert s.count(old)==1
s=s.replace(old,'\t\treturn dev_err_probe(mas->dev, -EOPNOTSUPP,\n'
    '\t\t\t\t     "SPI engine firmware handoff absent; upload forbidden\\n");')
s=s.replace('MODULE_VERSION("lemon-touch-v1")','MODULE_VERSION("lemon-touch-stage1-r2")')
assert 'geni_load_se_firmware(' not in s
p.write_text(s)
PY
printf 'obj-m := lemon_nt36672a_stage1_r2.o spi-geni-qcom-stage1-r2.o\nlemon_nt36672a_stage1_r2-y := nvt-spi.o nvt-frame.o\n' >"$stage/Makefile"
make -C "$kernel" O="$work/kernel-out-v8b" M="$stage" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- W=1 modules
cp "$stage/"*.ko artifacts/touchscreen-stage1-final/
cp "$stage/nvt-spi.c" "$stage/nvt-frame.c" "$stage/spi-geni-qcom-stage1-r2.c" \
    "$stage/nvt-frame.h" "$stage/lemon-geni-delay.h" "$stage/Makefile" touchscreen-v1/stage1-r2/
for module in artifacts/touchscreen-stage1-final/*.ko; do modinfo "$module"; done
sha256sum -c logs/touchscreen-stage1-final/kernel-before.sha256
printf '%s\n' "$stage" >logs/touchscreen-stage1-final/build-stage.txt
