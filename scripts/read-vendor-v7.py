exec((__import__('pathlib').Path(__file__).parent/'inspect-super-v7.py').read_text())
for p in report['partitions']:
    if p['name']!='vendor':continue
    dest=out/('vendor-slot'+str(p['slot'])+'.img')
    if dest.exists():
        assert dest.stat().st_size in [0,p['bytes']], 'Partial vendor copy: inspect before resuming'
        if dest.stat().st_size==p['bytes']:continue
    with dest.open('wb') as output:
        for e in p['extents']:
            assert e['source']==0 and e['type']==0
            assert e['target_sector']%8==0 and e['sectors']%8==0
            command='test "$(grep PARTNAME /sys/class/block/sda10/uevent)" = PARTNAME=super && /bin/busybox dd if=/dev/sda10 bs=4096 skip=%d count=%d'%(e['target_sector']//8,e['sectors']//8)
            result=subprocess.run(ssh+[command],stdout=output,stderr=subprocess.PIPE,timeout=240)
            assert result.returncode==0,result.stderr
    assert dest.stat().st_size==p['bytes']
    print(dest,hashlib.sha256(dest.read_bytes()).hexdigest())
