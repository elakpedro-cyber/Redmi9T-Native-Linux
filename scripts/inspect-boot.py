import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
backup = root.parent / 'platform-tools/Redmi9T_Backup'
for name in ['boot', 'recovery']:
    out = root / 'reports' / ('stock-' + name)
    result = subprocess.check_output([sys.executable, str(root / 'tools/unpack_bootimg.py'), '--boot_img', str(backup / (name + '.img')), '--out', str(out)])
    (root / 'reports' / (name + '-header.txt')).write_bytes(result)
    result = subprocess.check_output([sys.executable, str(root / 'tools/unpack_bootimg.py'), '--boot_img', str(backup / (name + '.img')), '--out', str(out), '--format=mkbootimg'])
    (root / 'reports' / (name + '-mkbootimg.txt')).write_bytes(result)
    kernel = (out / 'kernel').read_bytes()
    if kernel[:2] == b'\x1f\x8b':
        import zlib
        dec = zlib.decompressobj(31)
        image = dec.decompress(kernel)
        (out / 'Image').write_bytes(image)
        print(name, 'ARM64 magic:', image[56:60].hex(), 'uncompressed:', len(image), 'gzip trailing:', len(dec.unused_data))
    dtb = (out / 'dtb').read_bytes()
    print(name, 'DTB length:',len(dtb),'declared:',struct.unpack_from('>I',dtb,4)[0])
print('Inspection complete')
