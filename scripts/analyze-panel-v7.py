from pathlib import Path
import hashlib,json,re,struct
from fdt_audit import Fdt
root=Path(__file__).resolve().parents[1]
dt=Fdt(root/'reports/live.dtb');report={}
for path,props in dt.nodes.items():
    if 'td4330_truly_v2_video' not in path and path!='/soc/spi@4a88000' and not path.startswith('/soc/spi@4a88000/'):continue
    info={}
    for k,v in props.items():
        if len(v)%4==0: val=[hex(i) for i in dt.cells(v)]
        else:val={'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}
        if v.endswith(b'\0') and all(c==0 or 32<=c<127 for c in v):val=dt.strings(v)
        if len(v)>256:val={'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}
        if k.endswith('-supply') or k in ['qcom,panel-supply-entries','qcom,mdss-dsi-panel-supply-entries']:
            val={'cells':val,'targets':[dt.phandles.get(i) for i in dt.cells(v)]}
        info[k]=val
        if 'command' in k and len(v)>7 and not v.endswith(b'\0'):
            commands=[];off=0
            try:
                while off<len(v):
                    kind,last,channel,ack,wait,n=struct.unpack_from('>BBBBBH',v,off);off+=7
                    assert off+n<=len(v)
                    commands.append({'type':hex(kind),'wait_ms':wait,'payload_hex':v[off:off+n].hex()});off+=n
                info[k]={'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest(),'packets':commands}
            except (AssertionError,struct.error):pass
    report[path]=info
# Include provider definitions, not just unresolved downstream numeric phandles.
handles=set()
for path,props in dt.nodes.items():
    if 'td4330_truly_v2_video' in path or path.startswith('/soc/spi@4a88000'):
        for k,v in props.items():
            if k.endswith('-supply') or 'supply-entries' in k or 'gpio' in k or k=='pinctrl-0':
                if len(v)%4==0:handles.update(c for c in dt.cells(v) if c in dt.phandles)
providers={}
for h in handles:
    p=dt.phandles[h];providers[p]={k:(dt.strings(v) if v.endswith(b'\0') and all(c==0 or 32<=c<127 for c in v) else [hex(i) for i in dt.cells(v)] if len(v)%4==0 else v.hex()) for k,v in dt.nodes[p].items()}
report['resolved-providers']=providers
(root/'reports/v7-panel-touch-details.json').write_text(json.dumps(report,indent=2)+'\n')
source=root/'downloads/v7-xiaomi-source/arch/arm64/boot/dts/vendor/qcom/dsi-panel-td4330-truly-v2-singlemipi-fhd-vid.dtsi'
(root/'reports/v7-xiaomi-panel-wrapper.dts').write_text('/dts-v1/;\n/ { mdss_mdp: mdp {}; };\n'+source.read_text())
print('Selected panel, SPI touch candidates, resolved GPIO and supply providers saved')
