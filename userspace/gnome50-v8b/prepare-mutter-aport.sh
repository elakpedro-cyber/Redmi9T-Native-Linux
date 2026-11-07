#!/bin/sh
set -eu

source_aport=${1:?Pass a clean copy of community/mutter from Alpine 3.24 aports}
output=${2:?Pass a new output directory}
test ! -e "$output"
grep -qx 'pkgver=50.2' "$source_aport/APKBUILD"
grep -qx 'pkgrel=1' "$source_aport/APKBUILD"
mkdir "$output"
cp -R "$source_aport/." "$output/"
cp "$(dirname "$0")/require-render-node.patch" "$output/"
sed -i -e 's/^pkgrel=1$/pkgrel=2/' -e '/^[[:space:]]*fix-log-spam\.patch$/a\	require-render-node.patch' "$output/APKBUILD"
grep -q '^[[:space:]]*require-render-node.patch$' "$output/APKBUILD"
printf '%s\n' "In the isolated Alpine aarch64 builder: cd $output && abuild checksum && abuild -r"
