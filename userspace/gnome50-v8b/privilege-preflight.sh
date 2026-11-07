#!/bin/sh
set -eu
umask 077

check() {
    label=$1
    shift
    if "$@"; then
        printf 'LEMON_PRIVILEGE_OK %s\n' "$label"
    else
        status=$?
        printf 'LEMON_PRIVILEGE_FAILED %s exit=%s\n' "$label" "$status" >&2
        exit "$status"
    fi
}

uid=$(id -u)
gid=$(id -g)
runtime=${XDG_RUNTIME_DIR:-}
check identity test "$uid:$gid" = "$(id -u lemon):$(id -g lemon)"
check non-root test "$uid" -ne 0
check environment test -n "$runtime" -a -n "${HOME:-}" -a "${XDG_SESSION_TYPE:-}" = wayland
check runtime-traverse test -d "$runtime" -a -x "$runtime"
check home-access test -d "$HOME" -a -x "$HOME" -a -w "$HOME"
check runtime-owner-mode test "$(stat -c '%u:%g:%a' "$runtime")" = "$uid:$gid:700"
check runtime-tmpfs test "$(stat -f -c %T "$runtime")" = tmpfs
check system-bus-address test "${DBUS_SYSTEM_BUS_ADDRESS:-}" = "unix:path=$runtime/system-bus"
check system-bus-socket test -S "$runtime/system-bus"
check session-bus-address test -n "${DBUS_SESSION_BUS_ADDRESS:-}"
for app in gdbus socat gnome-shell gnome-session grdctl pipewire wireplumber; do
    check "executable-$app" command -v "$app" >/dev/null
done
for binary in /usr/bin/gnome-shell /usr/libexec/gnome-session-binary /usr/libexec/gnome-remote-desktop-daemon /usr/bin/grdctl /usr/bin/pipewire /usr/bin/wireplumber /usr/bin/socat; do
    check "libraries-${binary##*/}" /lib/ld-musl-aarch64.so.1 --list "$binary" >/dev/null
done
if [ -x /usr/bin/nautilus ]; then
    for binary in /usr/bin/kgx /usr/bin/gnome-control-center /usr/bin/nautilus /usr/bin/gnome-text-editor; do
        check "executable-${binary##*/}" test -x "$binary"
        check "libraries-${binary##*/}" /lib/ld-musl-aarch64.so.1 --list "$binary" >/dev/null
    done
fi
check system-bus-connect gdbus call --system --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetId >/dev/null
check session-bus-connect gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetId >/dev/null
check render-device test -c /dev/dri/renderD128
check render-owner-mode test "$(stat -c '%u:%g:%a' /dev/dri/renderD128)" = "$uid:$gid:600"
open_render() { ( : <>/dev/dri/renderD128 ); }
check render-open open_render
for name in rdp-test.crt rdp-test.key rdp-credentials; do
    file=$runtime/$name
    check "tls-owner-mode-$name" test "$(stat -c '%u:%g:%a' "$file")" = "$uid:$gid:600"
    check "tls-readable-$name" test -s "$file" -a -r "$file"
done
file=$(mktemp "$runtime/.lemon-probe.XXXXXX") || {
    echo 'LEMON_PRIVILEGE_FAILED runtime-create' >&2
    exit 1
}
check runtime-remove rm "$file"
probe=$(mktemp -d "$runtime/.lemon-socket.XXXXXX")
listener=
trap 'if [ -n "$listener" ]; then kill "$listener" 2>/dev/null || :; wait "$listener" 2>/dev/null || :; fi; rm -rf "$probe"' EXIT
socat "UNIX-LISTEN:$probe/wayland-probe" EXEC:/bin/true &
listener=$!
for delay in 1 2 3 4 5; do
    [ ! -S "$probe/wayland-probe" ] || break
    sleep .1
done
check wayland-socket-bind test -S "$probe/wayland-probe"
echo LEMON_PRIVILEGE_PREFLIGHT_OK
