"""Stage and run the bounded SimpleDRM/Devkit test over pinned USB SSH."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "logs/v8b-physical-gnome"
RUNNER = Path(__file__).with_name("run-physical-devkit.sh")
identity = json.loads((ROOT / "logs/v6-authorized/test-client-identity.json").read_text())["private_key_path"]
pin = LOG / "known_hosts"
SSH = ["ssh.exe", "-T", "-i", identity, "-oBatchMode=yes", "-oIdentitiesOnly=yes",
       "-oBindAddress=192.168.77.1", "-oConnectTimeout=5", "-oKexAlgorithms=curve25519-sha256",
       "-oStrictHostKeyChecking=yes", f"-oUserKnownHostsFile={pin}", "root@192.168.77.2"]
base = (LOG / "phone-temp.txt").read_text().strip()
if not re.fullmatch(r"/tmp/lemon-gnome-lcd\.[a-zA-Z0-9]{6}", base):
    raise SystemExit("Unexpected test directory")

SNAPSHOT = r"""
uname -r
cat /sys/class/tty/tty0/active /proc/swaps
ip -4 addr show usb0
awk '/^MemAvailable:/{print}' /proc/meminfo
grep ' sd[a-f] ' /proc/diskstats
cat /sys/bus/platform/devices/5900000.gpu/power/runtime_status
for z in /sys/class/thermal/thermal_zone*/temp; do [ ! -r "$z" ] || cat "$z" | sed 's/^/TEMP /'; done
dmesg | grep -Ei '((gpu|adreno|iommu|smmu|msm).*(fault|hang|timeout|recover))|((fault|hang).*(gpu|adreno|iommu|smmu|msm))' || :
"""


def remote(command, *, timeout=10, data=None, file=None):
    return subprocess.run(SSH + [f"b={shlex.quote(base)}; set -eu; {command}"],
                          input=data, stdin=file, capture_output=True, timeout=timeout, check=True).stdout


def stop():
    remote(r"""
        test -r "$b/watchdog.pid" || exit 0
        p=$(cat "$b/watchdog.pid")
        case "$p" in ''|*[!0-9]*) exit 3;; esac
        if [ "$(readlink "/proc/$p/exe" 2>/dev/null || :)" = "$b/watchdog" ]; then kill -TERM "$p"; fi
    """)


def stage():
    global base
    exists = remote('if [ -d "$b/gnome" ]; then echo ready; fi')
    if exists.strip() != b"ready":
        base = remote(r"""test "$(stat -f -c %T /tmp)" = tmpfs
            awk '/^MemAvailable:/ {exit !($2 >= 2800000)}' /proc/meminfo
            umask 077; mktemp -d /tmp/lemon-gnome-lcd.XXXXXX""").decode().strip()
        if not re.fullmatch(r"/tmp/lemon-gnome-lcd\.[a-zA-Z0-9]{6}", base):
            raise RuntimeError("Unexpected staging directory")
        (LOG / "phone-temp.txt").write_text(base + "\n")
        checksum = (LOG / "gnome-root.sha256").read_text().split()[0]
        if not re.fullmatch(r"[a-f0-9]{64}", checksum):
            raise RuntimeError("Invalid GNOME checksum")
        with (LOG / "gnome-root.tar.gz").open("rb") as file:
            result = remote(
                r"""cat >"$b/gnome.tar.gz"
                echo 'CHECKSUM' " $b/gnome.tar.gz" | sha256sum -c
                mkdir -m 755 "$b/gnome"; tar -xzf "$b/gnome.tar.gz" -C "$b/gnome"
                rm "$b/gnome.tar.gz"; chmod 755 "$b/gnome"
                """.replace("CHECKSUM", checksum), timeout=200, file=file)
        (LOG / "phone-gnome-stage.txt").write_bytes(result)
    archive = LOG / "weston-root.tar.gz"
    checksum = (LOG / "weston-root.sha256").read_text().split()[0]
    if not re.fullmatch(r"[a-f0-9]{64}", checksum):
        raise RuntimeError("Invalid archive checksum")
    with archive.open("rb") as file:
        result = remote(
            r"""test "$(stat -f -c %T "$b")" = tmpfs; test ! -e "$b/weston";
            cat >"$b/weston.tar.gz";
            echo 'CHECKSUM' " $b/weston.tar.gz" | sha256sum -c;
            mkdir -m 755 "$b/weston"; tar -xzf "$b/weston.tar.gz" -C "$b/weston"; rm "$b/weston.tar.gz"
            """.replace("CHECKSUM", checksum),
            timeout=140, file=file,
        )
    (LOG / "phone-weston-stage.txt").write_bytes(result)
    for source, name in ((RUNNER, "run.sh"),
                         (ROOT / "logs/v8b-physical-weston/probe", "probe"),
                         (ROOT / "logs/v8b-physical-weston/watchdog", "watchdog")):
        data = source.read_bytes()
        if name.endswith(".sh"):
            data = data.replace(b"\r\n", b"\n")
        remote(f'cat >"$b/{name}"; chmod 700 "$b/{name}"', data=data)
    result = remote(
        r"""test "$(stat -c %u:%a "$b")" = 0:700
        "$b/watchdog" 3 /bin/true
        chroot "$b/gnome" /bin/busybox id lemon
        chroot "$b/gnome" /usr/bin/gnome-shell --version
        chroot "$b/weston" /usr/bin/weston --version
        """,
    )
    (LOG / "phone-preflight.txt").write_bytes(result)
    print(result.decode())


def run(limit):
    log = LOG / f"hardware-{limit}"
    log.mkdir(exist_ok=False)
    baseline = remote(SNAPSHOT)
    (log / "before.txt").write_bytes(baseline)
    faults = {line for line in baseline.splitlines() if line.startswith(b"[")}
    with (log / "session.txt").open("wb") as out, (log / "samples.txt").open("wb") as samples:
        proc = subprocess.Popen(SSH + [f'exec env LEMON_PHYSICAL_VIEWER=rdp /bin/sh {shlex.quote(base)}/run.sh {shlex.quote(base)} {limit}'],
                                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
        try:
            while proc.poll() is None:
                time.sleep(2)
                current = remote(SNAPSHOT, timeout=7)
                samples.write(current)
                samples.flush()
                if {line for line in current.splitlines() if line.startswith(b"[")} - faults:
                    raise RuntimeError("New GPU/IOMMU fault message")
                memory = re.search(rb"MemAvailable:\s+(\d+)", current)
                if not memory or int(memory[1]) < 524288:
                    raise RuntimeError("RAM below 512 MiB")
                if any(int(t) >= 75000 for t in re.findall(rb"^TEMP (\d+)", current, re.M)):
                    raise RuntimeError("Thermal stop at 75 °C")
                renderer = remote(r'''if [ -r "$b/gnome/run/lemon/gnome.log" ]; then
                    grep -Ei 'LEMON_FD610|software fallback refused|llvmpipe|softpipe|swrast' "$b/gnome/run/lemon/gnome.log" || :
                    fi''')
                if re.search(rb"LEMON_FD610_REJECTED|software fallback refused|llvmpipe|softpipe|swrast",
                             renderer, re.I):
                    raise RuntimeError("GNOME hardware-renderer guard rejected the session")
        finally:
            if proc.poll() is None:
                stop()
                proc.wait(timeout=12)
    print(f"session exit {proc.returncode}")
    for name, source in (("gnome.log", "gnome.log"), ("capture.log", "capture.log"),
                         ("seat.log", "weston/tmp/seat.log"), ("weston.log", "weston/tmp/weston.log"),
                         ("pipewire.log", "gnome/run/lemon/pipewire.log"),
                         ("shell.log", "gnome/run/lemon/gnome.log"), ("rdp.log", "gnome/run/lemon/rdp.log"),
                         ("input.log", "gnome/run/lemon/input.log"),
                         ("client.log", "client.log"),
                         ("system-bus.log", "system-bus.log")):
        (log / name).write_bytes(remote(f'if [ -r "$b/{source}" ]; then cat "$b/{source}"; fi'))
    listing = remote(r'''for f in "$b/weston/tmp"/wayland-screenshot-*.png; do
        if [ -f "$f" ]; then basename "$f"; fi
        done''')
    for name in listing.decode().splitlines():
        if re.fullmatch(r"wayland-screenshot-[a-zA-Z0-9_.-]+\.png", name):
            (log / name).write_bytes(remote(f'cat "$b/weston/tmp/{name}"'))
    (log / "after.txt").write_bytes(remote(SNAPSHOT))

def reset():
    remote(r'''test "$(cat /sys/class/tty/tty0/active)" = tty1
        if grep -F " $b/" /proc/self/mountinfo; then exit 3; fi
        for p in /proc/[0-9]*; do
            case "$(readlink "$p/root" 2>/dev/null || :)" in "$b"/*) exit 4;; esac
            case "$(readlink "$p/exe" 2>/dev/null || :)" in "$b"/*) exit 4;; esac
        done
        for root in "$b/gnome" "$b/weston"; do
            for name in dev proc sys run tmp; do
                test ! -L "$root/$name"
                rm -rf -- "$root/$name"
                mkdir -m 755 "$root/$name"
            done
        done
        rm -f "$b/watchdog.pid"''')
    for source, name in ((RUNNER, "run.sh"), (RUNNER.with_name("physical-input.js"), "physical-input.js")):
        remote(f'cat >"$b/{name}"; chmod 700 "$b/{name}"',
               data=source.read_bytes().replace(b"\r\n", b"\n"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("stage", "run", "stop", "reset", "clean"))
    parser.add_argument("--limit", type=int, choices=(30, 60), default=30)
    args = parser.parse_args()
    if args.action == "stage":
        stage()
    elif args.action == "run":
        run(args.limit)
    elif args.action == "stop":
        stop()
    elif args.action == "reset":
        reset()
    else:
        stop()
        print(remote(r"""test "$(cat /sys/class/tty/tty0/active)" = tty1
            if grep -F " $b/" /proc/self/mountinfo; then exit 3; fi
            rm -rf -- "$b"; test ! -e "$b"; echo RAM_CLEANUP_OK""").decode())
