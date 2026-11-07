"""Offline RFB client for testing actual wayvnc frames and virtual input."""
from pathlib import Path
import runpy
import threading
import socket
import struct
import time
import zlib

log = Path("logs/v8b-labwc-offline").resolve()
root = Path((log / "root.txt").read_text().strip())
relay = runpy.run_path(str(Path(__file__).with_name("vnc-ssh.py")))["relay"]


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


client, peer = socket.socketpair()


def bridge():
    with peer:
        relay(peer, ["chroot", str(root), "/bin/sh", "/tmp/lemon-labwc-v8b/runtime/session.sh", "stream"])


worker = threading.Thread(target=bridge, daemon=True)
worker.start()
with client:
    client.settimeout(10)

    def read(size):
        data = bytearray()
        while len(data) < size:
            part = client.recv(size - len(data))
            if not part:
                raise EOFError("RFB socket closed")
            data.extend(part)
        return bytes(data)

    assert read(12) == b"RFB 003.008\n"
    client.sendall(b"RFB 003.008\n")
    assert 1 in read(read(1)[0]), "Expected None security on private socket"
    client.sendall(b"\x01")
    assert read(4) == b"\0"*4
    client.sendall(b"\x01")
    w, h = struct.unpack(">HH", read(4))
    assert (w, h) == (480, 720), (w, h)
    read(16)
    print("RFB desktop:", read(struct.unpack(">I", read(4))[0]).decode(), w, h)
    client.sendall(struct.pack(">B3xBBBBHHHBBB3x", 0, 32, 24, 0, 1, 255, 255, 255, 16, 8, 0))
    client.sendall(struct.pack(">BxHi", 2, 1, 0))

    def capture(name):
        start = time.monotonic()
        client.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, w, h))
        pixels = bytearray(w*h*3)
        while True:
            message = read(1)[0]
            if message == 2:  # Bell
                continue
            if message == 3:  # Clipboard notification
                read(3)
                read(struct.unpack(">I", read(4))[0])
                continue
            assert message == 0, message
            _, count = struct.unpack(">BH", read(3))
            for _ in range(count):
                x, y, rw, rh, encoding = struct.unpack(">HHHHi", read(12))
                assert encoding == 0 and x + rw <= w and y + rh <= h
                raw = read(rw * rh * 4)
                for row in range(rh):
                    src = raw[row*rw*4:(row+1)*rw*4]
                    offset = ((y+row)*w+x)*3
                    pixels[offset:offset+rw*3:3] = src[2::4]
                    pixels[offset+1:offset+rw*3:3] = src[1::4]
                    pixels[offset+2:offset+rw*3:3] = src[0::4]
            if count:
                break
        elapsed = (time.monotonic()-start)*1000
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB",w,h,8,2,0,0,0))
        png += chunk(b"IDAT", zlib.compress(b"".join(b"\0"+pixels[i:i+w*3] for i in range(0,len(pixels),w*3))))
        png += chunk(b"IEND",b"")
        (log/name).write_bytes(png)
        print(f"{name}: {elapsed:.0f} ms, {len(png)} PNG bytes (RFB raw, PNG generated on PC)")
        return pixels

    def key(code, pressed):
        client.sendall(struct.pack(">BB2xI", 4, pressed, code))

    def tap(code):
        key(code, 1)
        key(code, 0)

    def chord(modifier, code):
        key(modifier, 1)
        tap(code)
        key(modifier, 0)

    first = capture("initial.png")
    chord(0xffeb, 0xff0d)  # Super+Return
    time.sleep(2)
    for character in "echo VNC_INPUT_OK >/tmp/lemon-labwc-v8b/input-proof":
        tap(ord(character))
    tap(0xff0d)
    proof = root / "tmp/lemon-labwc-v8b/input-proof"
    for _ in range(12):
        if proof.exists():
            break
        time.sleep(.25)
    assert proof.read_text().strip() == "VNC_INPUT_OK"
    second = capture("two-windows.png")
    assert first != second

    def pointer(mask, x, y):
        client.sendall(struct.pack(">BBHH", 5, mask, x, y))

    # Open the real Labwc launcher using a virtual keyboard shortcut.
    chord(0xffeb, 0x20)
    time.sleep(.3)
    menu = capture("menu.png")
    assert second != menu
    tap(0xff1b)
    def drag(button, x, y, target_x, target_y):
        pointer(0, x, y)
        pointer(button, x, y)
        for i in range(1, 7):
            pointer(button, x + (target_x-x)*i//6, y + (target_y-y)*i//6)
            time.sleep(.035)
        pointer(0, target_x, target_y)
        time.sleep(.25)

    drag(1, 220, 277, 220, 432)
    moved = capture("moved.png")
    assert moved != second
    key(0xffeb, 1)
    drag(4, 390, 570, 445, 650)
    key(0xffeb, 0)
    resized = capture("resized.png")
    assert resized != moved
    chord(0xffe9, 0xff09)
    time.sleep(.25)
    capture("switched.png")
    print("PASS: RFB over stdio relay, virtual keyboard and mouse, terminal command and WM menu")

worker.join(timeout=4)
assert not worker.is_alive()

