import base64
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import urllib.request

root = Path(__file__).resolve().parents[1]

def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=90) as response, path.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            return
        except Exception:
            if attempt == 2:
                raise

def package(line):
    match = re.match(r"'([^']+)' (\S+) (\d+) (\S+)", line)
    if not match:
        return
    url, name, size, checksum = match.groups()
    path = root / 'downloads' / 'debs' / name
    if not path.exists() or path.stat().st_size != int(size):
        fetch(url.replace('http:', 'https:'), path)
    data = path.read_bytes()
    assert len(data) == int(size), name
    algorithm, expected = checksum.split(':')
    assert hashlib.new(algorithm.lower().replace('sum', ''), data).hexdigest() == expected, name
    print(name, flush=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(package, (root / 'reports/apt-uris.txt').read_text().splitlines()))

head = '05441d697f7f9a927264f4058cbbc6a03dfcac9d'
if not (root / 'downloads/linux.tar.gz').exists():
    fetch('https://codeload.github.com/torvalds/linux/tar.gz/' + head, root / 'downloads/linux.tar.gz')
fetch('https://busybox.net/downloads/busybox-1.37.0.tar.bz2', root / 'downloads/busybox-1.37.0.tar.bz2')
for file in ['mkbootimg.py', 'unpack_bootimg.py', 'gki/generate_gki_certificate.py']:
    url = 'https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/main/' + file + '?format=TEXT'
    data = base64.b64decode(urllib.request.urlopen(url, timeout=60).read())
    path = root / 'tools' / file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
print('Downloads complete, kernel commit:', head, flush=True)
