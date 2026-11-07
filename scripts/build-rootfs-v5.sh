#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Run as WSL root'; exit 1; }
project=$(cd "$(dirname "$0")/.." && pwd)
work=/home/hadirpc/Redmi9T-Native-Linux/rootfs-v5
root="$work/root"
mkdir -p "$work" "$project/downloads/v5"
archive=alpine-minirootfs-3.24.4-aarch64.tar.gz
url="https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/aarch64/$archive"
curl -fL --retry 3 "$url" -o "$project/downloads/v5/$archive"
curl -fL --retry 3 "$url.sha256" -o "$project/downloads/v5/$archive.sha256"
(cd "$project/downloads/v5"; sha256sum -c "$archive.sha256")
# Check the release metadata digest observed during research as well.
echo "4b14c18f7e90a063b61462ea1462a5732c154bf6adad594974fe6487cd98a8de  $project/downloads/v5/$archive" | sha256sum -c -
[ ! -e "$root" ] || { echo 'Refusing to replace existing rootfs'; exit 1; }
mkdir -p "$root"
tar xpf "$project/downloads/v5/$archive" -C "$root"
cp /etc/resolv.conf "$root/etc/resolv.conf"
printf '%s\n' https://dl-cdn.alpinelinux.org/alpine/v3.24/main https://dl-cdn.alpinelinux.org/alpine/v3.24/community > "$root/etc/apk/repositories"
curl -fL --retry 3 https://dl-cdn.alpinelinux.org/alpine/v3.24/main/x86_64/apk-tools-static-3.0.9-r0.apk -o "$project/downloads/v5/apk-tools-static-3.0.9-r0.apk"
tar xzf "$project/downloads/v5/apk-tools-static-3.0.9-r0.apk" -C "$work" sbin/apk.static
# Native apk preserves setuid/file capabilities; ARM64 package scripts use binfmt.
"$work/sbin/apk.static" --arch aarch64 --root "$root" add --no-cache alpine-base openrc iproute2 iputils lsblk blkid strace curl ca-certificates dropbear dropbear-openrc
chroot "$root" /sbin/apk info -vv > "$project/reports/rootfs-v5-packages.txt"
chroot "$root" /sbin/apk info -v > "$project/config/rootfs-v5-packages.lock"
cp "$root/lib/apk/db/installed" "$project/reports/rootfs-v5-apk-installed.txt"
echo 'Base Alpine rootfs ready; run configure-rootfs-v5.sh before packaging.'
