#!/bin/bash
set -euo pipefail
window=$1
log=$2
runtime=${3:-}
capture() { xwd -silent -id "$window" -out "$log/desktop-$1.xwd"; }
request_app() {
    if [ -n "$runtime" ]; then
        touch "$runtime/test-$1"
    else
        python3 userspace/gnome50-v8b/rdp-test-action.py "$log/bridge.json" "$1"
    fi
}

sleep 8
xdotool key Escape
sleep .5
capture before-mouse
python3 userspace/gnome50-v8b/rdp-frame-probe.py "$window" mouse | tee "$log/frame-mouse.txt"
capture mouse-overview
xdotool key Escape
sleep .7
python3 userspace/gnome50-v8b/rdp-frame-probe.py "$window" keyboard | tee "$log/frame-keyboard.txt"
capture app-grid
xdotool key Escape Escape
request_app console
sleep 9
xdotool type --clearmodifiers --delay 65 -- 'echo LEMON_RDP_KEYBOARD_OK'
xdotool key Return
sleep 1
capture console
request_app settings
sleep 7
capture settings
request_app files
sleep 7
capture files
request_app editor
sleep 7
capture editor
xdotool key Super_L
sleep 1
capture windows
xdotool key Escape alt+Tab
sleep 1
capture focus
