#!/bin/sh
set -eu
test "${LEMON_GNOME_OFFLINE:-0}" = 1 || {
    echo 'GNOME launcher is limited to offline tests until FD610 enforcement is verified.' >&2
    exit 1
}
mode=${LEMON_GNOME_MODE:-480x720}
case "$mode" in 480x720|720x1280) ;; *) exit 1;; esac

if [ "${1:-}" = "--session" ]; then
    shift
    (sleep "${LEMON_OFFLINE_PIPEWIRE_DELAY:-0}"; exec pipewire) >"$XDG_RUNTIME_DIR/pipewire.log" 2>&1 &
    pipewire_pid=$!
    wp_pid=
    rdp_pid=
    trap 'for pid in "$rdp_pid" "$wp_pid" "$pipewire_pid"; do
        [ -z "$pid" ] || { kill "$pid" 2>/dev/null || :; wait "$pid" 2>/dev/null || :; }
    done' EXIT
    /bin/sh /tmp/gnome50-wait-pipewire.sh "$pipewire_pid"
    wireplumber >"$XDG_RUNTIME_DIR/wireplumber.log" 2>&1 &
    wp_pid=$!
    if [ "${2:-}" = "--probe-rdp" ]; then
        /bin/sh /tmp/gnome50-rdp-probe.sh &
        rdp_pid=$!
    fi
    if [ "${1:-}" = "--session48" ]; then
        gnome-session --session=lemon-headless --failsafe
    else
        gnome-shell --wayland --headless --no-x11 --virtual-monitor="$mode"
    fi
    exit
fi

: "${XDG_RUNTIME_DIR:?Provide a private RAM-backed runtime directory}"
export XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=GNOME
unset DISPLAY WAYLAND_DISPLAY WAYLAND_SOCKET
exec dbus-run-session -- /bin/sh "$0" --session "$@"
