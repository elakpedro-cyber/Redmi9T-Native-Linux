"""Package the offline-validated v2 overlay and immutable ARM64 roots; no device access."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).parent
OUT = ROOT / "artifacts/gnome-physical-v2.1"
LOG = ROOT / "logs/gnome-physical-v2.1"
SNAPSHOT = ROOT / "snapshots/gnome-physical-lcd-v1"


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


manifest = json.loads((SNAPSHOT / "MANIFEST.json").read_text())
checks = []
for checkpoint in (SNAPSHOT, ROOT / "snapshots/gnome-physical-lcd-v2"):
    entries = json.loads((checkpoint / "MANIFEST.json").read_text())
    for item in entries:
        path = checkpoint / item["path"]
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], item["path"]
    checks.append({"checkpoint": str(checkpoint), "files": len(entries), "mismatches": 0})
write(LOG / "checkpoint-verification.json", checks)
vm = (LOG / "vt-v8b-vm.txt").read_text()
assert "ALL_VT_TESTS_PASS" in vm and "ALL_WATCHDOG_TESTS_PASS" in vm
assert "VT_VM_RESULT=0" in vm and "WATCHDOG_VM_RESULT=0" in vm
assert "TRACE_AARCH64_VARIADIC_ABI_PASS" in (LOG / "trace-abi.txt").read_text()
for tag in ("final-term", "final-int", "release-deadline", "release-term"):
    result = (LOG / f"offline-{tag}/result.txt").read_text()
    assert "OFFLINE_EXIT=0" in result and "OFFLINE_NAMESPACE_CLEANUP_PASS" in result
    shell = (LOG / f"offline-{tag}/gnome.log").read_text(errors="replace")
    rdp = (LOG / f"offline-{tag}/rdp.log").read_text(errors="replace")
    assert "GNOME Shell started" in shell
    assert not any(t in shell for t in ("failed to reply before timeout", "already disposed", "CRITICAL", 'value "inf"'))
    assert "g_close(fd:0)" not in rdp and "BIO_new failed" not in rdp
assert "OFFLINE_EXIT=1" in (LOG / "offline-partial-start/result.txt").read_text()
assert "OFFLINE_NAMESPACE_CLEANUP_PASS" in (LOG / "offline-partial-start/result.txt").read_text()
assert "OFFLINE_EXIT=1" in (LOG / "offline-partial-rdp/result.txt").read_text()
assert "USER_COMPONENT_EXIT component=rdp" in (LOG / "offline-partial-rdp/user-session.log").read_text()
assert "GRD_EGL_FAILURE_OLD_BUG_REPRODUCED_FIXED_STDIN_PRESERVED" in (LOG / "grd-egl-negative.txt").read_text()
assert "SCOPE_FD_NAMESPACE_REPEAT_PASS" in (LOG / "scope-tests.txt").read_text()
assert "CONTROLLER_FAILURE_POSTFLIGHT_UFS_NO_DELETE_PASS" in (LOG / "controller-tests.txt").read_text()
assert "CONTROLLER_SUCCESS_COLLECT_BEFORE_RAM_DELETE_PASS" in (LOG / "controller-tests.txt").read_text()
assert "SIMULTANEOUS_COHORT_NO_SUM_OF_PEAKS_PASS" in (LOG / "accounting-test.txt").read_text()
assert "TOUCH_MULTICONTACT_CANCEL_RELEASE_PASS" in (LOG / "touch-tests.txt").read_text()
assert "POWERSHELL_PARSE_PASS" in (LOG / "windows-parse.txt").read_text()
modes = {
    "C": {"status": "offline-pass", "hardware_v21": "not tested", "reason": "v2 display route retained; lifecycle and GRD fixes validated in ARM64 QEMU"},
    "B": {"status": "blocked", "hardware_v21": "not tested", "reason": "Use C; new v2.1 lifecycle has not been validated with Devkit, retained v2 is available separately"},
    "A": {"status": "blocked", "hardware_v21": "not tested", "reason": "Native render-only topology/seat/renderer guard not implemented"}}
write(OUT / "modes.json", modes)
from control import payload_paths
payload = payload_paths()
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
    root_files[f"artifacts/gnome-physical-v2.1/roots/{name}-root.tar.gz"] = path
write(OUT / "root-manifest.json", roots)
files = {}
for folder in (SRC, LOG):
    for path in folder.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".gz", ".cpio"):
            files[path.relative_to(ROOT).as_posix()] = path
for name in ("watchdog", "vt-cleanup", "drm-probe", "frame-trace.so", "dbus-trace.so", "rdp-copy-trace.so", "gnome-remote-desktop-daemon", "modes.json", "payload.json", "root-manifest.json"):
    path = OUT / name
    files[path.relative_to(ROOT).as_posix()] = path
for relative in ("scripts/Start-GNOME-Physical.ps1", "scripts/Stop-GNOME-Physical.ps1",
                 "GNOME_PHYSICAL_LCD_V21.md", "GNOME_PHYSICAL_V21_VALIDATION.md", "GNOME_PHYSICAL_V21_WARNINGS.md",
                 "GNOME_PHYSICAL_V21_MEMORY_PERFORMANCE.md", "GNOME_PHYSICAL_V21_TOUCH.md",
                 "PROJECT_CHECKPOINT.md", "RESUME_INSTRUCTIONS.md"):
    files[relative] = ROOT / relative
source_tar = ROOT / "downloads/gnome-physical-v2.1/gnome-remote-desktop-50.1.tar.xz"
files[source_tar.relative_to(ROOT).as_posix()] = source_tar
files.update(root_files)
bundle_manifest = [{"path": name, "bytes": path.stat().st_size, "sha256": sha(path)}
                   for name, path in sorted(files.items())]
write(OUT / "BUNDLE_MANIFEST.json", bundle_manifest)
files["artifacts/gnome-physical-v2.1/BUNDLE_MANIFEST.json"] = OUT / "BUNDLE_MANIFEST.json"
bundle = ROOT / "artifacts/lemon-gnome-physical-lcd-v2.1-aarch64.tar.gz"
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
