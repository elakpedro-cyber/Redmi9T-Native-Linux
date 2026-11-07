#!/bin/sh
set -eu
umask 077
fail() { echo "$*" >&2; exit 1; }
r=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$r" in /tmp/*/runtime) ;; *) fail 'Use a private /tmp bundle';; esac
state=$r/session
export LD_LIBRARY_PATH=$r/usr/lib:$r/usr/lib/pulseaudio
export PATH=$r/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin
export GBM_BACKENDS_PATH=$r/usr/lib/gbm LIBGL_DRIVERS_PATH=$r/usr/lib/dri
export XKB_CONFIG_ROOT=$r/usr/share/X11/xkb
export FONTCONFIG_PATH=$r/etc/fonts XDG_DATA_HOME=$r/usr/share XDG_DATA_DIRS=$r/usr/share
export XDG_RUNTIME_DIR=$state XDG_CONFIG_HOME=$r/config XDG_CACHE_HOME=$state/cache
export XDG_CONFIG_DIRS=$r/config XDG_SESSION_TYPE=wayland
export GDK_BACKEND=wayland GSK_RENDERER=cairo SHELL=/bin/sh
export MESA_SHADER_CACHE_DISABLE=true
unset LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER MESA_LOADER_DRIVER_OVERRIDE WLR_RENDERER_ALLOW_SOFTWARE
unset WAYLAND_DISPLAY WAYLAND_SOCKET DISPLAY SWAYSOCK I3SOCK
case "${1:-}" in
stream)
    test -S "$state/vnc.sock"
    exec "$r/usr/bin/socat" STDIO "UNIX-CONNECT:$state/vnc.sock";;
start) ;;
*) fail 'Usage: session.sh start [gles2|offline-pixman] or stream';;
esac
mode=${2:-gles2}
case "$mode" in
gles2)
    p=/sys/bus/platform/devices
    test "$(uname -r)" = 7.4.0-rc1-lemon-bringup-v8b
    awk '$2=="/tmp" && $3=="tmpfs" {ok=1} END {exit !ok}' /proc/mounts
    if grep -q '^/dev/' /proc/mounts; then fail 'Disk-backed mount present'; fi
    test "$(wc -l </proc/swaps)" -eq 1
    test -d /dev/shm && test -w /dev/shm || fail "POSIX shared memory requires /dev/shm in RAM"
    test "$(stat -f -c %T /dev/shm)" = tmpfs || fail "/dev/shm must be RAM-backed"
    test -c /dev/dri/renderD128 || fail 'No Adreno render node'
    test "$(cat /sys/class/drm/renderD128/dev)" = 226:128
    test "$(basename "$(readlink /sys/class/drm/renderD128/device/driver)")" = adreno
    test "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = 1
    test "$(cat "$p/5e00000.display-subsystem/driver_override")" = lemon-stage-b-hold
    test ! -L "$p/5e00000.display-subsystem/driver"
    test ! -d /sys/module/dispcc_sm6115
    test ! -e "$p/5e94000.dsi"; test ! -e "$p/5e94400.phy"
    test ! -d /sys/class/backlight
    test -z "$(ls -A /sys/bus/mipi-dsi/devices)"
    export WLR_RENDER_DRM_DEVICE=/dev/dri/renderD128 WLR_RENDERER=gles2;;
offline-pixman)
    test "${LEMON_OFFLINE_TEST:-0}" = 1 || fail 'Software mode reserved for offline tests'
    export WLR_RENDERER=pixman
    unset WLR_RENDER_DRM_DEVICE;;
*) exit 2;;
esac
export WLR_BACKENDS=headless WLR_HEADLESS_OUTPUTS=1
mkdir "$state"
lab=
bar=
term=
vnc=
bus=
cleanup() {
    for pid in "$vnc" "$bar" "$term" "$lab" "$bus"; do
        [ -z "$pid" ] || kill "$pid" 2>/dev/null || :
    done
    for pid in "$vnc" "$bar" "$term" "$lab" "$bus"; do
        [ -z "$pid" ] || wait "$pid" 2>/dev/null || :
    done
    rm -rf -- "$state"
}
trap cleanup EXIT
trap 'exit 1' INT TERM HUP
"$r/usr/bin/labwc" -d -C "$r/config/labwc" >"$r/labwc.log" 2>&1 &
lab=$!
for delay in 1 2 3 4 5; do
    set -- "$state"/wayland-*
    test ! -S "$1" || break
    kill -0 "$lab"; sleep 1
done
test -S "$1"
export WAYLAND_DISPLAY=${1##*/}
if [ "$mode" = gles2 ]; then
    grep -Eq 'GL renderer: (FD610|Adreno [(]TM[)] 610)([^0-9]|$)' "$r/labwc.log" || fail 'Labwc GL renderer is not FD610'
    if grep -Eiq 'GL renderer:.*(llvmpipe|softpipe|swrast)' "$r/labwc.log"; then fail 'Software GL rejected'; fi
    found=
    for fd in /proc/"$lab"/fd/*; do
        node=$(readlink "$fd" 2>/dev/null || :)
        case "$node" in /dev/dri/renderD128) found=yes;; /dev/dri/card*) fail 'Unexpected DRM primary node';; esac
    done
    test "$found" = yes || fail 'Labwc has no renderD128 fd'
fi
"$r/usr/bin/wlr-randr" --output HEADLESS-1 --custom-mode 480x720@30Hz
"$r/usr/bin/wlr-randr" >"$r/output.log"
export DBUS_SESSION_BUS_ADDRESS=unix:path=$state/bus
"$r/usr/bin/dbus-daemon" --nofork --config-file="$r/usr/share/dbus-1/session.conf" \
    --address="$DBUS_SESSION_BUS_ADDRESS" >"$r/dbus.log" 2>&1 &
bus=$!
for delay in 1 2 3 4 5; do
    test ! -S "$state/bus" || break
    kill -0 "$bus"; sleep .2
done
test -S "$state/bus"
"$r/usr/bin/waybar" -c "$r/config/waybar/config" -s "$r/config/waybar/style.css" >"$r/waybar.log" 2>&1 &
bar=$!
"$r/usr/bin/foot" -T 'Lemon terminal' -w 400x205 /bin/sh -c 'uname -a; exec /bin/sh -i' >"$r/foot.log" 2>&1 &
term=$!
"$r/usr/bin/wayvnc" -C "$r/config/wayvnc.conf" -u -S "$state/vnc-control" -f 10 -R -r -p -L info "$state/vnc.sock" >"$r/wayvnc.log" 2>&1 &
vnc=$!
for delay in 1 2 3 4 5; do
    test ! -S "$state/vnc.sock" || break
    kill -0 "$vnc"; sleep 1
done
test -S "$state/vnc.sock"
if ! kill -0 "$bar" 2>/dev/null; then
    echo "Waybar exited; see $r/waybar.log. Labwc and VNC remain available." >&2
    bar=
fi
kill -0 "$term"
echo "Labwc ready ($mode) on private Unix socket"
wait "$lab"
lab=
