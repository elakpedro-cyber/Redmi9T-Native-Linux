#!/bin/bash
set -euo pipefail

log=$PWD/logs/v8b-gnome50-offline
log=${LEMON_GNOME_LOG_DIR:-$log}
root=${LEMON_GNOME_TEST_ROOT:-$(cat "$log/root.txt")}
case "$root" in /home/hadirpc/Redmi9T-Native-Linux/gnome50-stage.*) ;; *) exit 1;; esac
mkdir -p "$root"/{dev/shm,proc,sys,tmp,run/gnome-test}
chmod 1777 "$root/tmp"
chmod 700 "$root/run/gnome-test"
mkdir -p "$root/run/gnome-test/applets"
chroot "$root" /bin/busybox --install -s /run/gnome-test/applets
export PATH="$PATH:/run/gnome-test/applets"
for entry in null:3 zero:5 random:8 urandom:9; do
    [ -e "$root/dev/${entry%:*}" ] || mknod "$root/dev/${entry%:*}" c 1 "${entry#*:}"
    chmod 666 "$root/dev/${entry%:*}"
done
cp userspace/gnome50-v8b/start-shell.sh "$root/tmp/gnome50-shell.sh"
cp userspace/gnome50-v8b/wait-pipewire.sh "$root/tmp/gnome50-wait-pipewire.sh"
mount -t proc proc "$root/proc"
mount -t sysfs -o ro sysfs "$root/sys"
mount -t tmpfs -o mode=1777 tmpfs "$root/dev/shm"
mkdir -p "$root/dev/pts"
test -e "$root/dev/ptmx" || ln -snf pts/ptmx "$root/dev/ptmx"
mount -t devpts -o newinstance,ptmxmode=0666,mode=0620 devpts "$root/dev/pts"
system_bus=
sampler=
rdp_client=
rdp_debugger=
cleanup() {
    if [ -n "$rdp_debugger" ]; then
        kill "$rdp_debugger" 2>/dev/null || :
        wait "$rdp_debugger" || :
    fi
    if [ -n "$rdp_client" ]; then
        kill "$rdp_client" 2>/dev/null || :
        wait "$rdp_client" || :
    fi
    if [ -n "$sampler" ]; then
        kill "$sampler" 2>/dev/null || :
        wait "$sampler" || :
    fi
    if [ -n "$system_bus" ]; then
        kill "$system_bus" 2>/dev/null || :
        wait "$system_bus" || :
    fi
    umount -l "$root/dev/pts" "$root/dev/shm" "$root/sys" "$root/proc"
    if [ "${2:-}" = --probe-rdp ]; then
        cp "$root/run/gnome-test/pipewire.log" "$log/pipewire.txt" 2>/dev/null || :
        cp "$root/run/gnome-test/wireplumber.log" "$log/wireplumber.txt" 2>/dev/null || :
        cp "$root/run/gnome-test/console.log" "$log/console.txt" 2>/dev/null || :
        for app_log in "$root/run/gnome-test"/app-*.log; do cp "$app_log" "$log/" 2>/dev/null || :; done
        cp "$root/run/gnome-test/settings.log" "$log/settings.txt" 2>/dev/null || :
        cp "$root/run/gnome-test/input-probe.log" "$log/input-probe.txt" 2>/dev/null || :
        rm -rf "$root/run/gnome-test"
    fi
}
trap 'cleanup "$@"' EXIT
ulimit -c 0
mkdir -p "$root/var/lib/dbus"
chroot "$root" /usr/bin/dbus-uuidgen --ensure=/var/lib/dbus/machine-id
cat >"$root/run/gnome-test/offline-system.conf" <<'EOF'
<busconfig>
  <type>system</type>
  <listen>unix:path=/run/gnome-test/system-bus</listen>
  <policy context="default">
    <allow user="lemon"/>
  </policy>
  <policy user="root">
    <allow send_destination="*"/>
    <allow receive_sender="*"/>
  </policy>
  <policy user="lemon">
    <allow send_destination="*"/>
    <allow receive_sender="*"/>
  </policy>
</busconfig>
EOF
rm -f "$root/run/gnome-test/system-bus"
chroot "$root" /usr/bin/dbus-daemon --nofork --config-file=/run/gnome-test/offline-system.conf &
system_bus=$!
for delay in 1 2 3 4 5; do
    [ ! -S "$root/run/gnome-test/system-bus" ] || break
    kill -0 "$system_bus"
    sleep .2
done
test -S "$root/run/gnome-test/system-bus"
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/gnome-test/system-bus
settings=memory
session_root=(chroot "$root")
home=/tmp
if [ "${2:-}" = --probe-rdp ]; then
    ip link set lo up
    cp userspace/gnome50-v8b/offline-rdp-probe.sh "$root/tmp/gnome50-rdp-probe.sh"
    cp userspace/gnome50-v8b/start-rdp.sh "$root/tmp/gnome50-start-rdp.sh"
    cp userspace/gnome50-v8b/check-private-net.sh "$root/tmp/gnome50-check-private-net.sh"
    cp userspace/gnome50-v8b/desktop-apps.sh "$root/tmp/gnome50-desktop-apps.sh"
    cp userspace/gnome50-v8b/offline-input-probe.js "$root/tmp/gnome50-input-probe.js"
    if [ "${LEMON_RDP_GDB:-0}" = 1 ]; then
        cp /usr/bin/qemu-aarch64-static "$root/tmp/qemu-aarch64-static"
        (
            for attempt in {1..40}; do
                if ss -lnt 'sport = :19130' | grep -q LISTEN; then break; fi
                sleep 1
            done
            timeout 45 gdb-multiarch -q -nx -batch -ex "set sysroot $root" -ex "file $root/usr/libexec/gnome-remote-desktop-daemon" -ex 'target remote 127.0.0.1:19130' -ex continue -ex bt -ex 'x/6i $pc' -ex 'info sharedlibrary'
        ) >"$log/grd-daemon-gdb.txt" 2>&1 &
        rdp_debugger=$!
    fi
    umask 077
    openssl req -x509 -newkey rsa:2048 -nodes -subj /CN=localhost -addext subjectAltName=DNS:localhost,IP:127.0.0.1 -days 1 -keyout "$root/run/gnome-test/rdp-test.key" -out "$root/run/gnome-test/rdp-test.crt" >/dev/null 2>&1
    mkdir -p "$root/run/gnome-test/"{config,data,cache,home}
    export XDG_CONFIG_HOME=/run/gnome-test/config XDG_DATA_HOME=/run/gnome-test/data
    export XDG_CACHE_HOME=/run/gnome-test/cache
    secret=$(openssl rand -hex 24)
    printf '%s\n' offline-probe "$secret" >"$root/run/gnome-test/rdp-credentials"
    printf '%s\n' "$secret" >"$root/run/gnome-test/client-credential"
    unset secret
    uid=$(chroot "$root" id -u lemon)
    gid=$(chroot "$root" id -g lemon)
    chown "$uid:$gid" "$root/run/gnome-test" "$root/run/gnome-test/"{config,data,cache,home,rdp-test.key,rdp-test.crt,rdp-credentials}
    session_root=(chroot --userspec="$uid:$gid" "$root")
    home=/run/gnome-test/home
    settings=dconf
    if [ "${LEMON_RDP_CLIENT:-0}" = 1 ]; then
        bash userspace/gnome50-v8b/offline-rdp-client.sh "$root/run/gnome-test" "$log" >"$log/rdp-client-controller.txt" 2>&1 &
        rdp_client=$!
    fi
fi
chroot "$root" /usr/bin/glib-compile-schemas /usr/share/glib-2.0/schemas
chroot "$root" /usr/bin/gnome-shell --version
if [ "${1:-}" = --session48 ]; then
    printf '%s\n' '[GNOME Session]' 'Name=Lemon Headless' 'RequiredComponents=lemon-headless-shell;' > "$root/usr/share/gnome-session/sessions/lemon-headless.session"
    mode=${LEMON_GNOME_MODE:-480x720}
    case "$mode" in 480x720|720x1280) ;; *) exit 1;; esac
    monitor=" --virtual-monitor=$mode"
    if [ "${2:-}" = --probe-rdp ]; then monitor=; fi
    sed "s|^Exec=.*|Exec=/usr/bin/gnome-shell --wayland --headless --no-x11$monitor|" "$root/usr/share/applications/org.gnome.Shell.desktop" > "$root/usr/share/applications/lemon-headless-shell.desktop"
    chmod 644 "$root/usr/share/gnome-session/sessions/lemon-headless.session" "$root/usr/share/applications/lemon-headless-shell.desktop"
fi
(
    while :; do
        total=0
        count=0
        for proc in /proc/[0-9]*; do
            [ "$(readlink "$proc/root" 2>/dev/null)" = "$root" ] || continue
            pss=$(awk '/^Pss:/ {print $2}' "$proc/smaps_rollup" 2>/dev/null) || continue
            total=$((total + pss))
            count=$((count + 1))
        done
        printf '%s %s %s\n' "$(date +%s)" "$count" "$total"
        sleep 1
    done
) > "$log/session48-pss.txt" &
sampler=$!
timeout -k 5 75 env LEMON_GNOME_OFFLINE=1 XDG_RUNTIME_DIR=/run/gnome-test HOME="$home" GSETTINGS_BACKEND="$settings" "${session_root[@]}" /bin/sh /tmp/gnome50-shell.sh "$@"
