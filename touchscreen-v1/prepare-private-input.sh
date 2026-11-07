#!/bin/sh
# Call only inside an approved private session namespace after Stage1 event validation.
set -eu
root=$1
event=${2:-}
case "$event" in event*) number=${event#event};; *) exit 2;; esac
case "$number" in ''|*[!0-9]*) exit 2;; esac
parent_ns=${3:-}
case "$parent_ns" in mnt:\[*\]) ;; *) exit 3;; esac
[ "$(readlink /proc/self/ns/mnt)" != "$parent_ns" ] || { echo 'Private mount namespace required' >&2; exit 3; }
case "$root" in /tmp/lemon-gnome-v21.??????/weston) ;; *) exit 3;; esac
[ "$(readlink -f "$root")" = "$root" ]
for part in dev run; do
 [ ! -L "$root/$part" ]
 if grep -F " $root/$part " /proc/self/mountinfo; then exit 3; fi
done
for part in dev/input run/udev run/udev/data; do [ ! -L "$root/$part" ]; done
[ -d "$root/dev" ] && [ -d "$root/run" ]
sys=/sys/class/input/$event
[ "$(cat "$sys/device/name")" = 'Lemon NT36672A handoff touchscreen' ]
props=$(cat "$sys/device/properties")
abs=$(cat "$sys/device/capabilities/abs")
case "$props$abs" in *[!0-9a-fA-F]*) exit 3;; esac
[ "$((0x$props & 2))" != 0 ]
mask=$(( (1<<47) | (1<<53) | (1<<54) | (1<<57) ))
[ "$((0x$abs & mask))" = "$mask" ]
IFS=: read -r major minor <"$sys/dev"
[ "$major" = 13 ]
case "$minor" in ''|*[!0-9]*) exit 3;; esac
[ "${LEMON_TOUCH_STAGE1_VALIDATED:-0}" = 1 ] || { echo 'Stage1 hardware events must be validated first' >&2; exit 3; }
matrix=${LEMON_TOUCH_MATRIX:-}
case "$matrix" in ''|*[!0-9.\ -]*) exit 3;; esac
set -- $matrix
[ "$#" = 6 ] || exit 3
for value; do printf '%s\n' "$value" | grep -Eq '^-?[0-9]+([.][0-9]+)?$' || exit 3; done
umask 077
mkdir -p "$root/dev/input" "$root/run/udev/data"
[ ! -e "$root/dev/input/$event" ]
mknod -m 600 "$root/dev/input/$event" c "$major" "$minor"
printf 'E:ID_INPUT=1\nE:ID_INPUT_TOUCHSCREEN=1\nE:ID_SEAT=seat0\nE:LIBINPUT_CALIBRATION_MATRIX=%s\n' "$matrix" >"$root/run/udev/data/c$major:$minor"
echo "PRIVATE_INPUT_READY $event; no host permissions or udev database changed"
