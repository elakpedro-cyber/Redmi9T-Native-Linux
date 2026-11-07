from pathlib import Path
import hashlib
import json
import re
import subprocess
import time

log = Path("logs/v8b-gnome50-fd610-r2")
base = "/tmp/lemon-gnome50-fd610"
src = Path(__file__).resolve().parent
key = json.loads(Path("logs/v6-authorized/test-client-identity.json").read_text())["private_key_path"]
pin = "logs/v8b-labwc-gpu-restore/known_hosts"
opts = [
    "-i", key, "-oBatchMode=yes", "-oIdentitiesOnly=yes", "-oBindAddress=192.168.77.1",
    "-oConnectTimeout=4", "-oKexAlgorithms=curve25519-sha256",
    "-oStrictHostKeyChecking=yes", "-oUserKnownHostsFile=" + pin,
    "-oServerAliveInterval=2", "-oServerAliveCountMax=2",
]
target = "root@192.168.77.2"
ssh = ["ssh.exe", "-T", *opts, target]

guards = r"""
set -eu
test "$(uname -r)" = 7.4.0-rc1-lemon-bringup-v8b
test -c /dev/dri/renderD128
test "$(cat /sys/class/drm/renderD128/dev)" = 226:128
test "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = 1
p=/sys/bus/platform/devices
test "$(cat "$p/5e00000.display-subsystem/driver_override")" = lemon-stage-b-hold
test ! -L "$p/5e00000.display-subsystem/driver"
test ! -L "$p/5f00000.clock-controller/driver"
test ! -d /sys/module/dispcc_sm6115
test ! -e "$p/5e94000.dsi"; test ! -e "$p/5e94400.phy"
test ! -d /sys/class/backlight
test -z "$(ls -A /sys/bus/mipi-dsi/devices)"
grep -q '^tmpfs /tmp tmpfs ' /proc/mounts
if grep -q '^/dev/' /proc/mounts; then exit 1; fi
test "$(wc -l </proc/swaps)" -eq 1
"""
snapshot = r"""
uname -r
ip -4 addr show usb0
cat /proc/mounts /proc/swaps
grep ' sd[a-f] ' /proc/diskstats
cat /sys/bus/platform/devices/5900000.gpu/power/runtime_status
dmesg
"""
fault = re.compile(r"(gpu|adreno|iommu|smmu|msm).*(\bfault\b|\bhang\b|timed out|recover)|"
                   r"(\bfault\b|\bhang\b).*(gpu|adreno|iommu|smmu|msm)", re.I)


def remote(command, timeout=5):
    return subprocess.check_output([*ssh, command], stderr=subprocess.STDOUT,
                                   timeout=timeout).decode(errors="replace")


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    gate = json.loads((log / "offline-pass.json").read_text())
    archive = Path("artifacts/lemon-gnome50-v8b-fd610-aarch64.tar.gz")
    paths = {
        "root.tar.gz": archive,
        "watchdog": log / "namespace-watchdog-aarch64",
        "run.sh": src / "run-fd610.sh",
        "sample.sh": src / "sample-fd610.sh",
    }
    actual = {name: digest(path) for name, path in paths.items()}
    if actual != gate:
        raise RuntimeError("Offline-validated artifact hashes do not match")

    before = remote(guards + snapshot)
    (log / "hardware-before.txt").write_text(before)
    baseline = set(re.findall(r"^\[.*$", before, re.M))
    remote(guards + f"""
test ! -e {base}; test ! -L {base}
awk '/^MemAvailable:/ {{exit !($2 >= 2097152)}}' /proc/meminfo
df -k /tmp | awk 'END {{exit !($4 >= 1468006)}}'
umask 077; mkdir {base}
""")
    process = None
    try:
        batch = "".join(f'put "{path.as_posix()}" {base}/{name}\n' for name, path in paths.items())
        with (log / "hardware-sftp.txt").open("wb") as out:
            subprocess.run(["sftp.exe", "-b", "-", *opts, target], input=batch.encode(),
                           stdout=out, stderr=subprocess.STDOUT, check=True, timeout=240)
        hashes = "\n".join(f"{value}  {name}" for name, value in actual.items())
        stage = remote(f"set -eu; cd {base}; printf '%s\\n' '{hashes}' | sha256sum -c -; "
                       "mkdir root; tar -xzf root.tar.gz -C root; rm root.tar.gz; chmod 700 watchdog", 120)
        (log / "hardware-stage.txt").write_text(stage)
        remote(guards + "\nawk '/^MemAvailable:/ {exit !($2 >= 1310720)}' /proc/meminfo")
        preflight = subprocess.run(
            [*ssh, f"exec {base}/watchdog 5 /bin/sh {base}/run.sh --mount-check"],
            capture_output=True, timeout=12,
        )
        proof = preflight.stdout + preflight.stderr
        (log / "hardware-mount-preflight.txt").write_bytes(proof)
        if (preflight.returncode != 124 or b"PRIVATE_MOUNTS_OK" not in proof
                or b"WATCHDOG deadline" not in proof):
            raise RuntimeError("Mount namespace preflight or watchdog failed")
        time.sleep(7)
        remote(f"""set -eu
test -f {base}/descendant-started
test ! -e {base}/descendant-escaped
if grep -q ' {base}/' /proc/self/mountinfo; then exit 1; fi
rm {base}/descendant-started
""")
        (log / "hardware-watchdog-proof.txt").write_text(
            "Mounts absent from host namespace; detached descendant did not survive deadline.\n")
        with (log / "hardware-once.journal").open("x") as f:
            f.write("One authorized GNOME launch, 60-second watchdog. No retry.\n")

        started = time.monotonic()
        with (log / "hardware-shell.txt").open("wb") as out, (log / "hardware-samples.txt").open("w") as samples:
            process = subprocess.Popen(
                [*ssh, f"exec env LEMON_WATCHDOG_HEARTBEAT=1 {base}/watchdog 60 /bin/sh {base}/run.sh"],
                stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT,
            )
            verified = False
            mutter_started = False
            shell_started = False
            while process.poll() is None and time.monotonic() - started < 65:
                current = remote(guards + f"/bin/sh {base}/sample.sh; dmesg", 5)
                elapsed = time.monotonic() - started
                samples.write(f"===== {elapsed:.2f}s =====\n{current}")
                samples.flush()
                new = set(re.findall(r"^\[.*$", current, re.M)) - baseline
                if any(fault.search(line) for line in new):
                    raise RuntimeError("New GPU/DRM/IOMMU fault")
                mem = re.search(r"^MemAvailable:\s+(\d+)", current, re.M)
                if not mem or int(mem[1]) < 524288:
                    raise RuntimeError("RAM below 512 MiB or unavailable")
                if any(int(value) >= 75000 for value in re.findall(r"^THERMAL \S+ (\d+)", current, re.M)):
                    raise RuntimeError("Thermal stop at 75 C")
                if re.search(r"^DRM_FD .* /dev/dri/card\d+", current, re.M):
                    raise RuntimeError("Unexpected DRM primary node")
                output = (log / "hardware-shell.txt").read_text(errors="replace")
                if re.search(r"LEMON_FD610_REJECTED|software fallback refused|llvmpipe|softpipe|swrast", output, re.I):
                    raise RuntimeError("Renderer gate failed")
                if not mutter_started and "Running GNOME Shell (using mutter 50.2)" in output:
                    mutter_started = True
                    with (log / "hardware-timing.txt").open("a") as timing:
                        timing.write(f"Mutter start observed by {elapsed:.2f}s\n")
                if not verified and "LEMON_FD610_EGL_VERIFIED node=/dev/dri/renderD128 renderer=FD610" in output:
                    verified = True
                    with (log / "hardware-timing.txt").open("a") as timing:
                        timing.write(f"EGL FD610 verified by {elapsed:.2f}s\n")
                if not verified and elapsed > 15:
                    raise RuntimeError("No FD610 verification within 15 seconds")
                if not shell_started and "GNOME Shell started" in output:
                    shell_started = True
                    (log / "hardware-ready.txt").write_text(f"Shell ready observed at {elapsed:.2f}s from SSH launch\n")
                if process.poll() is None:
                    try:
                        process.stdin.write(b".")
                        process.stdin.flush()
                    except BrokenPipeError:
                        break
                time.sleep(1.5)
            print(f"FD610 verified: {verified}. GNOME Shell ready: {shell_started}.")
            if not verified or not shell_started or process.poll() != 124:
                raise RuntimeError("GNOME Shell did not complete the verified watchdog run")
    finally:
        if process:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
            process.wait(timeout=15)
            print(f"Watchdog exit: {process.returncode}")
        after = remote(snapshot)
        (log / "hardware-after.txt").write_text(after)
        gone = remote(f"""set -eu
if grep -q ' {base}/' /proc/self/mountinfo; then exit 1; fi
for p in /proc/[0-9]*; do
  case "$(readlink "$p/root" 2>/dev/null || :)" in {base}/*) exit 1;; esac
  case "$(readlink "$p/exe" 2>/dev/null || :)" in {base}/*) exit 1;; esac
done
rm -rf {base}
test ! -e {base}
echo RAM_CLEANUP_OK
""")
        (log / "hardware-cleanup.txt").write_text(gone)


if __name__ == "__main__":
    main()
