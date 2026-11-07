from pathlib import Path
root=Path(__file__).resolve().parents[1]
t=(root/'scripts/build-kernel-v4.sh').read_text().replace('v4','v5')
t=t.replace('config/linux.config','config/linux-v4.config').replace('ufs-v5.fragment','bringup-v5.fragment')
(root/'scripts/build-kernel-v5.sh').write_text(t,newline='\n')
