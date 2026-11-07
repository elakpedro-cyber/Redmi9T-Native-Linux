#!/bin/sh
set -eu

# Linux may instantiate its inactive SIT fallback in every network namespace.
interfaces=$(awk -F: 'NR > 2 { gsub(/[[:space:]]/, "", $1); print $1 }' /proc/net/dev)
case "$interfaces" in
    lo) ;;
    'lo
sit0')
        sit=$(/bin/busybox ip link show dev sit0)
        printf '%s\n' "$sit" | awk '
            NR == 1 && /state DOWN/ && $0 !~ /[<,]UP[,>]/ { down=1 }
            /link\/sit[[:space:]]/ { tunnel=1 }
            END { exit !(down && tunnel) }
        '
        ;;
    *) echo 'Unexpected interfaces in RDP namespace' >&2; exit 1;;
esac
