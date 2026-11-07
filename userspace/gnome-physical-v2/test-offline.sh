#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
project=$PWD
case "${1:-C}" in C) viewer=rdp;; B) viewer=devkit;; *) exit 2;; esac
base=$(mktemp -d /home/hadirpc/Redmi9T-Native-Linux/physical-v2-offline.XXXXXX)
log="$project/logs/gnome-physical-v2/offline-${2:-${1:-C}}"
mkdir -p "$log"
rm -f "$log/samples.txt"
printf '%s\n' "$base" >"$log/stage.txt"
xvfb=
cleanup_xvfb() {
    if [ -n "$xvfb" ]; then kill -TERM "$xvfb" 2>/dev/null || :; wait "$xvfb" 2>/dev/null || :; fi
}
trap cleanup_xvfb EXIT
if [ "${LEMON_OFFLINE_X11_AUTO:-0}" = 1 ]; then
    : >"$log/x-display"
    Xvfb -displayfd 3 -screen 0 720x1280x24 -nolisten tcp -ac -noreset 3>"$log/x-display" >"$log/xvfb.log" 2>&1 &
    xvfb=$!
    for _ in $(seq 1 50); do [ ! -s "$log/x-display" ] || break; sleep .1; done
    export LEMON_OFFLINE_X11=":$(cat "$log/x-display")"
fi
cp -al /home/hadirpc/Redmi9T-Native-Linux/physical-gnome.hz2hQr "$base/gnome"
cp -al /home/hadirpc/Redmi9T-Native-Linux/gnome-parent.40RdpU "$base/weston"
for root in "$base/gnome" "$base/weston"; do
    for dir in dev proc sys run tmp; do rm -rf -- "$root/$dir"; mkdir -m 755 "$root/$dir"; done
done
cp userspace/gnome-physical-v2/{session.sh,user-session.sh,devkit-session.sh,input.js,session-component.js} "$base/"
cp artifacts/gnome-physical-v2/{watchdog,vt-cleanup,drm-probe,frame-trace.so,dbus-trace.so} "$base/"
mv "$base/drm-probe" "$base/probe"
chmod 755 "$base/watchdog" "$base/vt-cleanup"
# Only the namespace supervisor is native on the PC; all userspace remains ARM64/QEMU.
gcc -O2 -Wall -Wextra -Werror userspace/gnome-physical-v2/watchdog.c -o "$base/watchdog.native"
mv "$base/watchdog.native" "$base/watchdog"
set +e
LEMON_PHYSICAL_VIEWER=$viewer LEMON_TEST_ACTIONS=1 LEMON_CAPTURE=1 /bin/sh "$base/session.sh" "$base" "${LEMON_OFFLINE_SECONDS:-90}" offline >"$log/session.txt" 2>&1 &
session=$!
elapsed=0
while kill -0 "$session" 2>/dev/null; do
    {
        printf 'UPTIME '; cat /proc/uptime
        for pid in /proc/[0-9]*; do
            case "$(readlink "$pid/root" 2>/dev/null)" in "$base"/*)
                echo "PROCESS ${pid##*/}"
                cat "$pid/comm" "$pid/stat" 2>/dev/null
                grep '^Pss:' "$pid/smaps_rollup" 2>/dev/null
                ;;
            esac
        done
    } >>"$log/samples.txt"
    sleep 2
    elapsed=$((elapsed+2))
    if [ "${LEMON_OFFLINE_STOP_AFTER:-0}" != 0 ] && [ "$elapsed" -eq "$LEMON_OFFLINE_STOP_AFTER" ]; then
        kill -TERM "$(cat "$base/watchdog.pid")"
    fi
done
wait "$session"
result=$?
set -e
echo "OFFLINE_EXIT=$result" | tee "$log/result.txt"
for path in gnome.log client.log system-bus.log seat.log; do
    output=$path
    [ "$path" != gnome.log ] || output=user-session.log
    [ ! -f "$base/$path" ] || cp "$base/$path" "$log/$output"
done
for path in gnome/run/lemon weston/tmp; do
    find "$base/$path" -maxdepth 1 -type f \( -name '*.log' -o -name '*.jsonl' -o -name '*.png' \) -exec cp {} "$log/" \;
done
if grep -F " $base/" /proc/self/mountinfo; then exit 3; fi
for pid in /proc/[0-9]*; do
    case "$(readlink "$pid/root" 2>/dev/null || :)" in "$base"/*) echo "LEFTOVER $pid"; exit 3;; esac
done
echo OFFLINE_NAMESPACE_CLEANUP_PASS | tee -a "$log/result.txt"
