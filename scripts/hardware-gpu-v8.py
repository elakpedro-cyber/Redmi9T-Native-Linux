from pathlib import Path
import argparse,datetime,hashlib,json,subprocess,time
root=Path(__file__).resolve().parents[1];log=root/'logs/v8-authorized';log.mkdir(exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','load','render','after']);args=parser.parse_args()
key=json.loads((root/'logs/v6-authorized/test-client-identity.json').read_text())['private_key_path']
pin=log/'v8-known_hosts'
common=['-i',key,'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ServerAliveInterval=3','-o','ServerAliveCountMax=2','-o','KexAlgorithms=curve25519-sha256','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(pin),'-o','PasswordAuthentication=no','-o','KbdInteractiveAuthentication=no']
ssh=['ssh.exe',*common,'root@192.168.77.2']
def run(name,command,seconds=20,required=True):
    (log/'gpu-commands.jsonl').open('a').write(json.dumps({'time':time.time(),'phase':args.phase,'name':name,'command':command,'timeout':seconds})+'\n')
    try:p=subprocess.run(ssh+[command],capture_output=True,timeout=seconds)
    except subprocess.TimeoutExpired as error:
        (log/(name+'.stdout')).write_bytes(error.stdout or b'');(log/(name+'.stderr')).write_bytes(error.stderr or b'')
        (log/(name+'.json')).write_text(json.dumps({'returncode':None,'timed_out':True})+'\n');raise
    (log/(name+'.stdout')).write_bytes(p.stdout);(log/(name+'.stderr')).write_bytes(p.stderr)
    (log/(name+'.json')).write_text(json.dumps({'returncode':p.returncode,'timed_out':False})+'\n')
    print(name,'exit',p.returncode,flush=True)
    if required:p.check_returncode()
    return p
storage='for d in sda sdb sdc sdd sde sdf; do test -b /dev/$d || exit 30; /bin/busybox awk \'$5 != 0 || $7 != 0 || $12 != 0 || $14 != 0 {bad=1} END {exit bad}\' /sys/block/$d/stat || exit 31; done; /bin/busybox awk \'$3 !~ /^(rootfs|tmpfs|devtmpfs|proc|sysfs|devpts|configfs|pstore|cgroup|cgroup2)$/ {bad=1} END {exit bad}\' /proc/mounts || exit 32; test "$(wc -l < /proc/swaps)" -eq 1'
diagnostic='uname -a; cat /proc/uptime; lsmod; ls -l /dev/dri /sys/class/drm; if test -e /sys/module/msm/parameters/separate_gpu_kms; then cat /sys/module/msm/parameters/separate_gpu_kms; fi; for p in /sys/class/thermal/thermal_zone*; do echo "$p"; cat "$p/type" "$p/temp"; done; for p in /sys/class/power_supply/*; do echo "$p"; cat "$p/uevent"; done; for p in /sys/class/devfreq/*; do echo "$p"; cat "$p/name" "$p/cur_freq" "$p/available_frequencies" "$p/device/power/runtime_status"; done; for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt"; done; cat /proc/mounts /proc/swaps'
if args.phase=='prepare':
    run('gpu-pre-storage-guard',storage)
    run('gpu-pre-identity','test "$(cat /run/init-reached)" = LEMON_INIT_V8_REACHED && test ! -d /sys/module/msm && cat /etc/modprobe.d/lemon-gpu-manual.conf && free -m && test "$(/bin/busybox awk \'$2=="/tmp" {print $3}\' /proc/mounts)" = tmpfs')
    run('gpu-timeout-help','/bin/busybox timeout --help',required=False)
    run('gpu-pre-dmesg','dmesg')
    run('gpu-pre-diagnostic',diagnostic,required=False)
    archive=root/'artifacts/gpu-userspace-v7.tar.gz';digest='b81dcac42177033382803779dd0ef1450a42e096a76b22fb260737bac6297620'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest
    p=subprocess.run(['scp.exe',*common,str(archive),'root@192.168.77.2:/tmp/gpu-userspace-v7.tar.gz'],capture_output=True,timeout=45)
    (log/'gpu-addon-upload.stdout').write_bytes(p.stdout);(log/'gpu-addon-upload.stderr').write_bytes(p.stderr);p.check_returncode()
    p=run('gpu-addon-sha','sha256sum /tmp/gpu-userspace-v7.tar.gz');assert p.stdout.split()[0].decode()==digest
    run('gpu-addon-extract','tar xpf /tmp/gpu-userspace-v7.tar.gz -C / && test -x /usr/local/bin/gpu-render-v7 && /lib/ld-musl-aarch64.so.1 --list /usr/local/bin/gpu-render-v7',seconds=35)
    run('gpu-firmware-before','sha256sum /lib/firmware/qcom/a630_sqe.fw /lib/firmware/qcom/sm6115/xiaomi/lemon/a610_zap.*; cat /etc/modprobe.d/lemon-gpu-manual.conf')
    run('gpu-addon-storage-guard',storage)
    (log/'gpu-prepared.json').write_text(json.dumps({'ready':True,'addon_sha256':digest})+'\n')
elif args.phase=='load':
    assert (log/'gpu-prepared.json').exists()
    journal=log/'gpu-load-once.json';assert not journal.exists(),'No second GPU load attempt'
    run('gpu-load-pre-storage',storage)
    journal.write_text(json.dumps({'start':time.time(),'command':'timeout -s TERM -k 3 15 modprobe msm separate_gpu_kms=1','attempt':1})+'\n')
    run('gpu-load-once','/bin/busybox timeout -s TERM -k 3 15 /sbin/modprobe msm separate_gpu_kms=1',seconds=23)
    run('gpu-after-load-dmesg','dmesg')
    run('gpu-after-load-diagnostic',diagnostic,required=False)
    run('gpu-parameter-confirm','test "$(cat /sys/module/msm/parameters/separate_gpu_kms)" = 1 && ls -l /sys/class/drm/renderD*/device/driver /dev/dri')
elif args.phase=='render':
    assert (log/'gpu-load-once.json').exists()
    journal=log/'gpu-render-once.json';assert not journal.exists(),'No second GPU render attempt'
    run('gpu-render-pre-storage',storage)
    run('gpu-render-node','for p in /sys/class/drm/renderD*; do test -e "$p" || continue; echo "$p"; readlink -f "$p/device/driver"; done')
    # Select only the render node whose platform driver is msm/adreno.
    command='node=; for p in /sys/class/drm/renderD*; do test -e "$p" || continue; driver=$(readlink -f "$p/device/driver"); case "$driver" in */adreno|*/msm) node=/dev/dri/${p##*/};; esac; done; test -n "$node" || exit 40; echo "GPU_TEST_NODE=$node"; /bin/busybox timeout -s TERM -k 3 20 env MESA_SHADER_CACHE_DISABLE=true /usr/local/bin/gpu-render-v7 "$node"'
    journal.write_text(json.dumps({'start':time.time(),'limit_seconds':20,'attempt':1,'command':command})+'\n')
    p=run('gpu-render-once',command,seconds=28,required=False)
    if p.returncode==0:
        assert b'LEMON_GPU_V7_RENDER_PASS' in p.stdout
        run('gpu-render-output-sha','sha256sum /tmp/gpu-render-v7.rgba; wc -c /tmp/gpu-render-v7.rgba')
    run('gpu-after-render-dmesg','dmesg',required=False)
    run('gpu-after-render-diagnostic',diagnostic,required=False)
    run('gpu-after-render-storage',storage)
else:
    run('gpu-final-dmesg','dmesg',required=False)
    run('gpu-final-diagnostic',diagnostic,required=False)
    run('gpu-final-storage',storage)
    run('gpu-final-services','cat /run/init-reached /run/openrc-reached; rc-status; ip address show dev usb0; cat /run/ssh-hostkey.txt; ls -l /sys/class/backlight; cat /proc/bus/input/devices')
