#!/bin/bash
set -euo pipefail
log=logs/v8b-desktop-offline
root=$(cat "$log/build-root.txt")
mkdir -p "$root/tmp/lemon-desktop-v8b"
tar -xzf artifacts/lemon-desktop-v8b-aarch64.tar.gz -C "$root/tmp/lemon-desktop-v8b"
runtime="$root/tmp/lemon-desktop-v8b/runtime"
for n in null:3 random:8 urandom:9; do
    [ -e "$root/dev/${n%:*}" ] || mknod "$root/dev/${n%:*}" c 1 "${n#*:}"
done
launcher=/tmp/lemon-desktop-v8b/runtime/desktop.sh
if timeout 10 chroot "$root" /bin/sh "$launcher" start gl; then
    echo "GL without real Adreno was incorrectly accepted" >&2; exit 1
fi
LEMON_OFFLINE_TEST=1 timeout -k 3 30 chroot "$root" /bin/sh "$launcher" start pixman >"$log/start.txt" 2>&1 &
pid=$!
stop() {
    if kill -0 "$pid" 2>/dev/null; then
        chroot "$root" /bin/sh "$launcher" stop || kill "$pid" || :
        wait "$pid" || :
    fi
    for f in weston.log weston.stderr client.log; do
        [ ! -f "$runtime/$f" ] || cp "$runtime/$f" "$log/"
    done
}
trap stop EXIT
for i in {1..15}; do
    [ ! -S "$runtime/session/input" ] || break
    kill -0 "$pid"; sleep .4
done
sleep 1
for proc in /proc/[0-9]*; do
    [ "$(readlink "$proc/root" 2>/dev/null || :)" = "$root" ] || continue
    cmd=$(tr '\000' ' ' < "$proc/cmdline" 2>/dev/null || :)
    case "$cmd" in */runtime/usr/bin/weston\ --backend*|*/runtime/usr/local/bin/lemon-desktop\ pixman*)
        ps -p "${proc##*/}" -o comm=,rss=,time= ;;
    esac
done > "$log/process-rss.txt"
start_ns=$(date +%s%N)
chroot "$root" /bin/sh "$launcher" capture >"$log/initial.png"
end_ns=$(date +%s%N)
printf 'WSL capture elapsed ms: %s\n' "$(((end_ns-start_ns)/1000000))"
wc -c "$log/initial.png"
chroot "$root" /bin/sh "$launcher" capture >"$log/idle.png"
cmp "$log/initial.png" "$log/idle.png"
printf 'click 55 560\n' | chroot "$root" /bin/sh "$launcher" input
printf 'key A\n' | chroot "$root" /bin/sh "$launcher" input
printf 'move 280 650\n' | chroot "$root" /bin/sh "$launcher" input
if printf 'click 999 0\n' | chroot "$root" /bin/sh "$launcher" input; then exit 1; fi
sleep 1
chroot "$root" /bin/sh "$launcher" capture >"$log/after-input.png"
chroot "$root" /bin/sh "$launcher" stop
wait "$pid"
test ! -e "$runtime/session"
file "$log/initial.png" "$log/after-input.png"
sha256sum "$log/initial.png" "$log/after-input.png"
cmp -s "$log/initial.png" "$log/after-input.png" && exit 1
echo 'PASS: capture, app input, invalid input rejected, stop and session cleanup'
