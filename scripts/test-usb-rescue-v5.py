from pathlib import Path
import json,shutil,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
results=[]
with tempfile.TemporaryDirectory(prefix='lemon-rescue-',dir='/home/hadirpc/Redmi9T-Native-Linux') as name:
    target=Path(name)
    for directory in ['rescue','usr/local/sbin','root','run','sbin']:(target/directory).mkdir(parents=True,exist_ok=True)
    shutil.copy2(root/'artifacts/BusyBox-v4',target/'rescue/busybox')
    (target/'rescue/sh').symlink_to('busybox')
    shell=target/'usr/local/sbin/lemon-root-shell'
    shutil.copy2(root/'config/lemon-root-shell-v5',shell);shell.chmod(0o755)
    (target/'rescue/busybox').chmod(0o755)
    for scenario in ['missing-openrc-and-alpine-libraries','openrc-exits-1','openrc-hangs']:
        child=None
        if scenario!='missing-openrc-and-alpine-libraries':
            command='exit 1' if scenario=='openrc-exits-1' else 'exec /rescue/busybox sleep 60'
            mock=target/'sbin/openrc';mock.write_text('#!/rescue/busybox sh\n'+command+'\n');mock.chmod(0o755)
            if scenario=='openrc-exits-1':assert subprocess.run(['chroot',name,'/sbin/openrc']).returncode==1
            else:child=subprocess.Popen(['chroot',name,'/sbin/openrc'])
        try:
            p=subprocess.run(['chroot',name,'/usr/local/sbin/lemon-root-shell'],input=b"echo RESCUE_COMMAND_EXECUTED\nexit\n",capture_output=True,timeout=10)
            assert p.returncode==0 and b'USB_RESCUE_SHELL_V5' in p.stdout and b'RESCUE_COMMAND_EXECUTED' in p.stdout,(scenario,p.stdout,p.stderr)
            results.append({'scenario':scenario,'status':'PASS','stdout':p.stdout.decode(),'stderr':p.stderr.decode()})
        finally:
            if child is not None:child.terminate();child.wait(timeout=5)
(root/'reports/v5-rescue-failure-tests.json').write_text(json.dumps({'status':'PASS','scope':'QEMU-user/chroot shell isolation only; USB hardware/getty not emulated','cases':results},indent=2)+'\n')
print('PASS:',len(results),'static shell scenarios without Alpine loader or /bin/sh')
