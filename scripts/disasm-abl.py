from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools/uefi-deps'))
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
blob=next((root/'reports/abl-extracted').rglob('*.pe')).read_bytes()
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
for span in sys.argv[1:]:
    start,end=[int(n,16) for n in span.split(':')]
    for ins in md.disasm(blob[start:end],start):
        print(f'{ins.address:#x}: {ins.mnemonic} {ins.op_str}')
