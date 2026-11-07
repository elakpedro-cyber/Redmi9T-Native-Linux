import os
from pathlib import Path
import subprocess
import tempfile
import time

src = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="lemon-scope-", dir="/tmp") as directory:
    base = Path(directory)
    def check(expected):
        result = subprocess.run(["sh", str(src/"scope-check.sh"), directory], capture_output=True, text=True)
        print(result.stdout.strip())
        assert (result.returncode == 0) == expected, result.stderr
    check(True)
    fd = os.open(base/"held-file", os.O_CREAT | os.O_RDWR, 0o600)
    check(False)
    os.close(fd)
    check(True)
    subprocess.run(["gcc", "-O2", str(src/"watchdog.c"), "-o", str(base/"watchdog")], check=True)
    child = base/"child.sh"
    child.write_text('readlink /proc/self/ns/mnt >"$1/namespaces"; readlink /proc/self/ns/pid >>"$1/namespaces"; readlink /proc/self/ns/net >>"$1/namespaces"; trap "exit 0" TERM; while :; do sleep 1; done')
    watch = subprocess.Popen([str(base/"watchdog"), "10", "sh", str(child), directory])
    try:
        for _ in range(100):
            if (base/"namespaces").exists() and len((base/"namespaces").read_text().splitlines()) == 3:
                break
            time.sleep(.05)
        target = (base/"namespaces").read_text().splitlines()[0]
        holder = next(p for p in Path("/proc").glob("[0-9]*/ns/mnt") if os.readlink(p) == target)
        fd = os.open(holder, os.O_RDONLY)
        watch.terminate()
        assert watch.wait(timeout=8) == 0
        check(False)
        os.close(fd)
        check(True)
        check(True)
    finally:
        if watch.poll() is None:
            watch.terminate()
            watch.wait(timeout=8)
print("SCOPE_FD_NAMESPACE_REPEAT_PASS")
