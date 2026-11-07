#!/bin/sh
set -eu
umask 077
fail() { echo "$*" >&2; exit 1; }
r=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$r" in /tmp/*/runtime) ;; *) echo "Run from a private /tmp bundle" >&2; exit 2;; esac
state=$r/session
export LD_LIBRARY_PATH=$r/usr/lib:$r/usr/lib/weston
export GBM_BACKENDS_PATH=$r/usr/lib/gbm
export LIBGL_DRIVERS_PATH=$r/usr/lib/dri
export XKB_CONFIG_ROOT=$r/usr/share/X11/xkb
export FONTCONFIG_PATH=$r/etc/fonts
export XDG_DATA_DIRS=$r/usr/share
export XDG_DATA_HOME=$r/usr/share
export XDG_CACHE_HOME=$r/session/cache
export XDG_RUNTIME_DIR=$state
export WAYLAND_DISPLAY=lemon-desktop
export MESA_SHADER_CACHE_DISABLE=true
unset LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER MESA_LOADER_DRIVER_OVERRIDE
export WESTON_MODULE_MAP="headless-backend.so=$r/usr/lib/libweston-14/headless-backend.so;gl-renderer.so=$r/usr/lib/libweston-14/gl-renderer.so;desktop-shell.so=$r/usr/lib/weston/desktop-shell.so;weston-desktop-shell=$r/usr/libexec/weston-desktop-shell;weston-keyboard=$r/usr/libexec/weston-keyboard"
case "${1:-}" in
input) exec "$r/usr/local/bin/lemon-desktop" input "$state/input";;
stop) printf '%s\n' quit | "$r/usr/local/bin/lemon-desktop" input "$state/input"; exit;;
capture)
    test -S "$state/input"
    mkdir "$state/capture.lock" || fail "Another capture is in progress"
    capture=$state/capture.lock
    trap 'rm -rf -- "$capture"' EXIT
    frame=$(cat "$state/input.frame")
    if [ -s "$state/last.png" ] && [ "$frame" = "$(cat "$state/last.frame" 2>/dev/null || :)" ]; then
        cat "$state/last.png"
        exit
    fi
    cd "$capture"
    /bin/busybox timeout -s TERM -k 1 4 "$r/usr/bin/weston-screenshooter" >&2
    set -- wayland-screenshot-*.png
    test "$#" -eq 1 && test -s "$1"
    mv "$1" "$state/last.png"
    printf '%s\n' "$frame" > "$state/last.frame"
    cat "$state/last.png"
    exit;;
start) ;;
*) echo "Usage: desktop.sh start [gl|pixman], capture, input, stop" >&2; exit 2;;
esac
mode=${2:-gl}
case "$mode" in gl|pixman) ;; *) exit 2;; esac
if [ "${LEMON_OFFLINE_TEST:-0}" != 1 ] || [ "$mode" = gl ]; then
    awk '$2=="/tmp" && $3=="tmpfs" {ok=1} END {exit !ok}' /proc/mounts ||
        fail "A verified RAM tmpfs at /tmp is required"
    test "$(wc -l </proc/swaps)" -eq 1
    if grep -q '^/dev/' /proc/mounts; then fail 'Disk-backed mount present'; fi
fi
if [ "$mode" = gl ]; then
    p=/sys/bus/platform/devices
    test "$(uname -r)" = 7.4.0-rc1-lemon-bringup-v8b
    test -c /dev/dri/renderD128 && test "$(cat /sys/class/drm/renderD128/dev)" = 226:128 ||
        fail "Adreno renderD128 unavailable; use explicit pixman mode only if desired"
    test "$(basename "$(readlink /sys/class/drm/renderD128/device/driver)")" = adreno
    test "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = 1
    test "$(cat "$p/5e00000.display-subsystem/driver_override")" = lemon-stage-b-hold
    test ! -L "$p/5e00000.display-subsystem/driver"
    test ! -d /sys/module/dispcc_sm6115
    test ! -e "$p/5e94000.dsi"
    test ! -e "$p/5e94400.phy"
    test ! -d /sys/class/backlight
    test -z "$(ls -A /sys/bus/mipi-dsi/devices)"
fi
mkdir "$state"
pid=
client=
cleanup() {
    if [ -n "$client" ]; then kill "$client" 2>/dev/null || :; wait "$client" 2>/dev/null || :; fi
    if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || :; wait "$pid" 2>/dev/null || :; fi
    rm -rf -- "$state"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
cat > "$state/weston.ini" <<EOF
[shell]
background-image=$r/usr/share/weston/pattern.png
panel-position=none
locking=false
[launcher]
icon=$r/usr/share/weston/terminal.png
path=$r/usr/bin/weston-simple-shm
EOF
"$r/usr/bin/weston" --backend=headless --renderer="$mode" --width=360 --height=800 \
    --config="$state/weston.ini" --debug --idle-time=0 --socket="$WAYLAND_DISPLAY" \
    --log="$r/weston.log" >"$r/weston.stderr" 2>&1 &
pid=$!
for delay in 1 2 3 4 5; do
    [ ! -S "$state/$WAYLAND_DISPLAY" ] || break
    kill -0 "$pid"; sleep 1
done
test -S "$state/$WAYLAND_DISPLAY"
if [ "$mode" = gl ]; then
    grep -Eq 'GL renderer: (FD610|Adreno [(]TM[)] 610)([^0-9]|$)' "$r/weston.log" ||
        { echo "FD610 unavailable. Stop and use explicit pixman mode only if desired." >&2; exit 1; }
    if grep -Eiq 'GL renderer:.*(llvmpipe|softpipe|swrast)' "$r/weston.log"; then
        fail "Software fallback rejected"
    fi
    found=
    for fd in /proc/"$pid"/fd/*; do
        if [ "$(readlink "$fd" 2>/dev/null || :)" = /dev/dri/renderD128 ]; then found=yes; fi
    done
    test "$found" = yes
fi
"$r/usr/local/bin/lemon-desktop" "$mode" "$state/input" >"$r/client.log" 2>&1 &
client=$!
for delay in 1 2 3 4 5; do
    [ ! -S "$state/input" ] || break
    kill -0 "$client"; sleep 1
done
test -S "$state/input"
echo "Desktop ready: $mode, 360x800"
wait "$client"
client=
