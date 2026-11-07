#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || exit 1
project=$(cd "$(dirname "$0")/.." && pwd)
root=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v5/root
test -x "$root/sbin/openrc"
chroot "$root" apk info -vv > "$project/reports/rootfs-v5-packages.txt"
chroot "$root" apk info -v > "$project/config/rootfs-v5-packages.lock"
cp "$root/lib/apk/db/installed" "$project/reports/rootfs-v5-apk-installed.txt"
mkdir -p "$root/rescue" "$root/usr/local/sbin" "$root/root/.ssh"
mkdir -p "$root/etc/lemon"
install -m644 "$project/config/usbnet-mode-v5" "$root/etc/lemon/usbnet-mode"
install -m755 "$project/artifacts/BusyBox-v4" "$root/rescue/busybox"
for app in $(qemu-aarch64-static -0 busybox "$root/rescue/busybox" --list); do
    [ "$app" = busybox ] || ln -sf busybox "$root/rescue/$app"
done
install -m755 "$project/config/init-v5" "$root/init"
install -m755 "$project/config/lemon-root-shell-v5" "$root/usr/local/sbin/lemon-root-shell"
install -m755 "$project/config/lemon-diagnostics-v5" "$root/usr/local/sbin/lemon-diagnostics"
install -m755 "$project/config/lemon-health-v5" "$root/etc/init.d/lemon-health"
install -m644 "$project/config/inittab-v5" "$root/etc/inittab"
install -Dm644 "$project/pmaports/device/testing/device-xiaomi-lemon/deviceinfo" "$root/usr/share/deviceinfo/device-xiaomi-lemon"
ln -sf device-xiaomi-lemon "$root/usr/share/deviceinfo/deviceinfo"
# No Alpine default boot services: no localmount, swap, fsck, hwclock or hotplug automounter.
python3 - "$root" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
for level in ['sysinit','boot','default','shutdown']:
    folder=root/'etc/runlevels'/level
    folder.mkdir(parents=True,exist_ok=True)
    for p in folder.iterdir():
        assert p.is_symlink(),p
        p.unlink()
(root/'etc/runlevels/default/lemon-health').symlink_to('/etc/init.d/lemon-health')
(root/'etc/fstab').write_text('# RAM-only initramfs: no disk filesystems or swap\n')
(root/'etc/hostname').write_text('lemon-v5\n')
(root/'etc/resolv.conf').write_text('# Set DNS manually in RAM after optional networking is tested.\n')
p=root/'etc/rc.conf'
t='\n'.join(line for line in p.read_text().splitlines() if not line.startswith(('rc_parallel=','rc_logger=')))
p.write_text(t+'\nrc_parallel="NO"\nrc_logger="YES"\n')
PY
chmod 700 "$root/root/.ssh"
# The key file is deliberately empty: no password or pre-shared SSH credentials.
touch "$root/root/.ssh/authorized_keys"
chmod 600 "$root/root/.ssh/authorized_keys"
test -e "$root/dev/console" || mknod -m600 "$root/dev/console" c 5 1
test -e "$root/dev/null" || mknod -m666 "$root/dev/null" c 1 3
test -e "$root/dev/zero" || mknod -m666 "$root/dev/zero" c 1 5
chroot "$root" /bin/sh -n /init
chroot "$root" /bin/sh -n /usr/local/sbin/lemon-root-shell
chroot "$root" /bin/sh -n /usr/local/sbin/lemon-diagnostics
chroot "$root" /bin/sh -n /etc/init.d/lemon-health
{
    chroot "$root" /bin/busybox 2>&1 | sed -n '1,2p'
    chroot "$root" /sbin/openrc --version
    chroot "$root" /sbin/apk --version
    chroot "$root" /sbin/ip -Version
    chroot "$root" /bin/lsblk --version
    chroot "$root" /usr/bin/curl --version
    chroot "$root" /usr/sbin/dropbear -V
} > "$project/reports/rootfs-v5-execution.txt" 2>&1
cd "$root"
find . -print0 | LC_ALL=C sort -z | cpio --null -o --format=newc --owner=0:0 --reproducible | gzip -n -9 > "$project/artifacts/initramfs-v5.cpio.gz"
tar --sort=name --numeric-owner -cpf - . | gzip -n -9 > "$project/artifacts/alpine-rootfs-v5.tar.gz"
du -sh .
wc -c "$project/artifacts/initramfs-v5.cpio.gz"
