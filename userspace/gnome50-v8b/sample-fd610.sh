#!/bin/sh
set -eu
base=/tmp/lemon-gnome50-fd610
gpu=/sys/bus/platform/devices/5900000.gpu
awk '/^(MemAvailable|SwapTotal):/ {print}' /proc/meminfo
cat /proc/uptime
grep '^cpu ' /proc/stat
for proc in /proc/[0-9]*; do
    [ "$(readlink "$proc/root" 2>/dev/null || :)" = "$base/root" ] || continue
    printf 'PROCESS %s\n' "${proc##*/}"
    cat "$proc/stat" 2>/dev/null || :
    grep '^Pss:' "$proc/smaps_rollup" 2>/dev/null || :
    for fd in "$proc"/fd/*; do
        node=$(readlink "$fd" 2>/dev/null || :)
        case "$node" in
            */dri/*)
                printf 'DRM_FD %s %s\n' "${proc##*/}" "$node"
                grep '^drm-' "$proc/fdinfo/${fd##*/}" 2>/dev/null || :
                ;;
        esac
    done
done
for f in "$gpu"/power/runtime_status "$gpu"/devfreq/*/cur_freq "$gpu"/gpu_busy_percent; do
    [ ! -r "$f" ] || printf 'GPU %s %s\n' "${f##*/}" "$(cat "$f")"
done
for zone in /sys/class/thermal/thermal_zone*; do
    [ -r "$zone/type" ] && [ -r "$zone/temp" ] || continue
    printf 'THERMAL %s %s\n' "$(cat "$zone/type")" "$(cat "$zone/temp")"
done
