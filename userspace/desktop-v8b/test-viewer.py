"""Check the local Windows HTTP bridge without connecting to the phone."""
from http.client import HTTPConnection
from pathlib import Path
import threading
import time

from viewer import Viewer

png = Path("logs/v8b-desktop-offline/after-input.png").read_bytes()
calls = []


def remote(action, data):
    calls.append((action, data))
    return png if action == "capture" else b""


with Viewer(remote) as server:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    headers = {"X-Lemon-Token": server.token}

    def request(method, route, expected, body=None, **extra):
        client.request(method, route, body=body, headers=extra)
        response = client.getresponse()
        data = response.read()
        assert response.status == expected, (method, route, response.status, data)
        return data

    try:
        assert b"Lemon Desktop" in request("GET", "/", 200)
        request("GET", "/frame", 403)
        request("GET", "/frame", 403, Origin="http://192.168.0.1", **headers)
        assert request("GET", "/frame", 200, **headers) == png
        assert request("GET", "/frame", 200, **headers) == png
        assert calls == [("capture", b"")]
        request("POST", "/input", 400, b"click 999 0", **headers)
        request("POST", "/input", 400, b"quit", **headers)
        request("POST", "/input", 204, b"click 55 560", **headers)
        request("POST", "/input", 429, b"key A", **headers)
        time.sleep(.15)
        request("POST", "/input", 204, b"key A", **headers)
        assert calls[1:] == [("input", b"click 55 560\n"), ("input", b"key A\n")]
    finally:
        client.close()
        server.shutdown()
        thread.join(timeout=2)

print("PASS: loopback viewer serves verified Weston PNG, caches at 1 fps and validates input and token")
