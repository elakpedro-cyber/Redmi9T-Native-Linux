from pathlib import Path
import importlib.util,json,struct
p=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fw',p/'firmware-audit.py');fw=importlib.util.module_from_spec(spec);spec.loader.exec_module(fw)
from calibration import transform,matrix
corners=[(0,0),(1079,0),(0,2339),(1079,2339)]
for rot in (0,90,180,270):
 for ix in (False,True):
  for iy in (False,True):
   points={transform(x,y,rotation=rot,invert_x=ix,invert_y=iy) for x,y in corners}
   assert points==set(corners)
   assert len(matrix(rot,ix,iy))==6
assert transform(110,220,bounds=(10,210,20,420))==(540,1170)
for x,y in [(-1,0),(1080,0),(0,2340)]:
 try:transform(x,y)
 except ValueError:pass
 else:raise AssertionError('Out of range accepted')
blob=bytearray(8192)
struct.pack_into('<III',blob,0,0x30,0,15)
blob[4096:4098]=bytes([6,249])
blob[-3:]=b'NVT'
assert fw.inspect(blob)['version']==6
for change in ('short','header','range','version','marker'):
 b=bytearray(blob)
 if change=='short':b=b[:100]
 if change=='header':b[0:4]=b'\xff'*4
 if change=='range':b[4:8]=b'\xff'*4
 if change=='version':b[fw.inspect(blob)['fw_need_write_size']-4096]=0
 if change=='marker':
  for end in range(4096,len(b)+1,4096):b[end-3:end]=b'BAD'
 try:fw.inspect(b)
 except ValueError:pass
 else:raise AssertionError('Invalid firmware accepted: '+change)
print('CALIBRATION_PASS 16 axis/rotation combinations, offset bounds, invalid coordinates')
print('FIRMWARE_NEGATIVE_PASS 5 corrupt/truncated cases on synthetic fixture; no proprietary firmware required')
