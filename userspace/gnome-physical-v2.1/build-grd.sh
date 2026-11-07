#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
project=$PWD
sdk=/home/hadirpc/Redmi9T-Native-Linux/gnome50-build.hT7bPE
echo '089049119e1f2442fe9773f0285365cedc207f4cbc7ce9af388e153668e2b171  downloads/gnome-physical-v2.1/gnome-remote-desktop-50.1.tar.xz' | sha256sum -c
work=$(mktemp -d "$sdk/build/grd-v21.XXXXXX")
tar -xJf downloads/gnome-physical-v2.1/gnome-remote-desktop-50.1.tar.xz -C "$work"
src="$work/gnome-remote-desktop-50.1"
cp "$src/src/grd-egl-thread.c" "$work/grd-egl-thread.original.c"
python3 - "$src/src/grd-egl-thread.c" <<'PY'
from pathlib import Path
import sys
file = Path(sys.argv[1]); text = file.read_text()
needle = '  egl_thread = g_new0 (GrdEglThread, 1);'
assert text.count(needle) == 1
text = text.replace(needle, needle + '\n  egl_thread->drm_render_node_fd = -1;\n  egl_thread->impl.drm_render_node_fd = -1;')
file.write_text(text)
PY
diff -u "$work/grd-egl-thread.original.c" \
    "$src/src/grd-egl-thread.c" > userspace/gnome-physical-v2.1/grd-egl-fd-init.patch || [ "$?" = 1 ]
inside=${src#"$sdk"}
chroot "$sdk" /usr/bin/meson setup "$inside/out" "$inside" --prefix=/usr --libexecdir=libexec \
    --buildtype=debugoptimized -Dsystemd=false -Dtests=false -Dman=false
chroot "$sdk" /usr/bin/meson compile -C "$inside/out" -j4
cp "$src/out/src/gnome-remote-desktop-daemon" "$project/artifacts/gnome-physical-v2.1/gnome-remote-desktop-daemon"
printf '%s\n' "$work" > logs/gnome-physical-v2.1/grd-build-stage.txt
sha256sum artifacts/gnome-physical-v2.1/gnome-remote-desktop-daemon
