"""Negative tests on PC-only DTB copies; no device I/O."""
from pathlib import Path
import shutil,subprocess,tempfile

root=Path(__file__).resolve().parents[1]
candidate=root/'artifacts/touchscreen-v1/dtb-review/touchscreen-handoff-review.dtb'
touch='/soc@0/geniqup@4ac0000/spi@4a88000/touchscreen@1'
cases=[
    ('enabled-sensor',['-t','s',touch,'status','okay']),
    ('wrong-cs',['-t','x',touch,'reg','0']),
    ('wrong-irq',['-t','x',touch,'interrupts-extended','28','5c','1']),
    ('authorization-present',[touch,'xiaomi,validated-touch-handoff']),
    ('unrelated-power-change',['-t','x','/remoteproc/glink-edge/rpm-requests/regulators-0/l15','regulator-max-microvolt','1']),
]
with tempfile.TemporaryDirectory(prefix='lemon-touch-dtb-negative-') as directory:
    for name,args in cases:
        path=Path(directory)/(name+'.dtb');shutil.copyfile(candidate,path)
        options=[]
        if args[0]=='-t':options=args[:2];args=args[2:]
        subprocess.run(['fdtput',*options,str(path),*args],check=True)
        result=subprocess.run(['python3',str(root/'touchscreen-v1/validate-dtb.py'),str(path)],capture_output=True,text=True)
        if result.returncode==0:raise AssertionError('Unsafe DT accepted: '+name)
        assert 'AssertionError' in result.stderr,result.stderr
        print('DT_NEGATIVE_REJECTED',name)
print('OFFLINE_DTB_NEGATIVE_PASS',len(cases))
