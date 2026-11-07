from pathlib import Path
import hashlib
import json
from fdt_audit import Fdt

root=Path(__file__).resolve().parents[1]
dt=Fdt(root/'artifacts/sm6115-xiaomi-lemon-v2.dtb')
report={}
spec={'clocks':'#clock-cells','resets':'#reset-cells','power-domains':'#power-domain-cells','phys':'#phy-cells','iommus':'#iommu-cells','interconnects':'#interconnect-cells'}
for path in ['/soc@0/ufshc@4804000','/soc@0/phy@4807000']:
    props=dt.nodes[path];out={}
    for key,raw in props.items():
        if key in spec or key.endswith('-supply'):
            cells=dt.cells(raw);i=0;refs=[]
            while i<len(cells):
                provider=dt.phandles[cells[i]];i+=1
                count=dt.cells(dt.nodes[provider][spec[key]])[0] if key in spec else 0
                args=cells[i:i+count];i+=count
                refs.append({'provider':provider,'args':args,'provider_status':dt.nodes[provider].get('status',b'okay\0').rstrip(b'\0').decode()})
            out[key]=refs
        elif key in ['compatible','status'] or key.endswith('-names'):
            out[key]=dt.strings(raw)
        else:
            out[key]=[hex(v) for v in dt.cells(raw)] if len(raw)%4==0 else raw.hex()
    report[path]=out
(root/'reports/ufs-v4-dt-dependencies.json').write_text(json.dumps(report,indent=2)+'\n')
files=[*sorted((root/'bootshim').glob('*')),*sorted((root/'config').glob('*v4*')),*sorted((root/'scripts').glob('*v4*'))]
manifest={str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files if p.is_file()}
(root/'reports/v4-source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(report,indent=2))
