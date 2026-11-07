"""Create the offline TD4330 test frame and its exact XRGB8888 payload."""
import argparse
from pathlib import Path
import struct
import zlib

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
width, height = 1080, 2340
colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255))


def pixel(x, y):
    if min(x, y, width - 1 - x, height - 1 - y) < 12:
        return (255, 255, 255)
    if 40 <= x < 120 and 40 <= y < 120:
        return (255, 255, 0)
    if abs(x - width // 2) < 8 or abs(y - height // 2) < 8:
        return (0, 0, 0)
    return colors[2 * (y >= height // 2) + (x >= width // 2)]


def chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data)))


args.output.mkdir(parents=True, exist_ok=True)
raw = bytearray()
scanlines = bytearray()
for y in range(height):
    scanlines.append(0)  # PNG filter None
    for x in range(width):
        r, g, b = pixel(x, y)
        raw.extend((b, g, r, 0))  # DRM_FORMAT_XRGB8888 on little-endian ARM64
        scanlines.extend((r, g, b))

header = struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0)
png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
       chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))
(args.output / "first-frame-1080x2340.xrgb").write_bytes(raw)
(args.output / "first-frame-1080x2340.png").write_bytes(png)
