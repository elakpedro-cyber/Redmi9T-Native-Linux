#!/bin/bash
set -euo pipefail
log=$PWD/logs/v8b-labwc-offline
root=$(cat "$log/root.txt")
runtime="$root/tmp/lemon-labwc-v8b"
mkdir -p "$runtime" "$root/dev/pts" "$root/dev/shm"
tar -xzf "${1:-artifacts/lemon-labwc-v8b-aarch64.tar.gz}" -C "$runtime"
if [ "${LEMON_OFFLINE_FAIL_WAYBAR:-0}" = 1 ]; then
    printf '#!/bin/sh\nexit 42\n' > "$runtime/runtime/usr/bin/waybar"
fi
for n in null:3 random:8 urandom:9; do
    [ -e "$root/dev/${n%:*}" ] || mknod "$root/dev/${n%:*}" c 1 "${n#*:}"
done
[ -e "$root/dev/ptmx" ] || [ -L "$root/dev/ptmx" ] || ln -s pts/ptmx "$root/dev/ptmx"
mount -t devpts -o newinstance,ptmxmode=0666 devpts "$root/dev/pts"
rm -f "$runtime/input-proof"
launcher=/tmp/lemon-labwc-v8b/runtime/session.sh
LEMON_OFFLINE_TEST=1 timeout -k 3 60 chroot "$root" /bin/sh "$launcher" start offline-pixman >"$log/start.txt" 2>&1 &
pid=$!
cleanup() {
    kill "$pid" 2>/dev/null || :
    wait "$pid" || :
    for f in dbus.log labwc.log waybar.log wayvnc.log foot.log output.log; do
        [ ! -f "$runtime/runtime/$f" ] || cp "$runtime/runtime/$f" "$log/"
    done
}
trap cleanup EXIT
for i in {1..22}; do
    [ ! -S "$runtime/runtime/session/vnc.sock" ] || break
    kill -0 "$pid" || { cat "$log/start.txt"; exit 1; }
    sleep .5
done
sleep 1
python3 userspace/labwc-v8b/test-rfb.py
for proc in /proc/[0-9]*; do
    [ "$(readlink "$proc/root" 2>/dev/null || :)" = "$root" ] || continue
    ps -p "${proc##*/}" -o comm=,rss=,time=
done >"$log/rss.txt"
kill "$pid"
wait "$pid" || :
test ! -e "$runtime/runtime/session"

