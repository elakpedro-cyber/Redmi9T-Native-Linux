#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
sdk=/home/hadirpc/Redmi9T-Native-Linux/gnome50-build.hT7bPE
work=$(mktemp -d "$sdk/tmp/physical-v2-abi.XXXXXX")
trap 'rm -rf "$work"' EXIT
cp userspace/gnome-physical-v2/test-trace.c artifacts/gnome-physical-v2/frame-trace.so "$work/"
p=${work#"$sdk"}
chroot "$sdk" gcc -O2 -shared -fPIC -DPROVIDER "$p/test-trace.c" -o "$p/provider.so"
chroot "$sdk" gcc -O2 "$p/test-trace.c" "$p/provider.so" -o "$p/test"
chroot "$sdk" /bin/sh -c "LD_PRELOAD='$p/frame-trace.so' LEMON_FRAME_TRACE='$p/events.jsonl' '$p/test'"
cat "$work/events.jsonl"
