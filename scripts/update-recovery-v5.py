from pathlib import Path
root=Path(__file__).resolve().parents[1]
t=(root/'reports/RECOVERY_PLAN-v4-historical.md').read_text(encoding='utf-8-sig')
t=t.replace('v4','v5').replace('V4','V5').replace('v3','v4').replace('V3','V4')
t=t.replace('9379840','9576448').replace('2f90a2e9f07577f80245f70dec671f1e2b4c5a3bd79655d67c3413e6ffec24f7','4cf10f2a9c6d7298e46aec7afdcc64421b532705d29bbbf7b703ae2c90bffa45')
(root/'RECOVERY_PLAN.md').write_text(t,encoding='utf-8',newline='\n')
