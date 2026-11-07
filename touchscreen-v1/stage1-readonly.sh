#!/bin/sh
# Future authorized metadata collection only. No GPIO requests, event opens,
# voltage reads, module loads, mounts, unbinds or SPI commands. Stdout only.
set -eu
prefix=${LEMON_DIAG_ROOT:-}
show() {
    path=$1
    printf '\n=== %s ===\n' "$path"
    if [ -r "$prefix$path" ]; then cat "$prefix$path"; else echo UNAVAILABLE; fi
}
for path in /proc/sys/kernel/osrelease /proc/sys/kernel/random/boot_id /proc/fb \
    /sys/class/tty/tty0/active /proc/modules /proc/bus/input/devices \
    /proc/interrupts /proc/mounts /proc/swaps; do show "$path"; done
for disk in sda sdb sdc sdd sde sdf; do show "/sys/block/$disk/stat"; done
for node in "$prefix"/sys/class/regulator/regulator.*; do
    [ -d "$node" ] || continue
    for prop in name num_users min_microvolts max_microvolts; do show "${node#"$prefix"}/$prop"; done
done
for node in 4ac0000.geniqup 4a88000.spi 5900000.gpu 5e00000.display-subsystem 5e94000.dsi 5e94400.phy; do
    path=/sys/bus/platform/devices/$node
    printf '\nBINDING %s ' "$node"
    readlink "$prefix$path/driver" || :
    show "$path/power/runtime_status"
    show "$path/driver_override"
done
# pinmux-pins lists ownership; it is not a pin-voltage measurement.
for path in "$prefix"/sys/kernel/debug/pinctrl/*/pinmux-pins; do
    [ ! -r "$path" ] || show "${path#"$prefix"}"
done
printf '\nELECTRICAL_VDDIO_LCD_BIAS_IRQ_CS_RESET_LEVELS=UNKNOWN\n'
printf 'No voltage inference from regulator constraints or num_users.\n'
