#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
log="$PWD/logs/gnome-physical-v2/offline-$1"
base=$(tr -d '\r\n' <"$log/stage.txt")
for path in gnome.log client.log system-bus.log seat.log; do
    [ ! -f "$base/$path" ] || cp "$base/$path" "$log/${path}"
done
for path in gnome/run/lemon weston/tmp; do
    find "$base/$path" -maxdepth 1 -type f \( -name '*.log' -o -name '*.jsonl' -o -name '*.png' \) -exec cp {} "$log/" \;
done
if grep -F " $base/" /proc/self/mountinfo; then exit 3; fi
for pid in /proc/[0-9]*; do
    case "$(readlink "$pid/root" 2>/dev/null || :)" in "$base"/*) echo "LEFTOVER $pid"; exit 3;; esac
done
echo OFFLINE_NAMESPACE_CLEANUP_PASS
