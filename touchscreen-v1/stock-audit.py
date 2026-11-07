"""Resolve touch pins and supply phandles inside each saved DT, without rebuilding it."""
from pathlib import Path
import hashlib,json,sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from fdt_audit import Fdt

result={}
for name,filename in [('TWRP-live','reports/live.dtb'),('stock-overlay-result','reports/stock-overlay-result.dtb')]:
    f=Fdt(root/filename)
    bus='/soc/spi@4a88000'
    touch=f.nodes[bus+'/novatek@1']
    row={'blob':filename,'sha256':hashlib.sha256(f.data).hexdigest(),'bus':bus,'pinctrl':[],
         'touch':{},'supplies':{}}
    for prop in ['reg','spi-max-frequency','novatek,reset-gpio','novatek,irq-gpio','spi-cs-clk-delay','spi-inter-words-delay']:
        row['touch'][prop]=[hex(v) for v in f.cells(touch[prop])]
    for prop in ['pinctrl-0','pinctrl-1']:
        for phandle in f.cells(f.nodes[bus][prop]):
            target=f.phandles[phandle]
            item={'property':prop,'phandle_in_this_blob':hex(phandle),'target':target,'nodes':{}}
            for path,props in f.nodes.items():
                if path==target or path.startswith(target+'/'):
                    item['nodes'][path]={}
                    for key,value in props.items():
                        item['nodes'][path][key]=(f.strings(value) if key in ['pins','function'] else [hex(v) for v in f.cells(value)])
            row['pinctrl'].append(item)
    for prop in ['touch_vddio-supply','touch_lab-supply','touch_ibb-supply']:
        row['supplies'][prop]=f.phandles[f.cells(touch[prop])[0]]
    result[name]=row
output=root/'logs/touchscreen-v1/stock-topology.json'
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('SAVED_DT_AUDIT_PASS',len(result),'blobs; phandles resolved independently')
