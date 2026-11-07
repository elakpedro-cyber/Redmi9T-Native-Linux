import json
import subprocess
import sys
from pathlib import Path

bridge, app = sys.argv[1:]
if app not in {"console", "settings", "files", "editor"}:
    raise SystemExit("invalid desktop probe app")
args = json.loads(Path(bridge).read_text())
args[0] = "/mnt/c/Windows/System32/OpenSSH/ssh.exe"
args[-1] = f"test -d /tmp/lemon-gnome50/root/run/lemon-rdp && touch /tmp/lemon-gnome50/root/run/lemon-rdp/test-{app}"
subprocess.run(args, check=True, timeout=9)
