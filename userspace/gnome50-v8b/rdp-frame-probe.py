import hashlib
import statistics
import struct
import subprocess
import sys
import time

window, action = sys.argv[1:]
command = {
    "mouse": ["mousemove", "--window", window, "33", "15", "click", "1"],
    "keyboard": ["key", "super+a"],
}[action]


def pixels():
    frame = subprocess.check_output(["xwd", "-silent", "-id", window])
    h = struct.unpack(">25I", frame[:100])
    start = h[0] + 12 * h[19]
    return hashlib.sha256(frame[start + 155 * h[12]:start + (h[5] - 16) * h[12]]).digest()


previous = pixels()
start = time.monotonic()
event = subprocess.Popen(["xdotool", *command])
changes = []
samples = 0
while time.monotonic() - start < 1.25:
    current = pixels()
    now = time.monotonic()
    samples += 1
    if previous != current:
        changes.append(now - start)
        previous = current
    time.sleep(.015)
event.wait(timeout=2)
if event.returncode:
    raise SystemExit(event.returncode)
intervals = [(b - a) * 1000 for a, b in zip(changes, changes[1:])]
print(f"{action} samples={samples} changes={len(changes)} duration_s={now-start:.3f}")
if changes:
    print(f"{action} first_visible_change_ms={changes[0]*1000:.1f}")
if intervals:
    print(f"{action} sample_change_interval_median_ms={statistics.median(intervals):.1f}")
