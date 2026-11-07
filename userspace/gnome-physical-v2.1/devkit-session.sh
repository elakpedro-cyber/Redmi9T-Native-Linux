#!/bin/sh
set -eu
umask 077
export XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=GNOME GDK_BACKEND=wayland
export XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share" XDG_CACHE_HOME="$HOME/.cache"
if [ "${LEMON_PHYSICAL_OFFLINE:-0}" = 1 ]; then
    export LIBGL_ALWAYS_SOFTWARE=1 LEMON_GNOME_OFFLINE=1
else
    export LEMON_REQUIRE_RENDER_NODE=/dev/dri/renderD128
fi
if [ "${1:-}" != --bus ]; then
    exec dbus-run-session -- /bin/sh "$0" --bus
fi
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"
pipewire >"$XDG_RUNTIME_DIR/pipewire.log" 2>&1 &
pw=$!
/bin/sh /usr/local/libexec/lemon/wait-pipewire.sh "$pw"
wireplumber >"$XDG_RUNTIME_DIR/wireplumber.log" 2>&1 &
wp=$!
dbus-monitor --profile "type='method_call',destination='org.gnome.Mutter.RemoteDesktop'" \
    "type='method_call',destination='org.gnome.Mutter.ScreenCast'" >"$XDG_RUNTIME_DIR/devkit-dbus.log" 2>&1 &
gnome-session --session=lemon-headless --failsafe >"$XDG_RUNTIME_DIR/gnome.log" 2>&1 &
session=$!
cleanup() {
    trap - EXIT TERM INT HUP
    kill -TERM "$session" "$wp" "$pw" 2>/dev/null || :
    wait "$session" 2>/dev/null || :
}
trap cleanup EXIT
trap 'exit 0' TERM INT HUP
(
    trap - EXIT TERM INT HUP
    for _ in $(seq 1 150); do
        if grep -q 'GNOME Shell started' "$XDG_RUNTIME_DIR/gnome.log"; then break; fi
        kill -0 "$session"
        sleep .2
    done
    WAYLAND_DISPLAY=lemon-gnome kgx -- /bin/sh >"$XDG_RUNTIME_DIR/console.log" 2>&1 &
    if [ "${LEMON_PHYSICAL_ACTIONS:-0}" = 1 ]; then
        sleep 4
        LEMON_GNOME_WAYLAND_DISPLAY=lemon-gnome gjs -m /run/lemon/physical-input.js >"$XDG_RUNTIME_DIR/input.log" 2>&1
    fi
) &
owner=$$
(
    trap - EXIT TERM INT HUP
    while kill -0 "$owner" 2>/dev/null; do
        if [ -f "$XDG_RUNTIME_DIR/stop-requested" ]; then kill -TERM "$owner"; exit; fi
        sleep .1
    done
) &
wait "$session"
