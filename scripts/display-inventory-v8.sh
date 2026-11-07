#!/bin/sh
# Read-only inventory for stage A or B. No bind, module load or DSI transfers.
uname -r
cat /run/init-reached /run/openrc-reached
cat /proc/mounts /proc/swaps /proc/fb
for dev in /sys/bus/platform/devices/5e00000.* /sys/bus/platform/devices/5e01000.* \
           /sys/bus/platform/devices/5e94000.* /sys/bus/platform/devices/5e94400.* \
           /sys/bus/platform/devices/5f00000.* /sys/bus/platform/devices/5900000.*; do
    [ -e "$dev" ] || continue
    printf '\n%s\n' "$dev"
    readlink "$dev/driver" || :
    [ ! -r "$dev/power/runtime_status" ] || cat "$dev/power/runtime_status"
done
for dir in /sys/class/drm /sys/bus/mipi-dsi/devices /sys/class/backlight; do
    [ ! -d "$dir" ] || ls -l "$dir"
done
cat /proc/bus/input/devices
for disk in /sys/block/sd?; do
    [ -d "$disk" ] || continue
    printf '\n%s\n' "$disk"
    cat "$disk/stat" "$disk/device/ioerr_cnt"
done
dmesg
