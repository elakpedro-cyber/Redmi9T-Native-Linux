set -euo pipefail
work=/home/hadirpc/Redmi9T-Native-Linux
root=$(mktemp -d "$work/desktop-build.XXXXXX")
printf '%s\n' "$root" > logs/v8b-desktop-offline/build-root.txt
cp -a "$(cat logs/v8-blocker-resolution/headless-root.txt)/." "$root/"
apk="$work/rootfs-v5/sbin/apk.static"
"$apk" --arch aarch64 --root "$root" add --no-cache font-dejavu
"$apk" --arch aarch64 --root "$root" add --no-cache --virtual .desktop-build gcc musl-dev wayland-dev wayland-protocols cairo-dev
