#!/bin/sh
# Run inside the prepared RAM chroot only after the hardware test is authorized.
set -eu
umask 077
renderer=${1:-pixman}
case "$renderer" in
    pixman) ;;
    gl) test -c /dev/dri/renderD128 || { echo "Adreno render node is required" >&2; exit 1; } ;;
    *) exit 2 ;;
esac
export XDG_RUNTIME_DIR=/tmp/weston-test-runtime
export WAYLAND_DISPLAY=lemon-headless
export MESA_SHADER_CACHE_DISABLE=true
mkdir "$XDG_RUNTIME_DIR"
p=
client=
cleanup() {
    if test -n "$client"; then kill "$client" 2>/dev/null || :; wait "$client" || :; fi
    if test -n "$p"; then kill "$p" 2>/dev/null || :; wait "$p" || :; fi
    rm -rf "$XDG_RUNTIME_DIR"
}
trap cleanup EXIT
trap 'exit 1' INT TERM
cd /tmp
weston --backend=headless --renderer="$renderer" --width=320 --height=240 --no-config \
    --debug --idle-time=0 --socket="$WAYLAND_DISPLAY" --log=/tmp/weston-test.log &
p=$!
for delay in 1 2 3 4 5; do
    test ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" || break
    kill -0 "$p"
    sleep 1
done
test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"
if test "$renderer" = gl; then
    if ! grep -Eq 'GL renderer: (FD610|Adreno [(]TM[)] 610)([^0-9]|$)' /tmp/weston-test.log ||
       grep -Eiq 'GL renderer:.*(llvmpipe|softpipe|swrast)' /tmp/weston-test.log; then
        echo "Weston did not select hardware Adreno 610" >&2
        exit 1
    fi
fi
weston-simple-shm > /tmp/wayland-client.log 2>&1 &
client=$!
sleep 1
kill -0 "$client"
weston-screenshooter > /tmp/wayland-capture.log 2>&1
set -- /tmp/wayland-screenshot-*.png
if test "$#" -ne 1 || ! test -s "$1"; then
    cat /tmp/wayland-capture.log >&2
    exit 1
fi
mv "$1" /tmp/lemon-headless.png
sha256sum /tmp/lemon-headless.png
