from pathlib import Path
import json
from fdt_audit import Fdt
root=Path(__file__).resolve().parents[1]
report={}
for name,file in [('stock',root/'reports/stock-boot/dtb'),('native',root/'artifacts/sm6115-xiaomi-lemon-v2.dtb'),('live-v4',root/'reports/live-v4.dtb')]:
    tree=Fdt(file);items={}
    for path,props in tree.nodes.items():
        compatible=tree.strings(props.get('compatible',b''))
        if any(any(s in c.lower() for s in ['adreno','novatek','focal','goodix','touch','nt36','ft5','mdss','simple-framebuffer']) for c in compatible):
            items[path]={'compatible':compatible,'status':tree.strings(props.get('status',b'okay\0'))}
    report[name]=items
(root/'reports/hardware-v5-dt-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
