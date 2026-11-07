"""Assert the exact offline DT delta; never connects to the device."""
from pathlib import Path
import hashlib,json,struct,sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from fdt_audit import Fdt

base=root/'artifacts/sm6115-xiaomi-lemon-v8b.dtb'
candidate=Path(sys.argv[1]) if len(sys.argv)>1 else root/'artifacts/touchscreen-v1/dtb-review/touchscreen-handoff-review.dtb'
before=Fdt(base);after=Fdt(candidate)
spi='/soc@0/geniqup@4ac0000/spi@4a88000'
tlmm='/soc@0/pinctrl@500000'
touch=spi+'/touchscreen@1'
pins=[tlmm+'/lemon-touch-spi-data-state',tlmm+'/lemon-touch-spi-cs-state']
assert set(after.nodes)-set(before.nodes)=={touch,*pins}
assert not set(before.nodes)-set(after.nodes)
changed={}
for path,props in before.nodes.items():
    delta={key for key in set(props)|set(after.nodes[path]) if props.get(key)!=after.nodes[path].get(key)}
    if delta:changed[path]=sorted(delta)
assert changed=={spi:['num-cs','pinctrl-0']},changed
def reservations(f):
    offset=struct.unpack_from('>I',f.data,16)[0]
    entries=[]
    while True:
        pair=struct.unpack_from('>QQ',f.data,offset);offset+=16
        if pair==(0,0):return entries
        entries.append(pair)
assert reservations(before)==reservations(after)
assert struct.unpack_from('>I',before.data,28)==struct.unpack_from('>I',after.data,28)
assert after.nodes[spi]['status']==before.nodes[spi]['status']==b'okay\0'
assert after.cells(after.nodes[spi]['num-cs'])==[2]
assert [after.phandles[v] for v in after.cells(after.nodes[spi]['pinctrl-0'])]==pins
for path,values,pull in [(pins[0],['gpio6','gpio7','gpio71'],'bias-pull-down'),(pins[1],['gpio80'],'bias-pull-up')]:
    props=after.nodes[path]
    assert after.strings(props['pins'])==values
    assert props['function']==b'qup2\0' and after.cells(props['drive-strength'])==[6]
    assert pull in props and len(props[pull])==0
t=after.nodes[touch]
assert t['status']==b'disabled\0'
assert t['compatible']==b'xiaomi,lemon-nt36672a-handoff\0'
for key,want in [('reg',1),('spi-max-frequency',9600000),('qcom,cs-delay-counter',200),('qcom,inter-word-delay-counter',0),('touchscreen-size-x',1080),('touchscreen-size-y',2340)]:
    assert after.cells(t[key])==[want],key
irq=after.cells(t['interrupts-extended'])
assert after.phandles[irq[0]]==tlmm and irq[1:]==[93,1]
assert not any(key.endswith('-supply') or 'reset' in key or key=='xiaomi,validated-touch-handoff' for key in t)
# Whole-tree comparison above includes display, framebuffer, memory, UFS,
# regulators, firmware, chosen, clocks and their original phandle values.
log=root/'logs/touchscreen-v1/dtb-review'
def warnings(name):
    text=(log/name).read_text()
    return [line[line.index('Warning ('):] for line in text.splitlines() if 'Warning (' in line]
base_warnings=warnings('base-inspection-dtc.txt')
candidate_warnings=warnings('candidate-inspection-dtc.txt')
assert candidate_warnings==base_warnings,(base_warnings,candidate_warnings)
result={'base_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),
        'candidate_bytes':candidate.stat().st_size,'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
        'changed_existing_properties':changed,'added_nodes':sorted(set(after.nodes)-set(before.nodes)),
        'sensor_disabled':True,'authorization_property_absent':True,
        'all_other_nodes_and_properties_identical':True,'reservation_map_and_boot_cpu_unchanged':True,
        'baseline_dtc_warning_count':len(base_warnings),'new_merged_dtc_warnings':0,
        'status':'offline-only; not loaded or booted'}
(log/'delta.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('EXACT_DT_DELTA_PASS; touch disabled; all display/power/UFS properties unchanged')
