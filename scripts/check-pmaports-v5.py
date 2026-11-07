from pathlib import Path
import importlib,json,subprocess,sys,tomllib
root=Path(__file__).resolve().parents[1]
upstream=Path('/home/hadirpc/Redmi9T-Native-Linux/v5-tools')
device=root/'pmaports/device/testing/device-xiaomi-lemon'
values={}
for line in (device/'deviceinfo').read_text().splitlines():
    if line.startswith('deviceinfo_'):
        key,value=line[len('deviceinfo_'):].split('=',1);values[key]=value.strip('"')
schema=tomllib.loads((upstream/'pmaports/deviceinfo_schema.toml').read_text())
spec={k:v for category in schema['variable'].values() for k,v in category.items()}
for key,value in values.items():
    assert key in spec,key
    s=spec[key]
    if s.get('datatype')=='boolean':assert value in ['true','false'],key
    if s.get('datatype')=='integer':int(value)
    if s.get('datatype')=='enumeration':assert value in s['enum_values'],key
for key,s in spec.items():
    if s.get('mandatory'):assert key in values,key
sys.path.insert(0,str(upstream/'pmbootstrap'))
module=importlib.import_module('pmb.parse.deviceinfo')
# No kernel variants in this local package; isolate only that repository lookup.
module.pmb.parse._apkbuild.kernels=lambda device: []
import logging
logging.verbose=logging.debug
info=module.Deviceinfo(device/'deviceinfo')
assert str(info.arch)=='aarch64' and info.flash_method=='none'
work=Path('/home/hadirpc/Redmi9T-Native-Linux/devicepkg-v5-check')
(work/'src').mkdir(parents=True,exist_ok=True)
import shutil
for name in ['deviceinfo','kernel-cmdline.conf']:shutil.copyfile(device/name,work/'src'/name)
helpers=upstream/'pmaports/main/devicepkg-dev'
subprocess.run(['sh',str(helpers/'devicepkg_build.sh'),str(work),'device-xiaomi-lemon'],check=True)
target=work/'pkg/device-xiaomi-lemon/usr/share/deviceinfo/deviceinfo'
if not target.exists():
    subprocess.run(['sh',str(helpers/'devicepkg_package.sh'),str(work),'device-xiaomi-lemon'],check=True)
assert target.read_bytes()==(device/'deviceinfo').read_bytes()
report={'schema':'PASS','pmbootstrap_deviceinfo_parser':'PASS (only kernel-variant lookup isolated)','official_devicepkg_helpers':'PASS','pmbootstrap_commit':subprocess.check_output(['git','-C',str(upstream/'pmbootstrap'),'rev-parse','HEAD']).decode().strip(),'pmaports_commit':subprocess.check_output(['git','-C',str(upstream/'pmaports'),'rev-parse','HEAD']).decode().strip(),'apk_built':False,'pmbootstrap_install_run':False}
(root/'reports/pmaports-v5-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
