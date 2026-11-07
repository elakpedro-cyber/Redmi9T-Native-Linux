from pathlib import Path
import json,re,hashlib
from fdt_audit import Fdt
root=Path(__file__).resolve().parents[1]
live=Path((root/'reports/v7-live-research-location.txt').read_text().strip())
trees={'stock':root/'reports/stock-boot/dtb','stock-overlay0-merged':root/'reports/v6-abl-merged.dtb','twrp-live':root/'reports/live.dtb','native':root/'artifacts/sm6115-xiaomi-lemon-v2.dtb','v6-live':live/'live-v6.dtb'}
report={}
for label,file in trees.items():
    dt=Fdt(file);chosen={};nodes={}
    for key,value in dt.nodes.get('/chosen',{}).items():
        if key in ['bootargs','stdout-path'] or any(s in key for s in ['panel','display','touch']):
            chosen[key]=value.rstrip(b'\0').decode(errors='replace')
    for path,props in dt.nodes.items():
        text=path+' '+ ' '.join(value.decode(errors='ignore') for key,value in props.items() if key in ['compatible','qcom,mdss-dsi-panel-name','label'])
        if not re.search(r'panel|touch|novatek|focal|goodix|td4330|ft800|nt366|backlight|gpu@|gmu@|iommu@59',text,re.I):continue
        selected={}
        for key,value in props.items():
            if key in ['compatible','status','qcom,mdss-dsi-panel-name','firmware-name','regulator-name','label','qcom,dsi-pref-prim-pan','qcom,mdss-dsi-panel'] or any(s in key for s in ['reset','gpio','supply','width','height','framerate','clock','timing','lanes','interrupt','panel-id']):
                if value.endswith(b'\0') and all(32<=c<127 or c==0 for c in value):selected[key]=dt.strings(value)
                elif len(value)<=256 and len(value)%4==0:selected[key]=[hex(c) for c in dt.cells(value)]
                else:selected[key]={'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}
        nodes[path]=selected
    report[label]={'chosen':chosen,'nodes':nodes}
(root/'reports/v7-tree-audit.json').write_text(json.dumps(report,indent=2)+'\n')
for name,data in report.items():
    print(name,'chosen:',data['chosen'])
    for path,props in data['nodes'].items():
        if any(k in props for k in ['qcom,mdss-dsi-panel-name','qcom,dsi-pref-prim-pan','qcom,mdss-dsi-panel']):print(path,props)
