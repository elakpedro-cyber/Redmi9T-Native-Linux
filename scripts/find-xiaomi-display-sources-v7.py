from pathlib import Path
import hashlib,json,re,urllib.request
root=Path(__file__).resolve().parents[1];out=root/'downloads/v7-xiaomi-source';out.mkdir(parents=True,exist_ok=True)
commit='02ca1a919564a9b176a79cce09c40977f833e9ac'
url=f'https://api.github.com/repos/MiCode/Xiaomi_Kernel_OpenSource/git/trees/{commit}?recursive=1'
request=urllib.request.Request(url,headers={'User-Agent':'Redmi9T-native-bringup'})
data=json.load(urllib.request.urlopen(request,timeout=60))
hits=[p['path'] for p in data['tree'] if re.search(r'td4330|nt36672|ft8719|novatek',p['path'],re.I)]
(root/'reports/v7-xiaomi-source-paths.json').write_text(json.dumps({'commit':commit,'tree_truncated':data.get('truncated'),'paths':hits},indent=2)+'\n')
saved=[]
for name in hits:
    if name.endswith(('.dtsi','.h','.c')) and ('td4330' in name.lower() or 'nt36xxx' in name.lower()):
        if len(saved)>=25:break
        raw=f'https://raw.githubusercontent.com/MiCode/Xiaomi_Kernel_OpenSource/{commit}/{name}'
        content=urllib.request.urlopen(raw,timeout=30).read()
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        saved.append({'path':name,'url':raw,'sha256':hashlib.sha256(content).hexdigest()})
(root/'reports/v7-xiaomi-downloads.json').write_text(json.dumps(saved,indent=2)+'\n')
print('\n'.join(hits[:45]))
