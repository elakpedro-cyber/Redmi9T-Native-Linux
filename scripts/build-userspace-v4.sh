#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work="$HOME/Redmi9T-Native-Linux/userspace-v4"
mkdir -p "$work"
if [ ! -d "$work/busybox-1.37.0" ]; then
    tar xf "$project/downloads/busybox-1.37.0.tar.bz2" -C "$work"
fi
cd "$work/busybox-1.37.0"
cp "$project/config/busybox.config" .config
python3 - <<'PY'
from pathlib import Path
p=Path('.config'); t=p.read_text()
for name in ['GUNZIP','ZCAT','BASE64','OD','HEXDUMP']:
    key='CONFIG_'+name
    assert '# '+key+' is not set' in t or key+'=y' in t, key
    t=t.replace('# '+key+' is not set',key+'=y')
p.write_text(t)
PY
make CROSS_COMPILE=aarch64-linux-gnu- oldconfig </dev/null
make CROSS_COMPILE=aarch64-linux-gnu- -j12
cp .config "$project/config/busybox-v4.config"
cp busybox "$project/artifacts/BusyBox-v4"
qemu-aarch64-static ./busybox --list > "$project/reports/busybox-v4-applets.txt"
file busybox
