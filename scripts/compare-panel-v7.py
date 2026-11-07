from pathlib import Path
import hashlib,json
from fdt_audit import Fdt
root=Path(__file__).resolve().parents[1]
actual=Fdt(root/'reports/live.dtb');source=Fdt(root/'reports/v7-xiaomi-panel.dtb')
ap=next(p for p in actual.nodes if p.endswith('/qcom,mdss_dsi_td4330_truly_v2_video'))
sp=next(p for p in source.nodes if p.endswith('/qcom,mdss_dsi_td4330_truly_v2_video'))
rows=[]
for p,props in source.nodes.items():
    if not p.startswith(sp):continue
    q=ap+p[len(sp):]
    for k,v in props.items():
        if k=='phandle':continue
        other=actual.nodes.get(q,{}).get(k)
        rows.append({'path':p[len(sp):] or '/','property':k,'equal':v==other,'source_bytes':len(v),'actual_bytes':len(other) if other is not None else None,'source_sha256':hashlib.sha256(v).hexdigest(),'actual_sha256':hashlib.sha256(other).hexdigest() if other is not None else None})
touch={}
for p,props in actual.nodes.items():
    if p.startswith('/soc/spi@4a88000/') and 'panel' in props:
        touch[p]={'compatible':actual.strings(props['compatible']),'panels':[actual.phandles.get(c) for c in actual.cells(props['panel'])],'selected_panel_matches':actual.cells(actual.nodes[ap]['phandle'])[0] in actual.cells(props['panel'])}
providers={}
for p,props in actual.nodes.items():
    if p.startswith('/soc/dsi_panel_pwr_supply'):
        providers[p]={k:(actual.strings(v) if v.endswith(b'\0') and all(c==0 or 32<=c<127 for c in v) else actual.cells(v) if len(v)%4==0 else v.hex()) for k,v in props.items()}
report={'selected_panel':ap,'selection_evidence':'TWRP live chosen bootargs msm_drm.dsi_display0','touch_panel_binding':touch,'source_comparison':rows,'supply_entries':providers}
(root/'reports/v7-panel-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print('Panel properties:',sum(r['equal'] for r in rows),'equal,',sum(not r['equal'] for r in rows),'different')
print(json.dumps(touch,indent=2));print(json.dumps(providers,indent=2))
