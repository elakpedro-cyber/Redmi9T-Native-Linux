from pathlib import Path
import base64
from fdt_audit import Fdt
root=Path(__file__).resolve().parents[1]
encoded=sorted((root/'logs/v4-live-diagnostics').glob('*-live-fdt-base64.txt'))[-1]
blob=base64.b64decode(encoded.read_bytes(),validate=False)
live=root/'reports/live-v4.dtb';live.write_bytes(blob)
dt=Fdt(live)
print({k:dt.cells(v) for k,v in dt.nodes['/chosen'].items() if k.startswith('linux,initrd')})
t=(root/'scripts/build-shim-v4.sh').read_text().replace('v4','v5')
(root/'scripts/build-shim-v5.sh').write_text(t,newline='\n')
t=(root/'scripts/package-v4.py').read_text().replace('v4','v5')
a=t.index('# Preserve original newc');b=t.index('shim=(art/',a)
t=t[:a]+t[b:]
(root/'scripts/package-v5.py').write_text(t,newline='\n')
t=(root/'scripts/emulate-shim-v4.py').read_text().replace('v4','v5')
(root/'scripts/emulate-shim-v5.py').write_text(t,newline='\n')
t=(root/'scripts/emulate-abl-placement.py').read_text().replace('v3','v5')
# Check the entire decompressed wrapper allocation against ABL DTB/ramdisk placement.
t=t.replace("results=[]", "wrapper=(root/'artifacts/bootshim-v5.Image').read_bytes()\nwrapper_memory=struct.unpack_from('<Q',wrapper,16)[0]\nresults=[]")
t=t.replace("    results.append(","    assert values['kernel']+wrapper_memory<=values['dtb'],values\n    results.append(")
(root/'scripts/emulate-abl-placement-v5.py').write_text(t,newline='\n')
