"""Inspect saved recovery newc members in PC RAM. No extraction or uploads."""
from pathlib import Path
import gzip,hashlib,importlib.util,json

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('firmware',root/'touchscreen-v1/firmware-audit.py')
fw=importlib.util.module_from_spec(spec);spec.loader.exec_module(fw)
data=gzip.decompress((root/'reports/stock-recovery/ramdisk').read_bytes())
pos=0;rows=[]
while pos+110<=len(data):
    assert data[pos:pos+6] in (b'070701',b'070702')
    header=[int(data[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
    size=header[6];length=header[11]
    assert length>0 and pos+110+length<=len(data)
    name=data[pos+110:pos+110+length-1].decode()
    start=(pos+110+length+3)&~3;assert start+size<=len(data)
    body=data[start:start+size];pos=(start+size+3)&~3
    if name=='TRAILER!!!':break
    if 'firmware' in name and 'novatek' in name.lower() and name.endswith('.bin') and '_mp' not in name:
        result=fw.inspect(body)
        rows.append({'name':name,'bytes':len(body),'sha256':result['sha256'],'metadata_version':result['version']})
out=root/'logs/touchscreen-stage1-final/recovery-normal-versions.json'
out.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
print('RECOVERY_NORMAL_FIRMWARE_METADATA_PASS',len(rows),'members; no firmware copied/uploaded')
