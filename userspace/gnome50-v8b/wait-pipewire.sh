#!/bin/sh
set -eu

pid=${1:?PipeWire PID required}
socket=${XDG_RUNTIME_DIR:?}/pipewire-0
for attempt in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "FAIL [PipeWire readiness]: process exited" >&2
        exit 1
    fi
    # SO_ACCEPTCON distinguishes a listening stream socket from a bound path.
    if [ -S "$socket" ] && /bin/busybox awk -v path="$socket" '$4 == "00010000" && $5 == "0001" && $8 == path { found=1 } END { exit !found }' /proc/net/unix; then
        printf 'LEMON_PIPEWIRE_READY attempt=%s\n' "$attempt"
        exit 0
    fi
    sleep .2
done
echo "FAIL [PipeWire readiness]: core socket is not listening" >&2
exit 1
