#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux"
mkdir -p "$work"
cd "$work"
[ -d busybox-1.37.0 ] || tar xf "$project/downloads/busybox-1.37.0.tar.bz2"
cd busybox-1.37.0
make allnoconfig >/dev/null
python3 - <<'PY'
from pathlib import Path
p=Path('.config')
text=p.read_text()
for name in '''BUSYBOX STATIC ASH SH_IS_ASH ASH_JOB_CONTROL ASH_ALIAS ASH_ECHO ASH_PRINTF ASH_TEST ASH_OPTIMIZE_FOR_SIZE FEATURE_SH_MATH FEATURE_SH_STANDALONE FEATURE_PREFER_APPLETS FEATURE_INSTALLER CAT ECHO PRINTF TEST TRUE FALSE LS FEATURE_LS_LONG MKDIR LN SLEEP HEAD TAIL UNAME DMESG MOUNT FEATURE_MOUNT_FLAGS UMOUNT GETTY SETSID STTY PS FEATURE_PS_LONG KILL REBOOT POWEROFF FIND GREP SED READLINK CUT WC CP MV RM CHMOD ENV SYNC'''.split():
    key='CONFIG_'+name
    text=text.replace('# '+key+' is not set',key+'=y')
p.write_text(text)
PY
yes '' | make oldconfig >/dev/null || true
make CROSS_COMPILE=aarch64-linux-gnu- -j12
cp .config "$project/config/busybox.config"
root="$work/initramfs"
mkdir -p "$root"/{bin,sbin,dev,proc,sys,run,tmp,etc}
cp busybox "$root/bin/busybox"
for app in $(qemu-aarch64-static ./busybox --list); do
    [ "$app" = busybox ] || ln -sf busybox "$root/bin/$app"
done
cp "$project/config/init" "$root/init"
chmod 755 "$root/init"
if [ ! -e "$root/dev/console" ]; then
    echo 'Creating /dev/console requires root; using sudo once for this node.'
    sudo mknod "$root/dev/console" c 5 1
fi
cd "$root"
find . -print0 | LC_ALL=C sort -z | cpio --null -o --format=newc --owner=0:0 | gzip -n -9 > "$project/artifacts/initramfs.cpio.gz"
qemu-aarch64-static "$root/bin/busybox" uname -m
file "$root/bin/busybox"
