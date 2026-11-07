from pathlib import Path
import hashlib
import json
import struct

root = Path(__file__).resolve().parents[1]
abl = (root / 'reports/abl-readonly.bin').read_bytes()
pe = next((root / 'reports/abl-extracted').rglob('*.pe')).read_bytes()
flash = pe.index(b'flash:\0')
erase = pe.index(b'erase:\0')
table = pe.index(struct.pack('<Q', flash))
assert struct.unpack_from('<Q', pe, table + 16)[0] == erase
rows = []
for offset in range(table, len(pe) - 16, 16):
    address, handler = struct.unpack_from('<QQ', pe, offset)
    if not (0 < address < len(pe) and 0x1000 <= handler < 0x42000):
        break
    command = pe[address:].split(b'\0', 1)[0].decode('ascii')
    rows.append({'offset': hex(offset), 'command': command, 'handler': hex(handler)})
report = {
    'abl_sha256': hashlib.sha256(abl).hexdigest(),
    'pe_sha256': hashlib.sha256(pe).hexdigest(),
    'command_count': len(rows),
    'boot_in_table': any(row['command'] == 'boot' for row in rows),
    'commands': rows,
    'conclusion': 'boot absent from recovered static table; runtime protocol not tested',
}
(root / 'reports/abl-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
text = '\n'.join(f"{row['offset']}: {row['command']!r} -> {row['handler']}" for row in rows)
(root / 'reports/abl-command-table.txt').write_text(text + '\n')
print(text)
print(report['conclusion'])
