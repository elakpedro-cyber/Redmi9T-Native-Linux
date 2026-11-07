#!/bin/sh
set -eu
test "${LEMON_GNOME_OFFLINE:-0}" = 1
/bin/sh /tmp/gnome50-check-private-net.sh
for attempt in $(seq 1 25); do
    if gdbus introspect --session --dest org.gnome.Mutter.RemoteDesktop --object-path /org/gnome/Mutter/RemoteDesktop >/dev/null 2>&1; then
        echo 'Mutter RemoteDesktop D-Bus available'
        break
    fi
    sleep 1
done
gdbus introspect --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager >/dev/null
echo 'GNOME SessionManager D-Bus available'
if [ "${LEMON_RDP_DESKTOP_PROBE:-0}" = 1 ]; then
    /bin/sh /tmp/gnome50-desktop-apps.sh &
fi
(
    export WAYLAND_DISPLAY=wayland-0
    for attempt in $(seq 1 50); do
        if [ -f "$XDG_RUNTIME_DIR/rdp-open-input-probe" ]; then
            exec env GDK_BACKEND=wayland GSK_RENDERER=cairo gjs -m /tmp/gnome50-input-probe.js >"$XDG_RUNTIME_DIR/input-probe.log" 2>&1
        fi
        if [ -f "$XDG_RUNTIME_DIR/rdp-open-console" ]; then
            kgx -- /bin/sh >"$XDG_RUNTIME_DIR/console.log" 2>&1 &
            break
        fi
        sleep 1
    done
    for attempt in $(seq 1 20); do
        if [ -f "$XDG_RUNTIME_DIR/rdp-open-settings" ]; then
            exec gnome-control-center >"$XDG_RUNTIME_DIR/settings.log" 2>&1
        fi
        sleep 1
    done
) &
exec /bin/sh /tmp/gnome50-start-rdp.sh
