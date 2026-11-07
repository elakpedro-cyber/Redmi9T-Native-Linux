"""Package the offline-validated v2 overlay and immutable ARM64 roots; no device access."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).parent
OUT = ROOT / "artifacts/gnome-physical-v2"
LOG = ROOT / "logs/gnome-physical-v2"
SNAPSHOT = ROOT / "snapshots/gnome-physical-lcd-v1"


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


manifest = json.loads((SNAPSHOT / "MANIFEST.json").read_text())
for item in manifest:
    file = SNAPSHOT / item["path"]
    if file.stat().st_size != item["bytes"] or sha(file) != item["sha256"]:
        raise RuntimeError(f"v1 checkpoint changed: {item['path']}")
write(LOG / "checkpoint-verification.json", {"files_verified": len(manifest),
    "bytes": sum(item["bytes"] for item in manifest), "mismatches": 0})
vm = (LOG / "vt-v8b-vm.txt").read_text()
assert "ALL_VT_TESTS_PASS" in vm and "ALL_WATCHDOG_TESTS_PASS" in vm
assert "TRACE_AARCH64_VARIADIC_ABI_PASS" in (LOG / "trace-abi.txt").read_text()
for mode in ("C-session", "C-release", "B-headless-final"):
    assert "OFFLINE_NAMESPACE_CLEANUP_PASS" in (LOG / f"offline-{mode}/result.txt").read_text()
session = (LOG / "offline-C-session/gnome.log").read_text(errors="replace")
assert "SHELL_COMPONENT_REGISTERED" in session and "GNOME Shell started" in session
assert "failed to register before timeout" not in session
assert "USER_STOP component=pipewire" in (LOG / "offline-C-release/user-session.log").read_text()
assert "Stream has damage" in (LOG / "offline-B-headless-final/gnome.log").read_text()
modes = {
    "C": {"status": "offline-pass", "hardware_v2": "not tested", "reason": "v1 fallback retained"},
    "B": {"status": "offline-pass", "hardware_v2": "not tested", "reason": "Devkit/PipeWire; explicit Cairo presenter, FD610 guard for Shell"},
    "A": {"status": "blocked", "hardware_v2": "not tested", "reason": "Native render-only GPU topology, seat and dedicated renderer guard not implemented"}}
write(OUT / "modes.json", modes)
payload = {name: SRC / name for name in ("session.sh", "user-session.sh", "devkit-session.sh", "input.js", "session-component.js")}
payload.update({name: OUT / name for name in ("watchdog", "vt-cleanup", "frame-trace.so", "dbus-trace.so")})
payload["probe"] = OUT / "drm-probe"
write(OUT / "payload.json", {name: sha(path) for name, path in payload.items()})
roots = {}
root_files = {}
for name in ("gnome", "weston"):
    relative = f"logs/v8b-physical-gnome/{name}-root.tar.gz"
    item = next(entry for entry in manifest if entry["path"] == relative)
    roots[name] = {"bytes": item["bytes"], "sha256": item["sha256"]}
    path = SNAPSHOT / relative
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            entry = member.name.lstrip("./")
            if entry.startswith(("run/lemon/", "root/.ssh/")) or entry.endswith(("rdp-test.key", "client-credential")):
                raise RuntimeError(f"Unexpected runtime secret path in frozen root: {entry}")
    root_files[f"artifacts/gnome-physical-v2/roots/{name}-root.tar.gz"] = path
write(OUT / "root-manifest.json", roots)
files = {}
for folder in (SRC, LOG):
    for path in folder.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".gz", ".cpio"):
            files[path.relative_to(ROOT).as_posix()] = path
for name in ("watchdog", "vt-cleanup", "drm-probe", "frame-trace.so", "dbus-trace.so", "modes.json", "payload.json", "root-manifest.json"):
    path = OUT / name
    files[path.relative_to(ROOT).as_posix()] = path
for relative in ("scripts/Start-GNOME-Physical.ps1", "scripts/Stop-GNOME-Physical.ps1",
                 "GNOME_PHYSICAL_LCD_V2.md", "GNOME_PHYSICAL_V2_VALIDATION.md", "GNOME_PHYSICAL_V2_TOUCH_AND_KMS.md"):
    files[relative] = ROOT / relative
files.update(root_files)
bundle_manifest = [{"path": name, "bytes": path.stat().st_size, "sha256": sha(path)}
                   for name, path in sorted(files.items())]
write(OUT / "BUNDLE_MANIFEST.json", bundle_manifest)
files["artifacts/gnome-physical-v2/BUNDLE_MANIFEST.json"] = OUT / "BUNDLE_MANIFEST.json"
bundle = ROOT / "artifacts/lemon-gnome-physical-lcd-v2-aarch64.tar.gz"
with tarfile.open(bundle, "w:gz", compresslevel=1) as archive:
    for name, path in sorted(files.items()):
        info = tarfile.TarInfo(name)
        info.size = path.stat().st_size
        info.mode = 0o755 if name.endswith(".sh") or path.name in ("watchdog", "vt-cleanup", "drm-probe") else 0o644
        with path.open("rb") as file:
            archive.addfile(info, file)
expected = {entry["path"]: entry for entry in bundle_manifest}
verified = 0
with tarfile.open(bundle, "r:gz") as archive:
    for member in archive:
        if member.name.endswith("BUNDLE_MANIFEST.json"):
            continue
        item = expected[member.name]
        assert member.size == item["bytes"]
        assert hashlib.file_digest(archive.extractfile(member), "sha256").hexdigest() == item["sha256"]
        verified += 1
assert verified == len(expected)
result = {"path": str(bundle), "bytes": bundle.stat().st_size, "sha256": sha(bundle),
          "members_verified": verified, "v1_files_verified": len(manifest)}
write(OUT / "release.json", result)
print(json.dumps(result, indent=2))
