#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
sdk=/home/hadirpc/Redmi9T-Native-Linux/gnome50-build.hT7bPE
stage=$(mktemp -d "$sdk/build/lemon-touch-client.XXXXXX")
tarball=touchscreen-v1/sources/freerdp/FreeRDP-3.32.2.tar.gz
[ -f "$tarball" ] || tarball=downloads/touchscreen-v1/FreeRDP-3.32.2.tar.gz
tar -xzf "$tarball" -C "$stage"
src=$stage/FreeRDP-3.32.2
python3 - "$src" <<'PY'
from pathlib import Path
import sys,difflib
root=Path(sys.argv[1])
f=root/'client/Wayland/wlf_input.c';s=f.read_text();old=s
needle='FREERDP_TOUCH_MOTION, 0,\n\t                                   WINPR_ASSERTING_INT_CAST(uint32_t, ev->id), x, y)'
assert s.count(needle)==1
s=s.replace(needle,'FREERDP_TOUCH_MOTION, ev->id,\n\t                                   0, x, y)')
f.write_text(s)
patch=''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/client/Wayland/wlf_input.c',tofile='b/client/Wayland/wlf_input.c'))
f=root/'client/Wayland/wlfreerdp.c';s=f.read_text();old=s
needle='\t\t\tcase UWAC_EVENT_TOUCH_UP:'
assert s.count(needle)==1
s=s.replace(needle,'\t\t\tcase UWAC_EVENT_TOUCH_CANCEL:\n\t\t\t\tif (!freerdp_client_handle_touch(&context->common, FREERDP_TOUCH_CANCEL, 0, 0, 0, 0))\n\t\t\t\t\treturn FALSE;\n\t\t\t\tbreak;\n\n'+needle)
f.write_text(s)
patch+=''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/client/Wayland/wlfreerdp.c',tofile='b/client/Wayland/wlfreerdp.c'))
Path('touchscreen-v1/freerdp-touch.patch').write_text(patch)
PY
p=${src#"$sdk"}
chroot "$sdk" cmake -S "$p" -B "$p/out" -GNinja -DCMAKE_BUILD_TYPE=Release \
 -DWITH_CLIENT_SDL=OFF -DWITH_CLIENT_X11=OFF -DWITH_X11=OFF -DWITH_WAYLAND=ON \
 -DWITH_CLIENT_WAYLAND=ON -DWITH_SERVER=OFF -DWITH_SAMPLE=OFF -DWITH_PROXY=OFF \
 -DWITH_FFMPEG=OFF -DWITH_OPUS=OFF -DWITH_FAAC=OFF -DWITH_FAAD2=OFF -DWITH_GSM=OFF \
 -DWITH_CUPS=OFF -DWITH_PULSE=OFF -DWITH_ALSA=OFF -DWITH_OSS=OFF -DWITH_FUSE=OFF \
 -DWITH_MANPAGES=OFF -DWITH_PCSC=OFF -DWITH_SWSCALE=OFF -DWITH_OPENH264=OFF \
 -DWITH_OPENSSL=ON -DWITH_MBEDTLS=OFF -DWITH_SANITIZE_ADDRESS=OFF
chroot "$sdk" cmake --build "$p/out" --target wlfreerdp -j4
chroot "$sdk" patchelf --remove-rpath "$p/out/client/Wayland/wlfreerdp"
chroot "$sdk" patchelf --remove-rpath "$p/out/uwac/libuwac/libuwac0.so.0.2.0"
cp "$src/out/uwac/libuwac/libuwac0.so.0.2.0" artifacts/touchscreen-v1/libuwac0.so.0
cp "$src/out/client/Wayland/wlfreerdp" artifacts/touchscreen-v1/wlfreerdp3-touch
printf '%s\n' "$src" >logs/touchscreen-v1/client-build-stage.txt
