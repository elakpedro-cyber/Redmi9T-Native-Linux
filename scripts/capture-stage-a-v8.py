from pathlib import Path
import argparse
import json
import subprocess

from fdt_audit import Fdt

parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=("before-gpu", "after-gpu"))
phase = parser.parse_args().phase
root = Path(__file__).resolve().parents[1]
log = root / "logs/v8-authorized"
key = json.loads((root / "logs/v6-authorized/test-client-identity.json").read_text())["private_key_path"]
ssh = [
    "ssh.exe", "-i", key, "-oBatchMode=yes", "-oIdentitiesOnly=yes",
    "-oConnectTimeout=8", "-oKexAlgorithms=curve25519-sha256",
    "-oStrictHostKeyChecking=yes", f"-oUserKnownHostsFile={log / 'v8-known_hosts'}",
    "root@192.168.77.2",
]

def capture(name, command, payload=None):
    result = subprocess.run(ssh + [command], input=payload, capture_output=True, timeout=20)
    (log / f"{phase}-{name}.stderr").write_bytes(result.stderr)
    path = log / f"{phase}-{name}"
    path.write_bytes(result.stdout)
    result.check_returncode()
    return path

inventory = (root / "scripts/display-inventory-v8.sh").read_text().encode()
path = capture("inventory.txt", "sh -s", inventory)
assert b"LEMON_INIT_V8_REACHED" in path.read_bytes()
assert b"LEMON_OPENRC_V8_REACHED" in path.read_bytes()
capture("dmesg.txt", "dmesg")
tree = Fdt(capture("live.dtb", "cat /sys/firmware/fdt"))
display_compatibles = (
    b"sm6115-mdss", b"sm6115-dpu", b"sm6115-dsi", b"dsi-phy-14nm",
    b"sm6115-dispcc", b"lm36923", b"led-backlight",
)
gates = {}
for name, properties in tree.nodes.items():
    compatible = properties.get("compatible", b"")
    if any(value in compatible for value in display_compatibles):
        assert properties.get("status") == b"disabled\0", name
        gates[name] = "disabled"
    assert not any(value in compatible for value in (b"novatek,", b"td4330", b"lcdb")), name
assert len(gates) == 7
platform = capture("platform.txt", "ls /sys/bus/platform/devices; ls /sys/class/drm; cat /proc/fb")
for address in ("5e00000", "5e01000", "5e94000", "5e94400", "5f00000"):
    assert not any(line.startswith(address + ".") for line in platform.read_text().splitlines()), address
assert "simple" in platform.read_text().lower()

mounts = capture("mounts.txt", "cat /proc/mounts").read_text().splitlines()
allowed = {"rootfs", "tmpfs", "devtmpfs", "proc", "sysfs", "devpts", "configfs", "pstore", "cgroup", "cgroup2"}
assert all(line.split()[2] in allowed for line in mounts)
assert len(capture("swaps.txt", "cat /proc/swaps").read_text().splitlines()) == 1
stats = {}
for disk in ("sda", "sdb", "sdc", "sdd", "sde", "sdf"):
    disk_path = f"/sys/block/{disk}"
    lines = capture(f"{disk}.txt", f"test -b /dev/{disk} && cat {disk_path}/stat {disk_path}/device/ioerr_cnt").read_text().splitlines()
    values = [int(field) for field in lines[0].split()]
    assert all(values[index] == 0 for index in (4, 6, 11, 13, 15)), disk
    stats[disk] = {"writes": values[4], "discards": values[11], "flushes": values[15], "ioerr": int(lines[1], 0)}
if phase == "after-gpu":
    before = json.loads((log / "before-gpu-gates.json").read_text())
    assert before["ufs"] == stats, "UFS counters changed"
(log / f"{phase}-gates.json").write_text(json.dumps({"display": gates, "ufs": stats}, indent=2) + "\n")
print("PASS", phase, "seven disabled display nodes, no display platform bindings, six UFS LUNs and virtual mounts")
