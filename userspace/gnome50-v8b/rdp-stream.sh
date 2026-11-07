#!/bin/sh
set -eu

# Run from SSH in the normal namespace. The supervisor supplies the PID
# only after proving the desktop namespace contains just loopback.
base=/tmp/lemon-gnome50
test "$(stat -c '%u:%a' "$base")" = 0:700
test ! -L "$base/rdp.pid"
test "$(stat -c '%u:%a' "$base/rdp.pid")" = 0:600
pid=$(cat "$base/rdp.pid")
case "$pid" in ''|*[!0-9]*) exit 1;; esac
test "$pid" -gt 1
target=$(readlink "/proc/$pid/ns/net")
test -n "$target"
test "$target" != "$(readlink /proc/self/ns/net)"
exec /bin/busybox nsenter -t "$pid" -n /bin/sh -c '
    /bin/sh /tmp/lemon-gnome50/check-private-net.sh || exit 1
    root=/tmp/lemon-gnome50/root
    exec "$root/lib/ld-musl-aarch64.so.1" --library-path "$root/usr/lib" "$root/usr/bin/socat" STDIO TCP4:127.0.0.1:3389
'
