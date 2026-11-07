#!/bin/sh
set -eu
umask 077
export XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=GNOME
export XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share" XDG_CACHE_HOME="$HOME/.cache"
export LEMON_GNOME_LOG="$XDG_RUNTIME_DIR/gnome.log"
if [ "${LEMON_PHYSICAL_OFFLINE:-0}" = 1 ]; then
    export LEMON_GNOME_OFFLINE=1 LIBGL_ALWAYS_SOFTWARE=1
else
    export LEMON_REQUIRE_RENDER_NODE=/dev/dri/renderD128
fi
if [ "${1:-}" != --bus ]; then
    exec dbus-run-session -- /bin/sh "$0" --bus
fi
if [ "${LEMON_GNOME_OFFLINE:-0}" != 1 ]; then
    /bin/sh /usr/local/libexec/lemon/privilege-preflight.sh
fi
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"
pw= wp= shell= rdp= stopper=
cleanup() {
    trap - EXIT INT TERM HUP
    set +e
    [ -z "$stopper" ] || kill -TERM "$stopper" 2>/dev/null
    if [ -n "$shell" ] && kill -0 "$shell" 2>/dev/null; then
        echo USER_LOGOUT_REQUEST
        if ! /bin/busybox timeout -k 1 2 gdbus call --session --dest org.gnome.SessionManager \
            --object-path /org/gnome/SessionManager --method org.gnome.SessionManager.Logout 2; then
            echo USER_LOGOUT_FALLBACK_TERM
            kill -TERM "$shell" 2>/dev/null
        fi
        wait "$shell"
        echo USER_GNOME_SESSION_REAPED
    fi
    for item in "rdp:$rdp" "wireplumber:$wp" "pipewire:$pw"; do
        pid=${item#*:}
        [ -n "$pid" ] || continue
        printf 'USER_STOP component=%s pid=%s\n' "${item%:*}" "$pid"
        kill -TERM "$pid" 2>/dev/null
        wait "$pid" 2>/dev/null
    done
}
trap cleanup EXIT
trap 'exit 0' INT TERM HUP

# The baseline profile preserves v1. The optional quiet profile only reduces animation work.
if [ "${LEMON_PROFILE:-baseline}" = quiet ]; then
    gsettings set org.gnome.desktop.interface enable-animations false
fi
pipewire >"$XDG_RUNTIME_DIR/pipewire.log" 2>&1 &
pw=$!
/bin/sh /usr/local/libexec/lemon/wait-pipewire.sh "$pw"
wireplumber >"$XDG_RUNTIME_DIR/wireplumber.log" 2>&1 &
wp=$!
gnome-session --session=lemon-headless --failsafe >"$LEMON_GNOME_LOG" 2>&1 &
shell=$!
(
    trap - EXIT INT TERM HUP
    for _ in $(seq 1 100); do
        if gdbus introspect --session --dest org.gnome.Mutter.RemoteDesktop --object-path /org/gnome/Mutter/RemoteDesktop >/dev/null 2>&1; then break; fi
        kill -0 "$shell"
        sleep .2
    done
    exec /bin/sh /usr/local/libexec/lemon/start-rdp.sh
) >"$XDG_RUNTIME_DIR/rdp.log" 2>&1 &
rdp=$!
(
    trap - EXIT INT TERM HUP
    for _ in $(seq 1 120); do
        [ ! -f "$XDG_RUNTIME_DIR/client-started" ] || break
        sleep .2
    done
    sleep 4
    WAYLAND_DISPLAY=wayland-0 kgx -- /bin/sh >"$XDG_RUNTIME_DIR/console.log" 2>&1
) &
if [ "${LEMON_PHYSICAL_ACTIONS:-0}" = 1 ]; then
    (
        trap - EXIT INT TERM HUP
        for _ in $(seq 1 120); do
            [ ! -f "$XDG_RUNTIME_DIR/client-started" ] || break
            sleep .2
        done
        sleep 13
        gjs -m /run/lemon/physical-input.js
    ) >"$XDG_RUNTIME_DIR/input.log" 2>&1 &
fi
owner=$$
(
    trap - EXIT INT TERM HUP
    while kill -0 "$owner" 2>/dev/null; do
        for item in "rdp:$rdp" "pipewire:$pw" "wireplumber:$wp"; do
            if ! kill -0 "${item#*:}" 2>/dev/null; then
                echo "USER_COMPONENT_EXIT component=${item%:*}"
                kill -TERM "$owner"
                exit
            fi
        done
        if [ -f "$XDG_RUNTIME_DIR/stop-requested" ]; then kill -TERM "$owner"; exit; fi
        sleep .1
    done
) &
stopper=$!
wait "$shell"
