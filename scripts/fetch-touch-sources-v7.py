from pathlib import Path
import json,urllib.request,re,hashlib
root=Path(__file__).resolve().parents[1];commit='02ca1a919564a9b176a79cce09c40977f833e9ac'
base='https://raw.githubusercontent.com/MiCode/Xiaomi_Kernel_OpenSource/'+commit+'/'
request=urllib.request.Request('https://api.github.com/repos/MiCode/Xiaomi_Kernel_OpenSource/git/trees/'+commit+'?recursive=1',headers={'User-Agent':'lemon-bringup'})
tree=json.load(urllib.request.urlopen(request,timeout=60))
paths=[p['path'] for p in tree['tree'] if p['type']=='blob' and (('touchscreen' in p['path'] and re.search(r'novatek|nt36|nvt',p['path'],re.I)) or ('arch/arm64/boot/dts/vendor/qcom/' in p['path'] and re.search(r'bengal.*(touch|lcd|panel)|lime|lemon',p['path'],re.I)))]
(root/'reports/v7-touch-source-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
saved=[]
for p in paths:
    if not (p.endswith('.dtsi') or (re.search(r'spi',p,re.I) and p.endswith(('.c','.h')))):continue
    if len(saved)>35:break
    data=urllib.request.urlopen(base+p,timeout=30).read();path=root/'downloads/v7-xiaomi-source'/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    saved.append({'path':p,'url':base+p,'sha256':hashlib.sha256(data).hexdigest()})
(root/'reports/v7-touch-source-downloads.json').write_text(json.dumps(saved,indent=2)+'\n')
print('\n'.join(paths))
