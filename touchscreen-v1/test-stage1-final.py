"""PC-only policy, read-only fixture and source guard regression."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,hashlib

root=Path(__file__).resolve().parents[1]
for args in [['--check-only'],['--run']]:
    result=subprocess.run([sys.executable,str(root/'touchscreen-v1/stage1-test.py'),*args],capture_output=True,text=True)
    assert result.returncode==78
    data=json.loads(result.stdout);assert data['decision']=='NO-GO' and not data['hardware_actions_executed']
    assert len(data['blockers'])>=4
print('FAIL_CLOSED_CHECK_AND_RUN_PASS code78; no active path')
source=root/'touchscreen-v1/stage1-r2'
nvt=(source/'nvt-spi.c').read_text();geni=(source/'spi-geni-qcom-stage1-r2.c').read_text()
assert 'spi_get_chipselect(spi, 0) != 0' in nvt
assert 'xiaomi,stock-cs0-reviewed' in nvt and 'info[0] != 5' in nvt
assert 'module_param(recording_authorized, bool, 0600)' in nvt
opening=nvt[nvt.index('static int nvt_open'):nvt.index('static void nvt_stop')]
assert opening.index('if (!READ_ONCE(recording_authorized))')<opening.index('nvt_identity(ts)')
assert 'geni_load_se_firmware(' not in geni
for forbidden in ['gpio_set_value(', 'regulator_enable(', 'regulator_disable(', 'request_firmware(']:assert forbidden not in nvt
print('R2_SOURCE_GUARDS_PASS CS0 FW5 opt-in; no sensor reset/power/upload or GENI auto-upload')
with tempfile.TemporaryDirectory(prefix='lemon-touch-ro-fixture-') as directory:
    fixture=Path(directory)
    for name,text in [('proc/sys/kernel/osrelease','fixture-v8b\n'),('sys/class/tty/tty0/active','tty1\n'),('proc/swaps','Filename\tType\n'),('sys/class/regulator/regulator.11/name','l9\n')]:
        path=fixture/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    def state():return {str(p.relative_to(fixture)):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.rglob('*') if p.is_file()}
    before=state()
    result=subprocess.run(['sh',str(root/'touchscreen-v1/stage1-readonly.sh')],env={**os.environ,'LEMON_DIAG_ROOT':str(fixture)},capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert state()==before
    assert 'fixture-v8b' in result.stdout and 'ELECTRICAL_VDDIO_LCD_BIAS_IRQ_CS_RESET_LEVELS=UNKNOWN' in result.stdout
print('READONLY_FIXTURE_PASS no mutations; electrical levels never inferred')
