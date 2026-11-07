from pathlib import Path
import hashlib,json,os,shlex,shutil,subprocess,tempfile,time
root=Path(__file__).resolve().parents[1]
source=Path('/home/hadirpc/Redmi9T-Native-Linux/rootfs-v6/root')
results=[]
with tempfile.TemporaryDirectory(prefix='lemon-v6-test-',dir=str(source.parents[1])) as name:
    work=Path(name);target=work/'root'
    subprocess.run(['cp','-a',str(source),str(target)],check=True)
    for scenario in ['ncm-success','ncm-creation-fails']:
        gadget=work/scenario;gadget.mkdir()
        udcs=work/'udcs';udcs.mkdir(exist_ok=True);(udcs/'test-udc').mkdir(exist_ok=True)
        if scenario=='ncm-creation-fails':
            (gadget/'functions').mkdir();(gadget/'functions/ncm.usb0').write_text('injected creation failure')
        env={**os.environ,'LEMON_GADGET_ROOT':str(gadget),'LEMON_UDC_ROOT':str(udcs)}
        p=subprocess.run(['qemu-aarch64-static','-0','busybox',str(source/'rescue/busybox'),'sh',str(root/'config/lemon-usb-gadget-v6')],env=env,capture_output=True,timeout=10)
        assert p.returncode==0,(scenario,p.stderr)
        assert (gadget/'configs/c.1/acm.usb0').is_symlink()
        assert (gadget/'UDC').read_text().strip()=='test-udc'
        expected='0x0106' if scenario=='ncm-success' else '0x0104'
        assert (gadget/'idProduct').read_text().strip()==expected
        assert (gadget/'configs/c.1/ncm.usb0').is_symlink()==(scenario=='ncm-success')
        results.append({'scenario':scenario,'status':'PASS','scope':'ordinary-filesystem model, not configfs/USB hardware'})
    # Static console runs with neither Alpine loader nor OpenRC, and no USB network.
    rescue=work/'rescue-only'
    for directory in ['rescue','usr/local/sbin','root','run']:(rescue/directory).mkdir(parents=True,exist_ok=True)
    shutil.copy2(source/'rescue/busybox',rescue/'rescue/busybox')
    (rescue/'rescue/sh').symlink_to('busybox')
    shutil.copy2(source/'usr/local/sbin/lemon-root-shell',rescue/'usr/local/sbin/lemon-root-shell')
    p=subprocess.run(['chroot',str(rescue),'/usr/local/sbin/lemon-root-shell'],input=b'echo RESCUE_WITHOUT_NETWORK_OK\nexit\n',capture_output=True,timeout=10)
    assert p.returncode==0 and b'RESCUE_WITHOUT_NETWORK_OK' in p.stdout
    results.append({'scenario':'static-console-no-network-no-openrc-no-alpine-libraries','status':'PASS'})
    client=work/'client';wrong=work/'wrong'
    for key in [client,wrong]:subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
    shutil.copyfile(client.with_suffix('.pub'),target/'root/.ssh/authorized_keys')
    (target/'root/.ssh/authorized_keys').chmod(0o600)
    (target/'run/dropbear').mkdir(mode=0o700)
    subprocess.run(['chroot',str(target),'/usr/bin/dropbearkey','-t','ed25519','-f','/run/dropbear/host_ed25519'],check=True,capture_output=True)
    log=work/'dropbear.log'
    with log.open('wb') as output:
        server=subprocess.Popen(['chroot',str(target),'/usr/sbin/dropbear','-F','-E','-s','-j','-k','-r','/run/dropbear/host_ed25519','-p','127.0.0.1:22266'],stdout=output,stderr=output)
        try:
            common=['ssh','-p','22266','-o','ConnectTimeout=2','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','UserKnownHostsFile='+str(work/'known_hosts'),'-o','StrictHostKeyChecking=accept-new']
            for _ in range(20):
                p=subprocess.run(common+['-i',str(client),'root@127.0.0.1','echo LEMON_V6_SSH_TEST; cat /etc/alpine-release; /sbin/apk --version'],capture_output=True,timeout=8)
                if p.returncode==0:break
                if server.poll() is not None:break
                time.sleep(.2)
            assert p.returncode==0 and b'LEMON_V6_SSH_TEST' in p.stdout,(p.stderr,log.read_text())
            results.append({'scenario':'ARM64-Dropbear-public-key-auth-and-Alpine-command','status':'PASS','stdout':p.stdout.decode()})
            payload=work/'transfer.txt';payload.write_bytes(b'Redmi9T v6 SCP RAM-only roundtrip\n'+bytes(range(256))*8)
            scp=['scp','-P','22266','-i',str(client),'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','UserKnownHostsFile='+str(work/'known_hosts'),'-o','StrictHostKeyChecking=yes']
            p=subprocess.run(scp+[str(payload),'root@127.0.0.1:/tmp/lemon-v6-test.txt'],capture_output=True,timeout=15)
            assert p.returncode==0,p.stderr
            returned=work/'returned.txt'
            p=subprocess.run(scp+['root@127.0.0.1:/tmp/lemon-v6-test.txt',str(returned)],capture_output=True,timeout=15)
            assert p.returncode==0 and payload.read_bytes()==returned.read_bytes(),p.stderr
            results.append({'scenario':'SCP-default-SFTP-to-tmp-roundtrip','status':'PASS','bytes':payload.stat().st_size,'sha256':hashlib.sha256(payload.read_bytes()).hexdigest()})
            p=subprocess.run(common+['-i',str(wrong),'root@127.0.0.1','true'],capture_output=True,timeout=8)
            assert p.returncode!=0
            results.append({'scenario':'wrong-private-key-rejected','status':'PASS'})
            p=subprocess.run(common+['-vv','-o','PubkeyAuthentication=no','-o','PreferredAuthentications=password','root@127.0.0.1','true'],capture_output=True,timeout=8)
            assert p.returncode!=0 and b'Authentications that can continue: publickey' in p.stderr
            assert b'Authentications that can continue: publickey,password' not in p.stderr
            results.append({'scenario':'password-auth-not-offered','status':'PASS'})
        finally:
            server.terminate();server.wait(timeout=8)
    (root/'reports/v6-offline-sshd.log').write_bytes(log.read_bytes())
assert not (source/'run/dropbear/host_ed25519').exists()
assert (source/'root/.ssh/authorized_keys').read_bytes()==(root/'config/ssh-authorized-keys-v6').read_bytes()
(root/'reports/v6-functional-tests.json').write_text(json.dumps({'status':'PASS','phone_test_run':False,'limits':'QEMU-user shares WSL kernel/network. SSH test uses PC loopback and disposable test identities. No real NCM, Windows driver, USB traffic or serial-getty emulation.','cases':results},indent=2)+'\n')
print('PASS:',len(results),'v6 functional tests')
