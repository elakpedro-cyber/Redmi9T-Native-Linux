#!/bin/bash
set -euo pipefail

size=${LEMON_RDP_OFFLINE_SIZE:-480x720}
case "$size" in 480x720|720x1280|720x1600) ;; *) exit 2;; esac
runtime=$1
log=$2
scratch=$(mktemp -d)
client=
xserver=
cleanup() {
    for pid in "$client" "$xserver"; do
        [ -z "$pid" ] || { kill "$pid" 2>/dev/null || :; wait "$pid" 2>/dev/null || :; }
    done
    rm -rf "$scratch"
}
trap cleanup EXIT
export DISPLAY=:189 XAUTHORITY=$scratch/Xauthority
touch "$XAUTHORITY"
xauth add "$DISPLAY" . "$(mcookie)"
Xvfb "$DISPLAY" -screen 0 900x1800x24 -nolisten tcp -auth "$XAUTHORITY" >"$log/xvfb.txt" 2>&1 &
xserver=$!
for tick in {1..35}; do
    if ss -lnt 'sport = :3389' | grep -q LISTEN; then break; fi
    sleep 1
done
ss -lnt 'sport = :3389' | grep -q LISTEN
echo 'GRD listening in loopback-only namespace'
pin=$(openssl x509 -in "$runtime/rdp-test.crt" -noout -fingerprint -sha256 | cut -d= -f2)
connect_time=$(date +%s%3N)
xfreerdp3 /v:127.0.0.1 /u:offline-probe /from-stdin:force /sec:nla "/cert:fingerprint:sha256:$pin" "/size:$size" /title:LemonOfflineRDP -clipboard /log-level:WARN <"$runtime/client-credential" >"$log/freerdp.txt" 2>&1 &
client=$!
rm "$runtime/client-credential"
window=
for tick in {1..20}; do
    kill -0 "$client"
    window=$(xdotool search --onlyvisible --name '^LemonOfflineRDP$' | head -1 || :)
    [ -z "$window" ] || break
    sleep 1
done
test -n "$window"
xdotool windowfocus --sync "$window"
for tick in {1..22}; do
    xwd -silent -id "$window" -out "$log/rdp-desktop.xwd"
    if python3 -c 'import struct,sys; b=open(sys.argv[1],"rb").read(); h=struct.unpack(">25I",b[:100]); p=b[h[0]+12*h[19]:]; sys.exit(not any(p[0::4]) and not any(p[1::4]) and not any(p[2::4]))' "$log/rdp-desktop.xwd"; then
        echo "First non-black frame in $(( $(date +%s%3N) - connect_time )) ms"
        break
    fi
    kill -0 "$client"
    sleep 1
done
python3 -c 'import struct,sys; b=open(sys.argv[1],"rb").read(); h=struct.unpack(">25I",b[:100]); p=b[h[0]+12*h[19]:]; sys.exit(not any(p[0::4]) and not any(p[1::4]) and not any(p[2::4]))' "$log/rdp-desktop.xwd"
if [ "${LEMON_RDP_DESKTOP_PROBE:-0}" = 1 ]; then
    bash userspace/gnome50-v8b/desktop-probe.sh "$window" "$log" "$runtime"
    exit
fi
sleep 2
xdotool mousemove --window "$window" 453 15 click 1
sleep 4
xwd -silent -id "$window" -out "$log/rdp-mouse.xwd"
xdotool key Escape
if [ "${LEMON_RDP_INPUT_PROBE:-0}" = 1 ]; then
    touch "$runtime/rdp-open-input-probe"
    for tick in {1..15}; do
        xdotool mousemove --window "$window" 240 370 click 1 key x
        if grep -q RDP_MOUSE_OK "$runtime/input-probe.log" 2>/dev/null &&
           grep -q RDP_KEYBOARD_OK "$runtime/input-probe.log" 2>/dev/null; then
            xwd -silent -id "$window" -out "$log/rdp-input-probe.xwd"
            echo 'PASS: RDP mouse and keyboard reached a GTK Wayland client'
            exit 0
        fi
        sleep 1
    done
    xwd -silent -id "$window" -out "$log/rdp-input-probe.xwd"
    exit 1
fi
touch "$runtime/rdp-open-console"
sleep 9
xwd -silent -id "$window" -out "$log/rdp-console.xwd"
xdotool mousemove --window "$window" 180 260 click 1
xdotool key --clearmodifiers --delay 90 t o u c h space slash r u n slash g n o m e minus t e s t slash r d p minus i n p u t minus o k
xdotool key Return
for tick in {1..8}; do
    [ ! -f "$runtime/rdp-input-ok" ] || break
    sleep 1
done
test -f "$runtime/rdp-input-ok"
echo 'PASS: RDP keyboard command executed inside GNOME'
touch "$runtime/rdp-open-settings"
sleep 6
xwd -silent -id "$window" -out "$log/rdp-settings.xwd"
