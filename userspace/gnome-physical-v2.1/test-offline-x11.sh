#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
case "$(uname -r)" in *microsoft*|*WSL*) ;; *) echo 'PC WSL test only'; exit 2;; esac
if [ "${1:-}" != private ]; then
    exec unshare --mount --propagation private /bin/bash "$0" private
fi
# WSLg owns the host X11 directory. Xvfb gets a separate one, never chmod the host mount.
mount -t tmpfs -o mode=1777,nosuid,nodev tmpfs /tmp
mkdir -m 1777 /tmp/.X11-unix
LEMON_OFFLINE_X11_AUTO=1 LEMON_OFFLINE_SECONDS=90 bash userspace/gnome-physical-v2.1/test-offline.sh B "${LEMON_OFFLINE_TAG:-B-x11-final}"
