"""Windows controller for a bounded RAM-only GNOME Physical LCD session."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).parent
OUT = ROOT / "artifacts/gnome-physical-v2.1"
LOG = ROOT / "logs/gnome-physical-v2.1"
STATE = LOG / "current.json"
CHECKPOINT = ROOT / "snapshots/gnome-physical-lcd-v1"
PREFLIGHT = r"""
set -ex
test "$(uname -r)" = 7.4.0-rc1-lemon-bringup-v8b
test "$(cat /sys/class/tty/tty0/active)" = tty1
test "$(basename "$(readlink /sys/class/drm/card0/device/driver)")" = simple-framebuffer
test "$(cat /sys/class/drm/card0-Unknown-1/modes)" = 1080x2340
test "$(cat /sys/class/drm/renderD128/dev)" = 226:128
test "$(basename "$(readlink /sys/class/drm/renderD128/device/driver)")" = adreno
test "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = 1
test "$(cat /sys/bus/platform/devices/5e00000.display-subsystem/driver_override)" = lemon-stage-b-hold
test ! -L /sys/bus/platform/devices/5e00000.display-subsystem/driver
test ! -L /sys/bus/platform/devices/5f00000.clock-controller/driver
test -z "$(ls -A /sys/bus/mipi-dsi/devices)"
test ! -d /sys/class/backlight
test "$(stat -f -c %T /tmp)" = tmpfs
test "$(wc -l </proc/swaps)" -eq 1
awk '/^MemAvailable:/ {exit !($2 >= 1048576)}' /proc/meminfo
awk '$3 !~ /^(rootfs|tmpfs|devtmpfs|proc|sysfs|devpts|configfs|pstore|cgroup|cgroup2)$/ {bad=1} END {exit bad}' /proc/mounts
if pidof weston gnome-shell gnome-remote-desktop-daemon; then exit 9; fi
cat /proc/sys/kernel/random/boot_id
"""
SAMPLE = r"""
printf 'UPTIME '; cat /proc/uptime
grep MemAvailable /proc/meminfo
for device in /sys/block/sd?; do printf '%s ' "${device##*/}"; cat "$device/stat"; done
cat /sys/class/tty/tty0/active
printf 'SWAPS_ROWS '; wc -l </proc/swaps
cat /proc/mounts
cat /sys/bus/platform/devices/5900000.gpu/power/runtime_status
printf 'RUN_PERMISSIONS '; stat -c '%u:%g:%a' /run
printf 'MDSS_OVERRIDE '; cat /sys/bus/platform/devices/5e00000.display-subsystem/driver_override
if [ "$(cat /sys/bus/platform/devices/5e00000.display-subsystem/driver_override)" = lemon-stage-b-hold ] &&
   [ ! -L /sys/bus/platform/devices/5e00000.display-subsystem/driver ] &&
   [ ! -L /sys/bus/platform/devices/5f00000.clock-controller/driver ] &&
   [ -z "$(ls -A /sys/bus/mipi-dsi/devices)" ] && [ ! -d /sys/class/backlight ]; then
    echo DISPLAY_ISOLATED_1
else
    echo DISPLAY_ISOLATED_0
fi
for zone in /sys/class/thermal/thermal_zone*/temp; do
    [ ! -r "$zone" ] || { printf 'TEMP '; cat "$zone"; }
done
dmesg | grep -Ei '((gpu|adreno|iommu|smmu|msm).*(\bfault\b|\bhang\b|timeout|recover))' || :
for process in /proc/[0-9]*; do
    case "$(readlink "$process/root" 2>/dev/null || :)" in "$b"/*)
        echo "PROCESS ${process##*/}"
        cat "$process/comm" "$process/stat" 2>/dev/null || :
        grep '^NSpid:' "$process/status" 2>/dev/null || :
        grep -E '^(Rss|Pss|Pss_Anon|Pss_File|Pss_Shmem|Private_Clean|Private_Dirty|Swap):' "$process/smaps_rollup" 2>/dev/null || :
        ;;
    esac
done
"""


def payload_paths():
    files = {name: SRC / name for name in ("session.sh", "user-session.sh", "devkit-session.sh", "input.js", "configure-rdp.js", "start-rdp.sh", "scope-check.sh")}
    files.update({path.relative_to(SRC).as_posix(): path for path in (SRC / "shell-ui").rglob("*.js")})
    files.update({name: OUT / name for name in ("watchdog", "vt-cleanup", "frame-trace.so", "dbus-trace.so", "rdp-copy-trace.so", "gnome-remote-desktop-daemon")})
    files["probe"] = OUT / "drm-probe"
    return files


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


class Session:
    def __init__(self, args):
        self.args = args
        identity = json.loads((ROOT / "logs/v6-authorized/test-client-identity.json").read_text())["private_key_path"]
        pin = Path(args.known_hosts).resolve()
        if not pin.is_file():
            raise RuntimeError("Missing COM-verified known_hosts file")
        self.ssh = ["ssh.exe", "-T", "-i", identity, "-oBatchMode=yes", "-oIdentitiesOnly=yes",
                    "-oBindAddress=192.168.77.1", "-oConnectTimeout=5", "-oServerAliveInterval=3",
                    "-oServerAliveCountMax=2", "-oKexAlgorithms=curve25519-sha256",
                    "-oStrictHostKeyChecking=yes", f"-oUserKnownHostsFile={pin}", "root@192.168.77.2"]
        self.state = json.loads(STATE.read_text()) if STATE.exists() else {}
        self.base = self.state.get("base", "")
        if self.base and not re.fullmatch(r"/tmp/lemon-gnome-v21\.[A-Za-z0-9]{6}", self.base):
            raise RuntimeError("Invalid RAM directory in session state")
        self.log = None

    def remote(self, command, *, data=None, file=None, timeout=12):
        result = subprocess.run(self.ssh + [f"b={shlex.quote(self.base)}; set -eu; {command}"],
                                input=data, stdin=file, capture_output=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace") +
                               f"\nRemote operation exited {result.returncode}")
        return result.stdout

    def preflight(self):
        info = json.loads((OUT / "modes.json").read_text())[self.args.mode]
        if info["status"] != "offline-pass":
            raise RuntimeError(f"Mode {self.args.mode} blocked: {info['reason']}")
        for name, checksum in json.loads((OUT / "payload.json").read_text()).items():
            path = payload_paths()[name]
            if digest(path) != checksum:
                raise RuntimeError(f"Payload checksum mismatch: {name}")
        for name, item in json.loads((OUT / "root-manifest.json").read_text()).items():
            path = OUT / "roots" / f"{name}-root.tar.gz"
            if not path.is_file():
                path = CHECKPOINT / f"logs/v8b-physical-gnome/{name}-root.tar.gz"
            if digest(path) != item["sha256"]:
                raise RuntimeError(f"Root archive checksum mismatch: {name}")
        print("ROOTS_AND_PAYLOAD_SHA256_OK")
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.CreateFileW(r"\\.\COM4", 0xC0000000, 0, None, 3, 0, None)
        if handle == ctypes.c_void_p(-1).value:
            raise RuntimeError("COM4 unavailable or occupied; no terminal is closed automatically") from ctypes.WinError()
        if not kernel.CloseHandle(handle):
            raise ctypes.WinError()
        print("COM4_EXCLUSIVE_OPEN_OK no commands sent")
        boot = self.remote(PREFLIGHT).decode().strip()
        if not re.fullmatch(r"[a-f0-9-]{36}", boot):
            raise RuntimeError("Unexpected boot ID output")
        print(f"PREFLIGHT_OK mode={self.args.mode} boot={boot}")
        return boot

    def no_owners(self):
        if self.base and self.state.get("boot"):
            boot = self.remote('cat /proc/sys/kernel/random/boot_id').decode().strip()
            if boot != self.state["boot"]:
                raise RuntimeError("Previous boot: recorded RAM path must not be changed")
        self.remote(r"""
            test "$(cat /sys/class/tty/tty0/active)" = tty1
            if [ -d "$b" ]; then
                if [ -f "$b/scope-check.sh" ]; then /bin/sh "$b/scope-check.sh" "$b";
                else
                    test ! -e "$b/namespaces"
                    if grep -F " $b/" /proc/self/mountinfo; then exit 3; fi
                    for p in /proc/[0-9]*; do
                        case "$(readlink "$p/root" 2>/dev/null || :)" in "$b"/*) exit 4;; esac
                        case "$(readlink "$p/exe" 2>/dev/null || :)" in "$b"/*) exit 4;; esac
                    done
                fi
            fi
            """)

    def prepare(self, boot):
        roots_manifest = OUT / "root-manifest.json"
        root_identity = digest(roots_manifest)
        roots = json.loads(roots_manifest.read_text())
        reusable = self.base and self.state.get("boot") == boot
        if reusable and self.remote(f'if [ "$(cat "$b/roots-ready" 2>/dev/null || :)" = "{root_identity}" ]; then echo yes; fi').strip() == b"yes":
            self.no_owners()
        else:
            if reusable:
                self.no_owners()
                self.remote('rm -rf -- "$b"; test ! -e "$b"')
            self.base = self.remote(r"""awk '/^MemAvailable:/ {exit !($2 >= 2800000)}' /proc/meminfo
                umask 077; mktemp -d /tmp/lemon-gnome-v21.XXXXXX""").decode().strip()
            if not re.fullmatch(r"/tmp/lemon-gnome-v21\.[A-Za-z0-9]{6}", self.base):
                raise RuntimeError("Unexpected staging path")
            self.state = {"base": self.base, "boot": boot}
            STATE.write_text(json.dumps(self.state, indent=2))
            for name in ("gnome", "weston"):
                relative = f"logs/v8b-physical-gnome/{name}-root.tar.gz"
                archive = OUT / "roots" / f"{name}-root.tar.gz"
                if not archive.is_file():
                    archive = CHECKPOINT / relative
                checksum = roots[name]["sha256"]
                if digest(archive) != checksum:
                    raise RuntimeError(f"v1 archive checksum mismatch: {name}")
                with archive.open("rb") as file:
                    self.remote(f"""cat >"$b/{name}.tar.gz"
                        echo '{checksum}' " $b/{name}.tar.gz" | sha256sum -c
                        mkdir -m 755 "$b/{name}"
                        tar -xzf "$b/{name}.tar.gz" -C "$b/{name}"
                        rm "$b/{name}.tar.gz" """, file=file, timeout=240)
            self.remote(f'printf "%s\\n" "{root_identity}" >"$b/roots-ready"')
        self.no_owners()
        self.remote(r"""
            for root in "$b/gnome" "$b/weston"; do
                for name in dev proc sys run tmp; do
                    test ! -L "$root/$name"
                    rm -rf -- "$root/$name"; mkdir -m 755 "$root/$name"
                done
            done
            rm -f "$b/watchdog.pid" "$b/watchdog.start"
            """)
        payload = payload_paths()
        build = json.loads((OUT / "payload.json").read_text())
        for name, path in payload.items():
            if digest(path) != build[name]:
                raise RuntimeError(f"Unvalidated v2.1 payload: {name}")
            self.remote(f'mkdir -p "$b/{Path(name).parent.as_posix()}"; cat >"$b/{name}"; chmod 700 "$b/{name}"', data=path.read_bytes())
        print(f"RAM_READY {self.base}")

    def stop(self):
        if not self.base:
            print("No recorded session")
            return
        boot = self.remote('cat /proc/sys/kernel/random/boot_id').decode().strip()
        if boot != self.state.get("boot"):
            print("Previous boot: no process is signalled")
            return
        self.remote(r"""
            test -f "$b/watchdog.pid" || exit 0
            p=$(cat "$b/watchdog.pid")
            case "$p" in ''|*[!0-9]*) exit 3;; esac
            if [ "$(readlink "/proc/$p/exe" 2>/dev/null || :)" = "$b/watchdog" ] &&
               [ "$(awk '{print $22}' "/proc/$p/stat")" = "$(cat "$b/watchdog.start")" ]; then
                kill -TERM "$p"
            fi""")
        print("STOP_REQUESTED")
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            try:
                self.no_owners()
                print("STOPPED_TTY1_RESTORED")
                return
            except RuntimeError:
                time.sleep(.2)
        raise RuntimeError("Stop did not finish safely; RAM tree retained")

    def collect(self):
        files = {"gnome.log": "gnome.log", "client.log": "client.log",
                 "shell.log": "gnome/run/lemon/gnome.log", "input.log": "gnome/run/lemon/input.log",
                 "rdp.log": "gnome/run/lemon/rdp.log", "weston.log": "weston/tmp/weston.log",
                 "seat.log": "weston/tmp/seat.log", "gnome-frames.jsonl": "gnome/run/lemon/gnome-frames.jsonl",
                 "rdp-frames.jsonl": "weston/tmp/rdp-frames.jsonl",
                 "pipewire.log": "gnome/run/lemon/pipewire.log", "wireplumber.log": "gnome/run/lemon/wireplumber.log",
                 "console.log": "gnome/run/lemon/console.log", "system-bus.log": "system-bus.log",
                 "namespaces.txt": "namespaces", "devkit-dbus.log": "gnome/run/lemon/devkit-dbus.log",
                 "weston-timeline.jsonl": "weston/tmp/timeline.jsonl", "rdp-copies.jsonl": "weston/tmp/rdp-copies.jsonl"}
        for name, relative in files.items():
            (self.log / name).write_bytes(self.remote(f'if [ -r "$b/{relative}" ]; then cat "$b/{relative}"; fi'))

    def start(self):
        boot = self.preflight()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        self.log = LOG / stamp
        self.log.mkdir(parents=True)
        (self.log / "run.json").write_text(json.dumps({"scope": "physical Redmi 9T v8b",
            "mode": self.args.mode, "seconds": self.args.seconds,
            "profile": self.args.profile, "test_actions": self.args.test_actions}, indent=2))
        self.prepare(boot)
        baseline = self.remote(SAMPLE)
        (self.log / "before.txt").write_bytes(baseline)
        faults = {line for line in baseline.splitlines() if line.startswith(b"[")}
        viewer = "rdp" if self.args.mode == "C" else "devkit"
        command = (f"exec env LEMON_PHYSICAL_VIEWER={viewer} LEMON_PROFILE={self.args.profile} "
                   f"LEMON_TEST_ACTIONS={int(self.args.test_actions)} LEMON_MEASURE={int(self.args.measure)} "
                   f"/bin/sh {self.base}/session.sh {self.base} {self.args.seconds}")
        self.state["log"] = str(self.log.relative_to(ROOT))
        STATE.write_text(json.dumps(self.state, indent=2))
        failure = None
        try:
            with (self.log / "session.txt").open("wb") as output, (self.log / "samples.txt").open("wb") as samples:
                process = subprocess.Popen(self.ssh + [command], stdin=subprocess.DEVNULL,
                                           stdout=output, stderr=subprocess.STDOUT)
                try:
                    while process.poll() is None:
                        time.sleep(2)
                        current = self.remote(SAMPLE)
                        samples.write(current)
                        samples.flush()
                        if {line for line in current.splitlines() if line.startswith(b"[")} - faults:
                            raise RuntimeError("New GPU/IOMMU fault")
                        if b"DISPLAY_ISOLATED_1" not in current.splitlines():
                            raise RuntimeError("Display isolation changed")
                        memory = re.search(rb"MemAvailable:\s+(\d+)", current)
                        if not memory or int(memory[1]) < 524288:
                            raise RuntimeError("RAM safety threshold")
                        if any(int(t) >= 75000 for t in re.findall(rb"^TEMP (\d+)", current, re.M)):
                            raise RuntimeError("Thermal threshold")
                        renderer = self.remote(r"""if [ -r "$b/gnome/run/lemon/gnome.log" ]; then
                            grep -Ei 'LEMON_FD610|llvmpipe|softpipe|swrast|software fallback refused' "$b/gnome/run/lemon/gnome.log" || :; fi""")
                        if re.search(rb"LEMON_FD610_REJECTED|llvmpipe|softpipe|swrast|software fallback refused", renderer, re.I):
                            raise RuntimeError("Hardware-renderer guard")
                finally:
                    if process.poll() is None:
                        self.stop()
                    process.wait(timeout=15)
                print(f"SESSION_EXIT={process.returncode}")
                if process.returncode not in (0, 124, 143):
                    raise RuntimeError(f"Session/TTY restoration exited {process.returncode}")
        except Exception as error:
            failure = error
            (self.log / "failure.txt").write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
        finally:
            self.collect()
            (self.log / "after.txt").write_bytes(self.remote(SAMPLE))
        self.no_owners()
        after = (self.log / "after.txt").read_bytes()
        if {line for line in after.splitlines() if line.startswith(b"[")} - faults:
            raise RuntimeError("New GPU/IOMMU fault at session exit")
        if b"DISPLAY_ISOLATED_1" not in after.splitlines():
            raise RuntimeError("Display isolation not confirmed at exit")
        def writes(sample):
            disks = {}
            for line in sample.splitlines():
                fields = line.split()
                if fields and re.fullmatch(rb"sd[a-f]", fields[0]):
                    values = [int(value) for value in fields[1:]]
                    disks[fields[0].decode()] = [values[i] for i in (4, 5, 6, 11, 12, 13, 15) if i < len(values)]
            if len(disks) != 6:
                raise RuntimeError("Missing UFS counters")
            return disks
        if writes(baseline) != writes(after):
            raise RuntimeError("UFS write/discard/flush counters changed")
        print("UFS_WRITE_DISCARD_FLUSH_UNCHANGED")
        print(f"TTY_AND_PROCESS_CLEANUP_OK log={self.log}")
        if failure is not None:
            raise failure
        # Logs and all postflight evidence are on the PC before deleting the RAM roots.
        self.remote('rm -rf -- "$b"; test ! -e "$b"')
        self.state["base"] = ""
        STATE.write_text(json.dumps(self.state, indent=2))
        print("SESSION_RAM_ROOTS_REMOVED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preflight", "start", "stop", "status", "clean"))
    parser.add_argument("--mode", choices=("C", "B", "A"), default="C")
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--profile", choices=("baseline", "quiet"), default="baseline")
    parser.add_argument("--test-actions", action="store_true")
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--known-hosts", default=str(ROOT / "logs/v8b-physical-gnome/known_hosts"))
    args = parser.parse_args()
    if not 10 <= args.seconds <= 3600:
        parser.error("seconds must be 10..3600")
    LOG.mkdir(parents=True, exist_ok=True)
    session = Session(args)
    if args.action == "preflight":
        session.preflight()
    elif args.action == "start":
        import msvcrt
        with (LOG / "start.lock").open("a+b") as lock:
            lock.write(b"0")
            lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError("Another Physical LCD start is running") from error
            session.start()
    elif args.action == "stop":
        session.stop()
    elif args.action == "status":
        print(session.remote('cat /sys/class/tty/tty0/active; cat /proc/uptime; ip -4 addr show usb0').decode())
    else:
        session.no_owners()
        if session.base:
            session.remote('rm -rf -- "$b"; test ! -e "$b"')
        print("RAM_CLEANUP_OK")


if __name__ == "__main__":
    main()
