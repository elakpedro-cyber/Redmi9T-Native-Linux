from pathlib import Path
import json
import struct
import subprocess

root=Path(__file__).resolve().parents[1]
blob=(root.parent/'platform-tools/Redmi9T_Backup/dtbo.img').read_bytes()
magic,total,header,entry_size,count,offset,page,version=struct.unpack_from('>8I',blob)
assert magic==0xd7b7ab1e
assert total<=len(blob)
assert offset+count*entry_size<=total
rows=[]
for i in range(count):
    size,start,ident,revision,*custom=struct.unpack_from('>8I',blob,offset+i*entry_size)
    assert start+size<=total
    path=root/'reports'/f'stock-overlay-{i}.dtbo'
    path.write_bytes(blob[start:start+size])
    rows.append({'index':i,'bytes':size,'id':ident,'revision':revision,'custom':custom})
result={'header':{'total':total,'page_size':page,'version':version,'entries':count},'entries':rows}
for name,base in [('stock',root/'reports/stock-boot/dtb'),('mainline',root/'artifacts/sm6115-xiaomi-lemon-boot.dtb')]:
    out=root/'reports'/f'{name}-overlay-result.dtb'
    proc=subprocess.run(['fdtoverlay','-i',str(base),'-o',str(out),str(root/'reports/stock-overlay-0.dtbo')],capture_output=True,text=True)
    result[name+'_overlay_0']={'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}
(root/'reports/dtbo-compatibility.json').write_text(json.dumps(result,indent=2)+'\n')
validation_path=root/'reports/offline-validation.json'
if validation_path.exists():
    validation=json.loads(validation_path.read_text())
    validation['stock_dtbo_compatibility']='FAIL: stock overlay #0 applies to stock base, but not mainline (FDT_ERR_NOTFOUND)'
    validation['boot_test_gate']='STOP until nonpersistent boot path and vendor DTBO handling are resolved'
    validation_path.write_text(json.dumps(validation,indent=2)+'\n')
print(json.dumps(result,indent=2))
