#!/bin/sh
set -eu
export WAYLAND_DISPLAY=wayland-0 GDK_BACKEND=wayland

for app in console settings files editor; do
    while [ ! -f "$XDG_RUNTIME_DIR/test-$app" ]; do sleep .2; done
    rm "$XDG_RUNTIME_DIR/test-$app"
    case "$app" in
        console) set -- /usr/bin/kgx -- /bin/sh ;;
        settings) set -- /usr/bin/gnome-control-center ;;
        files) set -- /usr/bin/nautilus --new-window "$HOME" ;;
        editor) set -- /usr/bin/gnome-text-editor ;;
    esac
    (
        status=0
        "$@" || status=$?
        printf 'LEMON_APP_EXIT app=%s code=%s\n' "$app" "$status"
    ) >"$XDG_RUNTIME_DIR/app-$app.log" 2>&1 &
done
wait
