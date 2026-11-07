#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
sdk=/home/hadirpc/Redmi9T-Native-Linux/gnome50-build.hT7bPE
src=$(cat logs/touchscreen-v1/client-build-stage.txt)
work=$(mktemp -d "$sdk/build/lemon-touch-callback-test.XXXXXX")
cp touchscreen-v1/{test-wlf.c,touch-pointer.c} "$work/"
p=${work#"$sdk"};src=${src#"$sdk"}
chroot "$sdk" /bin/sh -s -- "$p" "$src" <<'EOF'
set -eu
p=$1;src=$2
flags="$(pkg-config --cflags freerdp-client3) -I$src/client/Wayland -I$src/uwac/include -I$src/out/uwac/include"
libs="$(pkg-config --libs freerdp-client3) -L$src/out/uwac/libuwac -luwac0"
gcc -O2 -Wall -Wextra -Werror -Wno-error=deprecated-declarations $flags \
 "$p/test-wlf.c" "$p/touch-pointer.c" "$src/out/client/Wayland/CMakeFiles/wlfreerdp.dir/wlf_input.c.o" \
 $libs -o "$p/test"
LD_LIBRARY_PATH="$src/out/uwac/libuwac" "$p/test"
EOF
