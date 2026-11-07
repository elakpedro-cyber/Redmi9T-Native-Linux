"""Local browser viewer. All phone commands use an existing pinned SSH host key."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
from pathlib import Path
import re
import secrets
import subprocess
import time
import webbrowser

REMOTE = "/tmp/lemon-desktop-v8b/runtime/desktop.sh"
PAGE = r"""<!doctype html><meta charset="utf-8"><title>Lemon Desktop</title>
<style>
body{margin:0;background:#101a2b;color:#eef6ff;font:16px system-ui;text-align:center}
header{padding:14px;background:#243d5a} button,label{margin:4px;padding:6px}
img{display:block;max-width:96vw;max-height:80vh;aspect-ratio:9/20;margin:12px auto;background:#192942;cursor:crosshair}
#status{min-height:1.5em} button{cursor:pointer}
</style>
<header><strong>Lemon Desktop</strong> <button id="capture">Capture</button>
<label><input id="auto" type="checkbox">1 fps</label>
<label><input id="motion" type="checkbox">Forward pointer</label></header>
<img id="screen" alt="Captured Weston output" tabindex="0" draggable="false">
<div id="status" role="status">Waiting for a frame. Focus the frame to type.</div>
<script>
const token = location.hash.slice(1) || sessionStorage.getItem("lemon-token") || "";
if (location.hash) sessionStorage.setItem("lemon-token", token);
history.replaceState(null, "", location.pathname);
const $ = id => document.getElementById(id);
const image = $("screen"), status = $("status");
let current, capturing = false, pending = false, lastMove = 0;
const headers = {"X-Lemon-Token":token};
async function frame() {
  if(capturing) return;
  capturing = true;
  try {
    const r = await fetch("/frame",{headers,cache:"no-store"});
    if(!r.ok) throw new Error(await r.text());
    const next = URL.createObjectURL(await r.blob());
    image.src = next;
    if(current) URL.revokeObjectURL(current);
    current = next;
    status.textContent = "Weston capture received - " + new Date().toLocaleTimeString();
  } catch(e) { status.textContent = e.message; }
  finally { capturing = false; }
}
async function send(value, redraw=false) {
  if(pending) return;
  pending = true;
  try {
    const r = await fetch("/input",{method:"POST",headers,body:value});
    if(!r.ok) throw new Error(await r.text());
    if(redraw) setTimeout(frame,1100);
  } catch(e) { status.textContent = e.message; }
  finally { pending = false; }
}
function point(e) {
  const b = image.getBoundingClientRect();
  return [Math.max(0,Math.min(359,Math.floor((e.clientX-b.left)*360/b.width))),
          Math.max(0,Math.min(799,Math.floor((e.clientY-b.top)*800/b.height)))].join(" ");
}
$("capture").onclick = frame;
image.onclick = e => { if(!current)return; image.focus(); send("click "+point(e),true); };
image.onpointermove = e => {
  if(current && $("motion").checked && Date.now()-lastMove>=350) {
    lastMove=Date.now(); send("move "+point(e));
  }
};
image.onkeydown = e => {
  if(e.ctrlKey||e.altKey||e.metaKey) return;
  if(e.key==="Backspace"||/^[ -~]$/.test(e.key)) {
    e.preventDefault(); send(e.key==="Backspace"?"backspace":"key "+e.key,true);
  }
};
setInterval(() => { if($("auto").checked) frame(); },1000);
frame();
</script>"""

def valid_input(data):
    if data == b"backspace" or re.fullmatch(rb"key [ -~]", data):
        return True
    point = re.fullmatch(rb"(?:move|click) (\d{1,3}) (\d{1,3})", data)
    return bool(point and int(point[1]) < 360 and int(point[2]) < 800)


class Viewer(HTTPServer):
    def __init__(self, remote):
        super().__init__(("127.0.0.1", 0), Handler)
        self.remote = remote
        self.token = secrets.token_urlsafe(32)
        self.frame = None
        self.frame_time = -10
        self.input_time = -10


class Handler(BaseHTTPRequestHandler):
    def send(self, code, data=b"", content_type="text/plain; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; img-src blob:; connect-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def allowed(self):
        host = f"127.0.0.1:{self.server.server_port}"
        return (self.headers.get("Host") == host and
                self.headers.get("Origin", f"http://{host}") == f"http://{host}" and
                hmac.compare_digest(self.headers.get("X-Lemon-Token", "").encode("utf-8"),
                                    self.server.token.encode("ascii")))

    def do_GET(self):
        if self.path == "/":
            self.send(200, PAGE.encode(), "text/html; charset=utf-8")
            return
        if self.path != "/frame" or not self.allowed():
            self.send(403, b"Capture not authorized")
            return
        try:
            now = time.monotonic()
            if self.server.frame is None or now - self.server.frame_time >= 1:
                data = self.server.remote("capture", b"")
                if not 24 <= len(data) <= 2_000_000 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[16:24] != bytes.fromhex("0000016800000320"):
                    raise ValueError("Unexpected Weston capture")
                self.server.frame, self.server.frame_time = data, time.monotonic()
            self.send(200, self.server.frame, "image/png")
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            self.send(502, str(exc).encode())

    def do_POST(self):
        if self.path != "/input" or not self.allowed():
            self.send(403, b"Input not authorized")
            return
        length = self.headers.get("Content-Length", "")
        if not re.fullmatch(r"[0-9]{1,2}", length) or not 1 <= int(length) <= 15:
            self.send(400, b"Invalid input size")
            return
        self.connection.settimeout(2)
        try:
            data = self.rfile.read(int(length))
        except TimeoutError:
            self.send(408, b"Input timed out")
            return
        if not valid_input(data):
            self.send(400, b"Invalid app input")
            return
        now = time.monotonic()
        if now - self.server.input_time < .12:
            self.send(429, b"Input rate limited")
            return
        self.server.input_time = now
        try:
            self.server.remote("input", data + b"\n")
            self.send(204)
        except (OSError, subprocess.SubprocessError) as exc:
            self.send(502, str(exc).encode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--known-hosts", type=Path, required=True)
    args = parser.parse_args()
    if not args.identity.is_file() or not args.known_hosts.is_file():
        parser.error("Identity and the COM-verified known_hosts file are required")

    def remote(action, data):
        cmd = ["ssh.exe", "-b", "192.168.77.1", "-i", str(args.identity),
               "-oBatchMode=yes", "-oIdentitiesOnly=yes", "-oConnectTimeout=4",
               "-oStrictHostKeyChecking=yes", "-oUserKnownHostsFile=" + str(args.known_hosts.resolve()),
               "-oKexAlgorithms=curve25519-sha256", "root@192.168.77.2",
               f"/bin/sh {REMOTE} {action}"]
        result = subprocess.run(cmd, input=data, capture_output=True, timeout=8)
        if result.returncode:
            raise OSError(result.stderr.decode(errors="replace").strip() or f"SSH exit {result.returncode}")
        return result.stdout

    with Viewer(remote) as server:
        url = f"http://127.0.0.1:{server.server_port}/#{server.token}"
        print(url, flush=True)
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
