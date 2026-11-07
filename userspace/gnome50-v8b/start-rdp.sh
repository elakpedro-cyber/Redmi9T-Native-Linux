#!/bin/sh
set -eu
umask 077
export TZ=Etc/UTC
test -r /usr/share/zoneinfo/Etc/UTC

: "${XDG_RUNTIME_DIR:?}"
: "${DBUS_SESSION_BUS_ADDRESS:?}"
test "$(id -u)" -ne 0
test "$(stat -c '%u:%a' "$XDG_RUNTIME_DIR")" = "$(id -u):700"
net_check=/usr/local/libexec/lemon/check-private-net.sh
if [ "${LEMON_GNOME_OFFLINE:-0}" = 1 ]; then net_check=/tmp/gnome50-check-private-net.sh; fi
/bin/sh "$net_check"
test "$(stat -c '%a' "$XDG_RUNTIME_DIR/rdp-test.key")" = 600
test "$(stat -c '%a' "$XDG_RUNTIME_DIR/rdp-credentials")" = 600

if [ "${LEMON_GNOME_OFFLINE:-0}" != 1 ]; then
    test "${LEMON_REQUIRE_RENDER_NODE:-}" = /dev/dri/renderD128
    test "$(stat -f -c %T "$XDG_RUNTIME_DIR")" = tmpfs
    : "${LEMON_GNOME_LOG:?}"
    for attempt in $(seq 1 20); do
        if grep -Fq 'LEMON_FD610_EGL_VERIFIED node=/dev/dri/renderD128 renderer=FD610' "$LEMON_GNOME_LOG" 2>/dev/null &&
           gdbus introspect --session --dest org.gnome.Mutter.RemoteDesktop --object-path /org/gnome/Mutter/RemoteDesktop >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    grep -Fq 'LEMON_FD610_EGL_VERIFIED node=/dev/dri/renderD128 renderer=FD610' "$LEMON_GNOME_LOG"
    if grep -Eiq 'software fallback refused|renderer=.*(llvmpipe|softpipe|swrast)|LEMON_FD610_REJECTED' "$LEMON_GNOME_LOG"; then
        exit 1
    fi
fi

gdbus introspect --session --dest org.gnome.Mutter.RemoteDesktop --object-path /org/gnome/Mutter/RemoteDesktop >/dev/null
gdbus introspect --session --dest org.gnome.SessionManager --object-path /org/gnome/SessionManager >/dev/null
grdctl --headless rdp set-tls-key "$XDG_RUNTIME_DIR/rdp-test.key"
grdctl --headless rdp set-tls-cert "$XDG_RUNTIME_DIR/rdp-test.crt"
grdctl --headless rdp set-auth-methods credentials
{
    IFS= read -r username
    test -n "$username"
    grdctl --headless rdp set-credentials "$username"
} <"$XDG_RUNTIME_DIR/rdp-credentials"
rm "$XDG_RUNTIME_DIR/rdp-credentials"
grdctl --headless rdp disable-port-negotiation
gsettings set org.gnome.desktop.remote-desktop.rdp.headless enable true
test "$(gsettings get org.gnome.desktop.remote-desktop.rdp.headless enable)" = true
if [ "${LEMON_GNOME_OFFLINE:-0}" = 1 ] && [ "${LEMON_RDP_GDB:-0}" = 1 ]; then
    exec /tmp/qemu-aarch64-static -g 19130 /usr/libexec/gnome-remote-desktop-daemon --headless --rdp-port 3389 --max-parallel-connections 1 </dev/null
fi
exec /usr/libexec/gnome-remote-desktop-daemon --headless --rdp-port 3389 --max-parallel-connections 1 </dev/null
