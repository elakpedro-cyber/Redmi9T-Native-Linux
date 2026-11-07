#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
src=$PWD/userspace/gnome-physical-v2.1
sdk=/home/hadirpc/Redmi9T-Native-Linux/gnome50-build.hT7bPE
stage=$(cat logs/gnome-physical-v2.1/grd-build-stage.txt)
# The build record contains the SDK path; use its existing compiled objects.
stage=${stage#"$sdk"}/gnome-remote-desktop-50.1
[[ "$stage" = /build/grd-v21.*/gnome-remote-desktop-50.1 ]]
work=$(mktemp -d "$sdk/tmp/grd-negative.XXXXXX")
trap 'rm -rf "$work"' EXIT
cp "$src/test-grd-egl-failure.c" "$work/"
cp /home/hadirpc/Redmi9T-Native-Linux/physical-v21-sources/gnome-remote-desktop-50.1/src/grd-egl-thread.c "$work/old.c"
inside=${work#"$sdk"}
chroot "$sdk" /bin/sh -s -- "$stage" "$inside" <<'EOF'
set -eu
stage=$1
work=$2
flags="$(pkg-config --cflags gio-2.0 epoxy libdrm) -I$stage/out -I$stage/src"
libs="$(pkg-config --libs gio-2.0 epoxy libdrm)"
obj=$stage/out/src/gnome-remote-desktop-daemon.p
gcc -O2 $flags -c "$work/old.c" -o "$work/old.o"
for kind in old fixed; do
    object=$work/old.o
    [ "$kind" != fixed ] || object=$obj/grd-egl-thread.c.o
    gcc -O2 -Wall -Wextra -Werror $flags "$work/test-grd-egl-failure.c" "$object" "$obj/grd-drm-utils.c.o" $libs -o "$work/test-$kind"
    "$work/test-$kind" "$kind"
done
EOF
echo GRD_EGL_FAILURE_OLD_BUG_REPRODUCED_FIXED_STDIN_PRESERVED
