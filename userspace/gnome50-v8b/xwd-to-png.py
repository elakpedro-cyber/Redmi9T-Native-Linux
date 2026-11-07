import struct,zlib,sys
from pathlib import Path
def c(t,x):return struct.pack('>I',len(x))+t+x+struct.pack('>I',zlib.crc32(t+x))
for p in Path(sys.argv[1]).glob('*.xwd'):
 b=p.read_bytes()
 if len(b)<100:continue
 h=struct.unpack('>25I',b[:100]); w,n=h[4:6]; s=h[12]; b=b[h[0]+h[19]*12:]
 assert h[7]==0 and h[11]==32 and (h[14],h[15],h[16])==(0xff0000,0xff00,0xff)
 out=bytearray()
 for i in range(n):
  row=b[i*s:i*s+w*4]
  rgb=bytearray(w*3); rgb[0::3]=row[2::4];rgb[1::3]=row[1::4];rgb[2::3]=row[0::4]
  out.extend(b'\0'+rgb)
 p.with_suffix('.png').write_bytes(b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',w,n,8,2,0,0,0))+c(b'IDAT',zlib.compress(out))+c(b'IEND',b''))



