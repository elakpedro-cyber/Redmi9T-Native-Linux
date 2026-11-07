set -euo pipefail
work=/home/hadirpc/Redmi9T-Native-Linux
root=$(mktemp -d "$work/labwc-stage.XXXXXX")
printf '%s\n' "$root" > logs/v8b-labwc-offline/root.txt
cp -a "$(cat logs/v8-blocker-resolution/headless-root.txt)/." "$root/"
apk="$work/rootfs-v5/sbin/apk.static"
"$apk" --arch aarch64 --root "$root" add --no-cache labwc foot waybar wayvnc font-dejavu wlr-randr socat dbus
chroot "$root" /sbin/apk info -vv > logs/v8b-labwc-offline/packages.txt
