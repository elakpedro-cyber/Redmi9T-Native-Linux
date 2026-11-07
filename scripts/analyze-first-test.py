from pathlib import Path
import argparse,json,re
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--version',choices=['v4','v5','v6'],required=True)
args=parser.parse_args()
folder=root/'logs'/('first-test-'+args.version)
summary=sorted(folder.glob('*.json'))[-1]
stamp=summary.stem
def read(name):return (folder/(stamp+'-'+name+'.txt')).read_text(errors='replace')
def counters(name):
    text=read(name);out={}
    for disk,values in re.findall(r'/sys/block/(sd[a-f])\s+(.*?)(?=/sys/block/|\Z)',text,re.S):
        lines=values.strip().splitlines();stat=lines[0].split()
        out[disk]={'writes_completed':int(stat[4]),'sectors_written_512':int(stat[6]),'discard_completed':int(stat[11]),'discard_sectors_512':int(stat[13]),'ioerr_cnt':int(lines[1],16)}
    return out
before,after=counters('ufs-before'),counters('ufs-after')
identity=read('identity');mounts=read('mounts-swaps');late=read('ufs-after')
allowed={'rootfs','tmpfs','devtmpfs','proc','sysfs','devpts','configfs','pstore','cgroup2','cgroup'}
def virtual_mounts_only(text):
    lines=[line.split() for line in text.splitlines()]
    mounts=[v for v in lines if len(v)==6 and v[-2:] == ['0','0']]
    return bool(mounts) and all(v[2] in allowed for v in mounts)
def no_swaps(text):
    lines=text.split('Filename',1)[1].split('rdinit=',1)[0].splitlines()[1:] if 'Filename' in text else ['MISSING']
    return not any(line.strip() for line in lines)
checks={
    'collection_complete':json.loads(summary.read_text())['status']=='COLLECTED_NOT_HARDWARE_PASS',
    'kernel_version':('lemon-bringup-'+('v5' if args.version=='v6' else args.version)) in identity,
    'init_marker':('LEMON_INIT_'+args.version.upper()+'_REACHED') in identity,
    'six_luns':set(before)==set(after)=={'sd'+c for c in 'abcdef'},
    'no_observed_block_writes':bool(before) and all(before[d]['writes_completed']==after[d]['writes_completed']==0 and before[d]['sectors_written_512']==after[d]['sectors_written_512']==0 for d in before),
    'ioerr_no_growth':bool(before) and all(before[d]['ioerr_cnt']==after[d]['ioerr_cnt'] for d in before),
    'no_observed_discards':bool(before) and all(before[d]['discard_completed']==after[d]['discard_completed']==0 and before[d]['discard_sectors_512']==after[d]['discard_sectors_512']==0 for d in before),
    'virtual_mounts_only_before':virtual_mounts_only(mounts),
    'virtual_mounts_only_after':virtual_mounts_only(late),
    'no_swap_before':no_swaps(mounts),
    'no_swap_after':no_swaps(late),
    'partitions_present':re.search(r'(?m)^\s*\d+\s+\d+\s+\d+\s+sd[a-f]\d+\s*$',read('ufs-before')) is not None,
    'acm_configured':'configured' in read('drivers'),
}
if args.version in ['v5','v6']:
    text=read('alpine-openrc')
    checks.update({'alpine_3_24_4':'3.24.4' in text,'openrc_version':'OpenRC' in text,'apk_version':'apk-tools' in text,'openrc_default':('LEMON_OPENRC_'+args.version.upper()+'_REACHED') in text and re.search(r'(?m)^default\s*$',text) is not None,'openrc_health_started':'lemon-health' in text})
report={'status':'PASS_OBSERVED_CHECKS' if all(checks.values()) else 'REVIEW_REQUIRED','version':args.version,'source':str(summary),'checks':checks,'before':before,'after':after,'limits':'No observed OS block writes in snapshots; not a proof against all firmware-side writes. Review raw logs, partition list, early counters, kernel errors and device regressions. USB shell failure tests on PC do not emulate hardware.'}
(root/'reports'/('first-test-'+args.version+'-assessment.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
if not all(checks.values()):raise SystemExit(1)
