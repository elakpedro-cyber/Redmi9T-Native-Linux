#!/bin/sh
set -eu
umask 077

base=/tmp/lemon-gnome50-fd610
root=$base/root
test "$$" = 1
test "$(uname -r)" = 7.4.0-rc1-lemon-bringup-v8b
test "$(stat -f -c %T "$base")" = tmpfs
test -c /dev/dri/renderD128
test "$(cat /sys/class/drm/renderD128/dev)" = 226:128
test "$(basename "$(readlink /sys/class/drm/renderD128/device/driver)")" = adreno
test "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = 1
test "$(cat /sys/bus/platform/devices/5e00000.display-subsystem/driver_override)" = lemon-stage-b-hold
test ! -L /sys/bus/platform/devices/5e00000.display-subsystem/driver

mkdir -p "$root"/dev/dri "$root"/dev/shm "$root"/proc "$root"/sys "$root"/tmp "$root"/run/gnome-fd610 "$root"/var/lib/dbus
mkdir -p "$root/run/gnome-fd610/applets"
for entry in null zero random urandom; do
    test -c "/dev/$entry"
    touch "$root/dev/$entry"
    mount -o bind "/dev/$entry" "$root/dev/$entry"
done
touch "$root/dev/dri/renderD128"
mount -o bind /dev/dri/renderD128 "$root/dev/dri/renderD128"
mount -t proc -o nosuid,nodev,noexec proc "$root/proc"
mount -o bind /sys "$root/sys"
mount -o remount,bind,ro "$root/sys"
mount -t tmpfs -o mode=1777,nosuid,nodev,size=128m tmpfs "$root/dev/shm"
chmod 1777 "$root/tmp"
chroot "$root" /bin/busybox --install -s /run/gnome-fd610/applets
chroot "$root" /usr/bin/dbus-uuidgen --ensure=/var/lib/dbus/machine-id
if [ "${1:-}" = --mount-check ]; then
    awk -v root="$root" '
      $5=="/" && $7 !~ /^(shared|master):/ { private=1 }
      $5==root"/sys" && $6 ~ /^ro(,|$)/ { sys=1 }
      $5==root"/proc" { proc=1 }
      $5==root"/dev/shm" { shm=1 }
      $5==root"/dev/dri/renderD128" { render=1 }
      END {exit !(private && sys && proc && shm && render)}
    ' "$root/proc/self/mountinfo"
    test -r "$root/dev/dri/renderD128"
    test -w "$root/dev/dri/renderD128"
    echo PRIVATE_MOUNTS_OK
    /bin/busybox setsid /bin/sh -c 'touch "$1/descendant-started"; sleep 7; touch "$1/descendant-escaped"' sh "$base" &
    wait
    exit 1
fi

cat >"$root/run/gnome-fd610/system.conf" <<'EOF'
<busconfig>
  <type>system</type>
  <listen>unix:path=/run/gnome-fd610/system-bus</listen>
  <policy user="root">
    <allow send_destination="*"/>
    <allow receive_sender="*"/>
  </policy>
</busconfig>
EOF
chroot "$root" /usr/bin/dbus-daemon --nofork --config-file=/run/gnome-fd610/system.conf &
system_bus=$!
for delay in 1 2 3 4 5; do
    [ ! -S "$root/run/gnome-fd610/system-bus" ] || break
    kill -0 "$system_bus"
    sleep .2
done
test -S "$root/run/gnome-fd610/system-bus"
exec chroot "$root" /bin/busybox env -i PATH=/usr/bin:/bin:/run/gnome-fd610/applets HOME=/tmp XDG_RUNTIME_DIR=/run/gnome-fd610 XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=GNOME DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/gnome-fd610/system-bus GSETTINGS_BACKEND=memory LEMON_REQUIRE_RENDER_NODE=/dev/dri/renderD128 /usr/bin/dbus-run-session -- /usr/bin/gnome-shell --wayland --headless --no-x11 --virtual-monitor=480x720
