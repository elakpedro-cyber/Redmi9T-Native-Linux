#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
src="$PWD/userspace/gnome-physical-v2"
out="$PWD/artifacts/gnome-physical-v2"
sdk=/home/hadirpc/Redmi9T-Native-Linux/gnome50-build.hT7bPE
mkdir -p "$out"
for name in watchdog vt-cleanup drm-probe; do
    aarch64-linux-gnu-gcc -O2 -static -Wall -Wextra -Werror "$src/$name.c" -o "$out/$name"
done
work=$(mktemp -d "$sdk/tmp/physical-v2-build.XXXXXX")
trap 'rm -rf "$work"' EXIT
cp "$src"/{frame-trace.c,frame-trace.S,dbus-trace.c} "$work/"
inside=${work#"$sdk"}
chroot "$sdk" /usr/bin/gcc -O2 -fPIC -shared -Wall -Wextra -Werror \
    -I/usr/include/pipewire-0.3 -I/usr/include/spa-0.2 \
    "$inside/frame-trace.c" "$inside/frame-trace.S" -o "$inside/frame-trace.so" \
    -lwayland-client -lpipewire-0.3 -ldl
chroot "$sdk" /bin/sh -c "gcc -O2 -fPIC -shared -Wall -Wextra -Werror \
    \$(pkg-config --cflags gio-2.0) '$inside/dbus-trace.c' \
    -o '$inside/dbus-trace.so' \$(pkg-config --libs gio-2.0) -ldl"
cp "$work/"*.so "$out/"
for script in "$src/"*.sh; do sh -n "$script"; done
file "$out/"*.so "$out/watchdog" "$out/vt-cleanup" "$out/drm-probe"
sha256sum "$out/"*.so "$out/watchdog" "$out/vt-cleanup" "$out/drm-probe" > logs/gnome-physical-v2/build-sha256.txt
