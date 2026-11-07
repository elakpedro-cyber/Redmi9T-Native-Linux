#!/bin/sh
set -eu
umask 077
ulimit -c 0
phase=namespace-and-hardware-guards
clock() { IFS=' ' read -r uptime rest </proc/uptime; printf '%s' "$uptime"; }
started=$(clock)
step() {
    line=$1 label=$2
    shift 2
    from=$(clock)
    if "$@"; then status=0; else status=$?; fi
    to=$(clock)
    printf 'RDP_STEP phase=%s line=%s command=%s status=%s uptime_from=%s uptime_to=%s\n' "$phase" "$line" "$label" "$status" "$from" "$to" >&2
    return "$status"
}
trap 'status=$?; if [ "$status" -ne 0 ]; then echo "RDP_BOOTSTRAP_FAILED phase=$phase status=$status uptime_from=$started uptime_to=$(clock)" >&2; fi' EXIT

base=/tmp/lemon-gnome50
root=$base/root
runtime=/run/lemon-rdp
step "$LINENO" namespace-pid1 test "$$" = 1
step "$LINENO" kernel-release test "$(uname -r)" = 7.4.0-rc1-lemon-bringup-v8b
step "$LINENO" ram-filesystem test "$(stat -f -c %T "$base")" = tmpfs
step "$LINENO" staging-owner-mode test "$(stat -c '%u:%a' "$base")" = 0:700
step "$LINENO" private-network /bin/sh "$base/check-private-net.sh"
step "$LINENO" render-character-device test -c /dev/dri/renderD128
step "$LINENO" render-device-number test "$(cat /sys/class/drm/renderD128/dev)" = 226:128
step "$LINENO" adreno-driver test "$(basename "$(readlink /sys/class/drm/renderD128/device/driver)")" = adreno
step "$LINENO" gpu-kms-separation test "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = 1
p=/sys/bus/platform/devices
step "$LINENO" mdss-override test "$(cat "$p/5e00000.display-subsystem/driver_override")" = lemon-stage-b-hold
step "$LINENO" mdss-unbound test ! -L "$p/5e00000.display-subsystem/driver"
step "$LINENO" dispcc-unbound test ! -L "$p/5f00000.clock-controller/driver"
step "$LINENO" dsi-absent test ! -e "$p/5e94000.dsi"
step "$LINENO" dsi-phy-absent test ! -e "$p/5e94400.phy"
step "$LINENO" backlight-absent test ! -d /sys/class/backlight
if [ "${1:-}" = --check-only ]; then
    echo 'RDP_PRECHECK_OK'
    exit 0
fi

phase=private-loopback
step "$LINENO" loopback-up ip link set lo up
phase=private-mounts
for directory in "$root/run" "$root/dev" "$root/dev/dri"; do
    step "$LINENO" ordinary-directory test ! -L "$directory"
    step "$LINENO" not-host-mount awk -v path="$directory" '$5==path { mounted=1 } END { exit mounted }' /proc/self/mountinfo
done
step "$LINENO" chmod chmod 755 "$root"
step "$LINENO" mkdir mkdir -p "$root"/dev/dri "$root"/dev/shm "$root"/dev/pts "$root"/proc "$root"/sys "$root"/tmp "$root$runtime" "$root"/var/lib/dbus
step "$LINENO" chmod chmod 1777 "$root/tmp"
step "$LINENO" private-run-traverse chmod 0711 "$root/run"
step "$LINENO" private-dev-traverse chmod 0755 "$root/dev" "$root/dev/dri"
step "$LINENO" mount-proc mount -t proc -o nosuid,nodev,noexec proc "$root/proc"
step "$LINENO" mount-bind mount -o bind /sys "$root/sys"
step "$LINENO" mount-sysfs-readonly mount -o remount,bind,ro "$root/sys"
step "$LINENO" mount-shared-memory mount -t tmpfs -o mode=1777,nosuid,nodev,size=128m tmpfs "$root/dev/shm"
step "$LINENO" mount-devpts mount -t devpts -o newinstance,ptmxmode=0666,mode=0620 devpts "$root/dev/pts"
step "$LINENO" ln ln -s pts/ptmx "$root/dev/ptmx"
for entry in null zero random urandom; do
    step "$LINENO" touch touch "$root/dev/$entry"
    step "$LINENO" mount-bind mount -o bind "/dev/$entry" "$root/dev/$entry"
done

phase=desktop-account-and-render-node
uid=$(step "$LINENO" desktop-uid chroot "$root" /bin/busybox id -u lemon)
gid=$(step "$LINENO" desktop-gid chroot "$root" /bin/busybox id -g lemon)
step "$LINENO" mknod mknod -m 600 "$root/dev/dri/renderD128" c 226 128
step "$LINENO" chown chown "$uid:$gid" "$root/dev/dri/renderD128" "$root$runtime"
step "$LINENO" chmod chmod 700 "$root$runtime"
step "$LINENO" mkdir mkdir "$root$runtime/home"
step "$LINENO" chown chown "$uid:$gid" "$root$runtime/home"
phase=private-tls-files
for file in rdp-test.key rdp-test.crt rdp-credentials; do
    step "$LINENO" check test -f "$base/$file"
    step "$LINENO" check test "$(stat -c '%u:%a' "$base/$file")" = 0:600
    step "$LINENO" mv mv "$base/$file" "$root$runtime/$file"
    step "$LINENO" chown chown "$uid:$gid" "$root$runtime/$file"
done
phase=private-system-bus
step "$LINENO" dbus-parent-traverse chmod 0755 "$root/var/lib/dbus"
step "$LINENO" dbus-machine-id chroot "$root" /usr/bin/dbus-uuidgen --ensure=/var/lib/dbus/machine-id
cat >"$root$runtime/system.conf" <<'EOF'
<busconfig>
  <type>system</type>
  <listen>unix:path=/run/lemon-rdp/system-bus</listen>
  <policy context="default"><allow user="lemon"/></policy>
  <policy user="lemon">
    <allow send_destination="*"/>
    <allow receive_sender="*"/>
  </policy>
</busconfig>
EOF
chroot "$root" /usr/bin/dbus-daemon --nofork --config-file="$runtime/system.conf" &
bus=$!
for delay in 1 2 3 4 5; do
    [ ! -S "$root$runtime/system-bus" ] || break
    step "$LINENO" kill kill -0 "$bus"
    sleep .2
done
step "$LINENO" check test -S "$root$runtime/system-bus"

phase=desktop-session
desktop_probe=0
if [ "${1:-}" = --desktop-probe ]; then desktop_probe=1; fi
if [ -f "$root/usr/bin/nautilus" ]; then
    step "$LINENO" ice-directory mkdir -m 1777 "$root/tmp/.ICE-unix"
fi
echo "RDP_BOOTSTRAP_READY phase=$phase"
exec chroot "$root" /bin/busybox su -s /bin/sh lemon -c 'exec /bin/busybox env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/run/lemon-rdp/home XDG_RUNTIME_DIR=/run/lemon-rdp DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/lemon-rdp/system-bus LEMON_RDP_DESKTOP_PROBE='"$desktop_probe"' /usr/local/libexec/lemon/start-gnome-rdp-session.sh'
