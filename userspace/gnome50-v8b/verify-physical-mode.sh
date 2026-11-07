#!/bin/sh
# Verify an already enumerated output from inside an authorized native session.
set -eu

connector=${1:?Provide the connector from gdctl show}
mode=${2:?Provide the exact 1080x2340 mode ID from gdctl show}
case "$connector" in DSI-[0-9]*) ;; *) exit 2 ;; esac
case "$mode" in 1080x2340@*) ;; *) exit 2 ;; esac
: "${DBUS_SESSION_BUS_ADDRESS:?Run inside the native GNOME session}"
exec gdctl set --verify --layout-mode logical --logical-monitor \
    --primary --scale 2 --transform normal --monitor "$connector" --mode "$mode"
