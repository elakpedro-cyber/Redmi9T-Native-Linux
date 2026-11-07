#!/bin/sh
set -eu
umask 077
ulimit -c 0

if [ "${1:-}" = session ]; then
    test "$(id -u)" -ne 0
    test "$(stat -c '%u:%a' "$XDG_RUNTIME_DIR")" = "$(id -u):700"
    test -S "$WAYLAND_DISPLAY"
    if [ "${LEMON_PHYSICAL_VIEWER:-devkit}" = rdp ]; then
        export XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=GNOME
        export XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share" XDG_CACHE_HOME="$HOME/.cache"
        export LEMON_GNOME_LOG="$XDG_RUNTIME_DIR/gnome.log"
        if [ "${LEMON_PHYSICAL_OFFLINE:-0}" = 1 ]; then
            export LEMON_GNOME_OFFLINE=1 LIBGL_ALWAYS_SOFTWARE=1
        else
            export LEMON_REQUIRE_RENDER_NODE=/dev/dri/renderD128
        fi
        exec dbus-run-session -- /bin/sh -eu -c '
            if [ "${LEMON_GNOME_OFFLINE:-0}" != 1 ]; then
                /bin/sh /usr/local/libexec/lemon/privilege-preflight.sh
            fi
            mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"
            pipewire >"$XDG_RUNTIME_DIR/pipewire.log" 2>&1 &
            /bin/sh /usr/local/libexec/lemon/wait-pipewire.sh "$!"
            wireplumber >"$XDG_RUNTIME_DIR/wireplumber.log" 2>&1 &
            gnome-session --session=lemon-headless --failsafe >"$LEMON_GNOME_LOG" 2>&1 &
            shell=$!
            (
                for _ in $(seq 1 100); do
                    if gdbus introspect --session --dest org.gnome.Mutter.RemoteDesktop --object-path /org/gnome/Mutter/RemoteDesktop >/dev/null 2>&1; then break; fi
                    kill -0 "$shell"
                    sleep .2
                done
                exec /bin/sh /usr/local/libexec/lemon/start-rdp.sh
            ) >"$XDG_RUNTIME_DIR/rdp.log" 2>&1 &
            rdp=$!
            (
                for _ in $(seq 1 80); do
                    [ ! -S "$XDG_RUNTIME_DIR/wayland-0" ] || break
                    sleep .2
                done
                sleep 12
                WAYLAND_DISPLAY=wayland-0 kgx -- /bin/sh >"$XDG_RUNTIME_DIR/console.log" 2>&1
            ) &
            if [ "${LEMON_PHYSICAL_ACTIONS:-0}" = 1 ]; then
                (
                    for _ in $(seq 1 120); do
                        [ ! -f "$XDG_RUNTIME_DIR/client-started" ] || break
                        sleep .2
                    done
                    sleep 13
                    gjs -m /run/lemon/physical-input.js
                ) >"$XDG_RUNTIME_DIR/input.log" 2>&1 &
            fi
            wait "$shell"
        '
    fi
    export GDK_BACKEND=wayland GSK_RENDERER=cairo
    export XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=GNOME
    exec dbus-run-session -- /bin/sh -eu -c '
        pipewire >"$XDG_RUNTIME_DIR/pipewire.log" 2>&1 &
        /bin/sh /usr/local/libexec/lemon/wait-pipewire.sh "$!"
        wireplumber >"$XDG_RUNTIME_DIR/wireplumber.log" 2>&1 &
        if [ "${LEMON_PHYSICAL_OFFLINE:-0}" = 1 ]; then
            export LIBGL_ALWAYS_SOFTWARE=1
            unset LEMON_REQUIRE_RENDER_NODE
        else
            test -r /dev/dri/renderD128 && test -w /dev/dri/renderD128
            export LEMON_REQUIRE_RENDER_NODE=/dev/dri/renderD128
        fi
        gnome-shell --wayland --devkit --no-x11 --wayland-display=lemon-gnome &
        shell=$!
        (
            for _ in $(seq 1 35); do
                [ ! -S "$XDG_RUNTIME_DIR/lemon-gnome" ] || break
                sleep .2
            done
            test -S "$XDG_RUNTIME_DIR/lemon-gnome"
            sleep 7
            echo "Launching GNOME Console in the nested session"
            WAYLAND_DISPLAY=lemon-gnome kgx -- /bin/sh
        ) &
        wait "$shell"
    '
fi

if [ "${1:-}" = inner ]; then
    base=$2
    limit=$3
    mode=$4
    test "$(readlink /proc/self/ns/mnt)" != "$5"
    w=$base/weston
    g=$base/gnome
    viewer=${LEMON_PHYSICAL_VIEWER:-devkit}
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
    actions=0
    if [ "$limit" = 60 ] && [ -f "$base/physical-input.js" ]; then
        cp "$base/physical-input.js" "$g/run/lemon/physical-input.js"
        chmod 644 "$g/run/lemon/physical-input.js"
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
    chroot "$g" /bin/busybox su -s /bin/sh lemon -c 'exec /bin/busybox env -i \
        PATH=/usr/local/bin:/usr/bin:/bin HOME=/run/lemon/home XDG_RUNTIME_DIR=/run/lemon \
        WAYLAND_DISPLAY=/run/parent/lemon-physical DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/lemon/system-bus \
        G_MESSAGES_DEBUG=mdk LEMON_PHYSICAL_ACTIONS='"$actions"' LEMON_PHYSICAL_VIEWER='"$viewer"' LEMON_PHYSICAL_OFFLINE='"$offline"' /bin/sh /run/lemon-session.sh session' >"$base/gnome.log" 2>&1 &
    gnome=$!
    if [ "$viewer" = rdp ]; then
        for _ in $(seq 1 90); do
            if grep -q ':0D3D .* 0A ' /proc/net/tcp /proc/net/tcp6; then break; fi
            kill -0 "$gnome"
            sleep .2
        done
        grep -q ':0D3D .* 0A ' /proc/net/tcp /proc/net/tcp6
        WAYLAND_DISPLAY=lemon-physical chroot "$w" /bin/busybox sh -c \
            'exec /usr/bin/wlfreerdp3 /v:127.0.0.1 /u:lemon-local /from-stdin:force /sec:nla \
             "/cert:fingerprint:sha256:$1" /size:1080x2340 /f -clipboard /log-level:WARN </tmp/client-credential' \
            local-rdp "$pin" >"$base/client.log" 2>&1 &
        touch "$g/run/lemon/client-started"
    fi
    for _ in $(seq 1 "$((limit / 2))"); do
        sleep 2
        kill -0 "$weston"
        kill -0 "$gnome"
        if grep -q 'Using Wayland display name' "$base/gnome.log" "$g/run/lemon/gnome.log" 2>/dev/null; then
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
case "$limit" in 30|60) ;; *) exit 2;; esac
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
    if [ "$mode" = hardware ]; then
        /bin/busybox timeout -k 1 4 "$base/probe" --restore-tty1 || exit 12
        test "$(cat /sys/class/tty/tty0/active)" = tty1 || exit 12
        printf '\r\nLEMON GNOME TEST ENDED - TTY1 RESTORED\r\n' >/dev/tty1
    fi
    exit "$rc"
}
trap cleanup EXIT
"$base/watchdog" "$limit" /bin/sh "$0" inner "$base" "$limit" "$mode" "$(readlink /proc/self/ns/mnt)" &
watchdog=$!
printf '%s\n' "$watchdog" >"$base/watchdog.pid"
stop() {
    kill -TERM "$watchdog" 2>/dev/null || :
    wait "$watchdog" || :
    exit 143
}
trap stop HUP INT TERM
wait "$watchdog"
