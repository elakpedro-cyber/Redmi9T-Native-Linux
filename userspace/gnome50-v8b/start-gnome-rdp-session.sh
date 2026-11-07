#!/bin/sh
set -eu
umask 077
ulimit -c 0

: "${HOME:?}"
: "${XDG_RUNTIME_DIR:?}"
test "$(id -u)" -ne 0
/bin/sh "/usr/local/libexec/lemon/check-private-net.sh"
test -z "${LEMON_GNOME_OFFLINE:-}"
case "${1:-}" in ''|--preflight-only) ;; *) exit 2;; esac
unset DISPLAY WAYLAND_DISPLAY WAYLAND_SOCKET LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER MESA_LOADER_DRIVER_OVERRIDE
export LEMON_REQUIRE_RENDER_NODE=/dev/dri/renderD128
export XDG_SESSION_TYPE=wayland XDG_SESSION_CLASS=user XDG_CURRENT_DESKTOP=GNOME XDG_SESSION_DESKTOP=gnome
export DESKTOP_SESSION=lemon-headless GSETTINGS_BACKEND=dconf
export XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share" XDG_CACHE_HOME="$HOME/.cache"
export LEMON_GNOME_LOG="$XDG_RUNTIME_DIR/gnome.log"

exec dbus-run-session -- /bin/sh -c '
    set -eu
    /bin/sh /usr/local/libexec/lemon/privilege-preflight.sh
    if [ "${1:-}" = --preflight-only ]; then exit 0; fi
    mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"
    pipewire >"$XDG_RUNTIME_DIR/pipewire.log" 2>&1 &
    pw=$!
    wp= session= rdp=
    cleanup() {
        for pid in "$rdp" "$session" "$wp" "$pw"; do
            [ -z "$pid" ] || kill "$pid" 2>/dev/null || :
        done
    }
    trap cleanup EXIT
    /bin/sh /usr/local/libexec/lemon/wait-pipewire.sh "$pw"
    wireplumber >"$XDG_RUNTIME_DIR/wireplumber.log" 2>&1 &
    wp=$!
    gnome-session --session=lemon-headless --failsafe >"$LEMON_GNOME_LOG" 2>&1 &
    session=$!
    /usr/local/libexec/lemon/start-rdp.sh >"$XDG_RUNTIME_DIR/rdp.log" 2>&1 &
    rdp=$!
    if [ "${LEMON_RDP_DESKTOP_PROBE:-0}" = 1 ]; then
        /bin/sh /usr/local/libexec/lemon/desktop-apps.sh &
    fi
    while :; do
        for service in "gnome-session:$session" "rdp:$rdp" "pipewire:$pw" "wireplumber:$wp"; do
            pid=${service#*:}
            if ! kill -0 "$pid" 2>/dev/null; then
                status=0
                wait "$pid" || status=$?
                printf "FAIL [session supervisor]: %s exited with status %s\n" "${service%:*}" "$status" >&2
                exit 1
            fi
        done
        sleep 1
    done
' lemon-session "$@"
