#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
sdk=/home/hadirpc/Redmi9T-Native-Linux/gnome50-build.hT7bPE
stage=$(mktemp -d "$sdk/build/lemon-touch-input.XXXXXX")
cp touchscreen-v1/{touch-pointer.c,test-pointer.c} "$stage/"
p=${stage#"$sdk"}
chroot "$sdk" /bin/sh -s -- "$p" <<'EOF'
set -eu
p=$1
flags="$(pkg-config --cflags freerdp-client3)"
gcc -O2 -Wall -Wextra -Werror -Wno-error=deprecated-declarations -fPIC -shared $flags "$p/touch-pointer.c" -o "$p/touch-pointer.so"
gcc -O2 -Wall -Wextra -Werror -Wno-error=deprecated-declarations $flags "$p/test-pointer.c" "$p/touch-pointer.c" -o "$p/test-pointer"
"$p/test-pointer"
EOF
cp "$stage/touch-pointer.so" artifacts/touchscreen-v1/
