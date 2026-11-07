#!/bin/sh
set -eu
umask 077
ulimit -c 0

if [ "${1:-}" = session ]; then
    test "$(id -u)" -ne 0
    test "$(stat -c '%u:%a' "$XDG_RUNTIME_DIR")" = "$(id -u):700"
    test -S "$WAYLAND_DISPLAY"
    case "${LEMON_PHYSICAL_VIEWER:-rdp}" in
        rdp) exec /bin/sh /run/lemon/user-session.sh ;;
        devkit) exec /bin/sh /run/lemon/devkit-session.sh ;;
        *) exit 2 ;;
    esac
fi

if [ "${1:-}" = inner ]; then
    base=$2
    limit=$3
    mode=$4
    test "$(readlink /proc/self/ns/mnt)" != "$5"
    w=$base/weston
    g=$base/gnome
    viewer=${LEMON_PHYSICAL_VIEWER:-rdp}
    client= gnome= weston= bus=
    shutdown() {
        trap - EXIT TERM INT HUP
        set +e
        [ ! -d "$g/run/lemon" ] || touch "$g/run/lemon/stop-requested"
        for component in "rdp-client:$client" "gnome-session:$gnome" "weston:$weston" "system-bus:$bus"; do
            pid=${component#*:}
            [ -n "$pid" ] || continue
            printf 'NAMESPACE_STOP component=%s pid=%s\n' "${component%:*}" "$pid"
            case "$component" in
                gnome-session:*) : ;; # Its user-session watcher handles the stop request and waits for children.
                *) kill -TERM "$pid" 2>/dev/null ;;
            esac
            wait "$pid" 2>/dev/null
        done
        kill -TERM -1 2>/dev/null
        wait
    }
    trap shutdown EXIT
    trap 'exit 0' TERM INT HUP
    for root in "$w" "$g"; do
        mkdir -p "$root"/dev "$root"/proc "$root"/sys "$root"/run "$root"/tmp
        mount -t proc proc "$root/proc"
        mount -o bind /sys "$root/sys"
        mount -o remount,bind,ro "$root/sys"
        for name in null zero random urandom; do
            [ ! -e "$root/dev/$name" ] || exit 11
            case "$name" in null) minor=3;; zero) minor=5;; random) minor=8;; urandom) minor=9;; esac
            mknod -m 666 "$root/dev/$name" c 1 "$minor"
        done
    done
    mkdir -p "$w/tmp/runtime" "$g/run/parent" "$g/run/lemon" "$g/dev/shm" "$g/dev/pts" "$g/var/lib/dbus"
    chmod 700 "$w/tmp/runtime"
    chmod 711 "$g/run"
    chmod 755 "$g/dev"
    chmod 1777 "$g/tmp"
    mkdir -m 1777 "$g/tmp/.ICE-unix"
    mount -t tmpfs -o mode=1777,nosuid,nodev,size=128m tmpfs "$g/dev/shm"
    mount -t devpts -o newinstance,ptmxmode=0666,mode=0620 devpts "$g/dev/pts"
    ln -s pts/ptmx "$g/dev/ptmx"
    mount -o bind "$w/tmp/runtime" "$g/run/parent"
    mount -o remount,bind,ro "$g/run/parent"
    cp "$0" "$g/run/lemon-session.sh"
    chmod 644 "$g/run/lemon-session.sh"
    uid=$(chroot "$g" /bin/busybox id -u lemon)
    gid=$(chroot "$g" /bin/busybox id -g lemon)
    test "$uid" -ne 0
    mkdir "$g/run/lemon/home"
    chown "$uid:$gid" "$g/run/lemon" "$g/run/lemon/home"
    chmod 700 "$g/run/lemon"
    for name in user-session.sh devkit-session.sh input.js session-component.js; do
        cp "$base/$name" "$g/run/lemon/$name"
        chmod 644 "$g/run/lemon/$name"
    done
    cp "$base/frame-trace.so" "$g/run/lemon/frame-trace.so"
    chmod 644 "$g/run/lemon/frame-trace.so"
    if [ "$viewer" = devkit ]; then
        cp "$base/dbus-trace.so" "$g/run/lemon/dbus-trace.so"
        chmod 644 "$g/run/lemon/dbus-trace.so"
        if [ ! -e "$g/usr/libexec/mutter-devkit.real" ]; then
            mv "$g/usr/libexec/mutter-devkit" "$g/usr/libexec/mutter-devkit.real"
            cat >"$g/usr/libexec/mutter-devkit" <<'DEVKIT'
#!/bin/sh
export LD_PRELOAD=/run/lemon/dbus-trace.so
export GDK_BACKEND=wayland GSK_RENDERER=cairo
exec /usr/libexec/mutter-devkit.real "$@"
DEVKIT
            chmod 755 "$g/usr/libexec/mutter-devkit"
        fi
    fi
    cp "$base/frame-trace.so" "$w/run/frame-trace.so"
    chmod 644 "$w/run/frame-trace.so"
    cat >"$g/run/lemon/gnome-shell" <<'WRAPPER'
#!/bin/sh
export LD_PRELOAD=/run/lemon/frame-trace.so
export LEMON_FRAME_TRACE=/run/lemon/gnome-frames.jsonl
exec /usr/bin/gjs -m /run/lemon/session-component.js "$@"
WRAPPER
    chmod 755 "$g/run/lemon/gnome-shell"
    shell_entry="$g/usr/share/applications/lemon-headless-shell.desktop"
    sed -e 's|^Exec=.*|Exec=/run/lemon/gnome-shell --wayland --headless --no-x11|' \
        "$shell_entry" >"$base/shell.desktop"
    if [ "$viewer" = devkit ]; then
        sed 's/ --headless/ --devkit --wayland-display=lemon-gnome/' "$base/shell.desktop" >"$shell_entry.new"
    else
        cp "$base/shell.desktop" "$shell_entry.new"
    fi
    chmod 644 "$shell_entry.new"
    mv "$shell_entry.new" "$shell_entry"
    cp "$g/run/lemon/input.js" "$g/run/lemon/physical-input.js"
    chmod 644 "$g/run/lemon/physical-input.js"
    actions=0
    if [ "${LEMON_TEST_ACTIONS:-0}" = 1 ]; then
        actions=1
    fi
    chroot "$g" /usr/bin/dbus-uuidgen --ensure=/var/lib/dbus/machine-id
    cat >"$g/run/bus.conf" <<'EOF'
<busconfig>
  <type>system</type>
  <listen>unix:path=/run/lemon/system-bus</listen>
  <policy context="default"><allow user="lemon"/></policy>
  <policy user="lemon"><allow send_destination="*"/><allow receive_sender="*"/></policy>
</busconfig>
EOF
    chroot "$g" /usr/bin/dbus-daemon --nofork --config-file=/run/bus.conf >"$base/system-bus.log" 2>&1 &
    bus=$!
    for _ in $(seq 1 20); do [ ! -S "$g/run/lemon/system-bus" ] || break; sleep .1; done
    test -S "$g/run/lemon/system-bus"
    if [ "$viewer" = rdp ]; then
        ip link set lo up
        cp "$g/usr/local/libexec/lemon/check-private-net.sh" "$g/tmp/gnome50-check-private-net.sh"
        chmod 644 "$g/tmp/gnome50-check-private-net.sh"
        chroot "$w" /usr/bin/openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=lemon-private-loopback \
            -keyout /tmp/rdp.key -out /tmp/rdp.crt >"$base/tls-setup.log" 2>&1
        cp "$w/tmp/rdp.key" "$g/run/lemon/rdp-test.key"
        cp "$w/tmp/rdp.crt" "$g/run/lemon/rdp-test.crt"
        pin=$(chroot "$w" /usr/bin/openssl x509 -in /tmp/rdp.crt -noout -fingerprint -sha256 | cut -d= -f2)
        password=$(chroot "$w" /usr/bin/openssl rand -hex 24)
        printf '%s\n' lemon-local "$password" >"$g/run/lemon/rdp-credentials"
        printf '%s\n' "$password" >"$w/tmp/client-credential"
        unset password
        chmod 600 "$g/run/lemon"/rdp-* "$w/tmp/client-credential"
        chown "$uid:$gid" "$g/run/lemon"/rdp-*
    fi
    export XDG_RUNTIME_DIR=/tmp/runtime HOME=/tmp LIBSEAT_BACKEND=seatd
    if [ "$mode" = offline ]; then
        backend=headless
        if [ -n "${LEMON_OFFLINE_X11:-}" ]; then
            mkdir "$w/tmp/.X11-unix"
            mount -o bind /tmp/.X11-unix "$w/tmp/.X11-unix"
            export DISPLAY="$LEMON_OFFLINE_X11"
            backend=x11
        fi
        chroot "$w" /usr/bin/weston --backend="$backend" --width=720 --height=1280 \
            --renderer=pixman --shell=kiosk --no-config --idle-time=0 \
            --socket=lemon-physical --debug --log=/tmp/weston.log >"$base/seat.log" 2>&1 &
        offline=1
    else
        mkdir "$g/dev/dri" "$w/dev/dri"
        chmod 755 "$g/dev/dri"
        mknod -m 600 "$g/dev/dri/renderD128" c 226 128
        chown "$uid:$gid" "$g/dev/dri/renderD128"
        mknod "$w/dev/dri/card0" c 226 0
        mknod "$w/dev/tty0" c 4 0
        mknod "$w/dev/tty2" c 4 2
        mknod "$w/dev/tty" c 5 0
        /bin/busybox openvt -s -w -c 2 -- /bin/busybox chroot "$w" /bin/busybox sh -c '
            exec /usr/bin/seatd-launch -- /usr/bin/weston --backend=drm --drm-device=card0 \
                --renderer=pixman --current-mode --continue-without-input --shell=kiosk \
                --no-config --idle-time=0 --socket=lemon-physical --debug --log=/tmp/weston.log >/tmp/seat.log 2>&1
        ' &
        offline=0
    fi
    weston=$!
    for _ in $(seq 1 35); do
        [ ! -S "$w/tmp/runtime/lemon-physical" ] || break
        kill -0 "$weston"
        sleep .1
    done
    test -S "$w/tmp/runtime/lemon-physical"
    chmod 711 "$w/tmp/runtime"
    chown "0:$gid" "$w/tmp/runtime/lemon-physical"
    chmod 660 "$w/tmp/runtime/lemon-physical"
    if [ "${LEMON_CAPTURE:-0}" = 1 ]; then
        WAYLAND_DISPLAY=lemon-physical chroot "$w" /usr/bin/weston-debug timeline \
            >"$w/tmp/timeline.jsonl" 2>"$w/tmp/timeline.log" &
    fi
    chroot "$g" /bin/busybox su -s /bin/sh lemon -c 'exec /bin/busybox env -i \
        PATH=/usr/local/bin:/usr/bin:/bin HOME=/run/lemon/home XDG_RUNTIME_DIR=/run/lemon \
        WAYLAND_DISPLAY=/run/parent/lemon-physical DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/lemon/system-bus \
        G_MESSAGES_DEBUG=mdk LEMON_PHYSICAL_ACTIONS='"$actions"' LEMON_PHYSICAL_VIEWER='"$viewer"' LEMON_PROFILE='"${LEMON_PROFILE:-baseline}"' LEMON_PHYSICAL_OFFLINE='"$offline"' /bin/sh /run/lemon-session.sh session' >"$base/gnome.log" 2>&1 &
    gnome=$!
    if [ "$viewer" = rdp ]; then
        for _ in $(seq 1 90); do
            if grep -q ':0D3D .* 0A ' /proc/net/tcp /proc/net/tcp6; then break; fi
            kill -0 "$gnome"
            sleep .2
        done
        grep -q ':0D3D .* 0A ' /proc/net/tcp /proc/net/tcp6
        WAYLAND_DISPLAY=lemon-physical chroot "$w" /bin/busybox sh -c \
            'export LD_PRELOAD=/run/frame-trace.so LEMON_FRAME_TRACE=/tmp/rdp-frames.jsonl; exec /usr/bin/wlfreerdp3 /v:127.0.0.1 /u:lemon-local /from-stdin:force /sec:nla \
             "/cert:fingerprint:sha256:$1" /size:1080x2340 /f -clipboard /log-level:WARN </tmp/client-credential' \
            local-rdp "$pin" >"$base/client.log" 2>&1 &
        client=$!
        touch "$g/run/lemon/client-started"
    fi
    for _ in $(seq 1 "$((limit / 2))"); do
        sleep 2
        kill -0 "$weston"
        kill -0 "$gnome"
        if [ "${LEMON_CAPTURE:-0}" = 1 ] && grep -q 'Using Wayland display name' "$base/gnome.log" "$g/run/lemon/gnome.log" 2>/dev/null; then
            WAYLAND_DISPLAY=lemon-physical chroot "$w" /bin/busybox sh -c 'cd /tmp; exec /usr/bin/weston-screenshooter' \
                >>"$base/capture.log" 2>&1 || :
        fi
    done
    sleep "$limit"
    exit
fi

base=$1
limit=$2
mode=${3:-hardware}
case "$limit" in ''|*[!0-9]*) exit 2;; esac
[ "$limit" -ge 10 ] && [ "$limit" -le 3600 ] || exit 2
case "$mode" in hardware|offline) ;; *) exit 2;; esac
if [ "$mode" = hardware ]; then
    test "$(uname -r)" = 7.4.0-rc1-lemon-bringup-v8b
    test "$(stat -f -c %T "$base")" = tmpfs
    test "$(cat /sys/class/drm/card0-Unknown-1/modes)" = 1080x2340
    test "$(cat /sys/class/drm/renderD128/dev)" = 226:128
    test "$(basename "$(readlink /sys/class/drm/renderD128/device/driver)")" = adreno
    test "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = 1
    p=/sys/bus/platform/devices
    test "$(cat "$p/5e00000.display-subsystem/driver_override")" = lemon-stage-b-hold
    test ! -L "$p/5e00000.display-subsystem/driver"
    test ! -L "$p/5f00000.clock-controller/driver"
    test -z "$(ls -A /sys/bus/mipi-dsi/devices)"
    test ! -d /sys/class/backlight
    awk '/^MemAvailable:/ {exit !($2 >= 1048576)}' /proc/meminfo
    "$base/probe" /dev/tty1
fi

cleanup() {
    rc=$?
    trap - EXIT
    rm -f "$base/gnome/run/lemon/rdp-test.key" "$base/gnome/run/lemon/rdp-credentials" \
        "$base/weston/tmp/rdp.key" "$base/weston/tmp/client-credential"
    if [ "$mode" = hardware ]; then
        /bin/busybox timeout -k 1 5 "$base/vt-cleanup" 1 2 || exit 12
        test "$(cat /sys/class/tty/tty0/active)" = tty1 || exit 12
        printf '\r\nLEMON GNOME V2 ENDED - TTY1 RESTORED\r\n' >/dev/tty1
    fi
    exit "$rc"
}
trap cleanup EXIT
"$base/watchdog" "$limit" /bin/sh "$0" inner "$base" "$limit" "$mode" "$(readlink /proc/self/ns/mnt)" &
watchdog=$!
printf '%s\n' "$watchdog" >"$base/watchdog.pid"
awk '{print $22}' "/proc/$watchdog/stat" >"$base/watchdog.start"
stop() {
    kill -TERM "$watchdog" 2>/dev/null || :
    wait "$watchdog" || :
    exit 143
}
trap stop HUP INT TERM
wait "$watchdog"
