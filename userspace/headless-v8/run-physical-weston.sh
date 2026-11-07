#!/bin/sh
# The watchdog starts the inner branch in private PID, mount and network namespaces.
set -eu
umask 077

if [ "${1:-}" = inner ]; then
    base=$2
    [ "$(readlink /proc/self/ns/mnt)" != "$3" ] || exit 11
    r=$base/root
    mount -t proc proc "$r/proc"
    mount -o bind /sys "$r/sys"
    mount -o remount,bind,ro "$r/sys"
    mkdir -p "$r/dev/dri" "$r/tmp/runtime"
    chmod 700 "$r/tmp/runtime"
    mknod "$r/dev/dri/card0" c 226 0
    mknod "$r/dev/tty0" c 4 0
    mknod "$r/dev/tty2" c 4 2
    mknod "$r/dev/tty" c 5 0
    mknod "$r/dev/null" c 1 3
    mknod "$r/dev/urandom" c 1 9
    mknod "$r/dev/random" c 1 8
    export PATH=/usr/bin:/bin HOME=/tmp XDG_RUNTIME_DIR=/tmp/runtime
    export LIBSEAT_BACKEND=seatd
    exec /bin/busybox openvt -s -w -c 2 -- /bin/busybox chroot "$r" \
        /bin/busybox sh -c 'exec /bin/busybox timeout -k 1 26 /usr/bin/seatd-launch -- /usr/bin/weston \
            --backend=drm --drm-device=card0 --renderer=pixman --current-mode \
            --continue-without-input --shell=desktop --no-config --idle-time=0 \
            --socket=lemon-physical --log=/tmp/weston.log >/tmp/seat.log 2>&1'
fi

base=$1
test "$(uname -r)" = 7.4.0-rc1-lemon-bringup-v8b
test "$(cat /sys/class/tty/tty0/active)" = tty1
test "$(basename "$(readlink /sys/class/drm/card0/device/driver)")" = simple-framebuffer
test "$(cat /sys/class/drm/card0-Unknown-1/modes)" = 1080x2340
test "$(cat /sys/bus/platform/devices/5e00000.display-subsystem/driver_override)" = lemon-stage-b-hold
test ! -L /sys/bus/platform/devices/5e00000.display-subsystem/driver
test ! -L /sys/bus/platform/devices/5f00000.clock-controller/driver
# Avoid taking a VT that was opened since the initial DRM probe.
"$base/probe" /dev/tty1

cleanup() {
    rc=$?
    trap - EXIT
    set +e
    /bin/busybox timeout -k 1 4 "$base/probe" --restore-tty1
    restored=$?
    printf 'session_rc=%s restore_rc=%s active=%s\n' "$rc" "$restored" "$(cat /sys/class/tty/tty0/active)"
    if [ -r "$base/root/tmp/weston.log" ]; then
        echo '=== Weston log ==='
        cat "$base/root/tmp/weston.log"
    fi
    if [ -r "$base/root/tmp/seat.log" ]; then
        echo '=== Seat log ==='
        cat "$base/root/tmp/seat.log"
    fi
    if [ "$restored" = 0 ] && [ "$(cat /sys/class/tty/tty0/active)" = tty1 ]; then
        printf '\r\nLEMON WESTON TEST ENDED - TTY1 RESTORED\r\n' >/dev/tty1
    else
        exit 12
    fi
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

ns=$(readlink /proc/self/ns/mnt)
"$base/watchdog" 30 /bin/sh "$0" inner "$base" "$ns"
