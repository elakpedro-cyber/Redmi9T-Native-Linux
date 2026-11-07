set -euo pipefail
r=$(cat logs/v8-blocker-resolution/headless-root.txt)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
bundle="$PWD/artifacts/lemon-headless-v8b-aarch64.tar.gz"
mkdir -p "$tmp/runtime"/{bin,etc,lib,dev,tmp}
cp -a "$r"/lib/ld-musl-aarch64.so.1 "$tmp/runtime/lib/"
cp -a "$r"/bin/busybox "$tmp/runtime/bin/"
ln -s busybox "$tmp/runtime/bin/sh"
for name in mkdir rm sleep cat mv sha256sum; do ln -s busybox "$tmp/runtime/bin/$name"; done
cp -a "$r"/etc/fonts "$tmp/runtime/etc/"
cp -a "$r"/usr "$tmp/runtime/"
rm -rf -- "$tmp/runtime/usr/include"
cp userspace/headless-v8/run-wayland.sh "$tmp/runtime/run-wayland.sh"
find "$tmp/runtime" -type f | sed "s|^$tmp/||" | LC_ALL=C sort > logs/v8-blocker-resolution/bundle-files.txt
test -x "$tmp/runtime/usr/local/bin/gpu-render-v7"
test -x "$tmp/runtime/usr/bin/weston"
tar --sort=name --numeric-owner --owner=0 --group=0 --mtime=2026-11-06T00:00:00Z -C "$tmp" -cf - runtime | gzip -n -6 > "$bundle"
mkdir "$tmp/extracted"
tar -xzf "$bundle" -C "$tmp/extracted"
ch="$tmp/extracted/runtime"
for n in null:3 random:8 urandom:9; do mknod "$ch/dev/${n%:*}" c 1 "${n#*:}"; done
timeout 18 chroot "$ch" /bin/sh /run-wayland.sh
file "$ch/tmp/lemon-headless.png"
cp "$ch/tmp/lemon-headless.png" logs/v8-blocker-resolution/lemon-headless.png
cp "$ch/tmp/weston-test.log" logs/v8-blocker-resolution/weston-test.log
chroot "$ch" /lib/ld-musl-aarch64.so.1 --list /usr/local/bin/gpu-render-v7
if chroot "$ch" /usr/local/bin/gpu-render-v7 /dev/dri/renderD128; then exit 1; fi
sha256sum "$bundle"
stat -c %s "$bundle"
