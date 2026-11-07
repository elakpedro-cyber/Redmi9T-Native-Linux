import importlib.util
from pathlib import Path
from types import SimpleNamespace
p = Path(__file__).with_name('control.py')
spec = importlib.util.spec_from_file_location('control', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
assert all(path.is_file() for path in m.payload_paths().values())
s = object.__new__(m.Session)
s.base = '/tmp/lemon-gnome-v21.ABC123'
s.state = {'boot': 'old'}
commands = []
s.remote = lambda command: commands.append(command) or b'new\n'
s.stop()
assert commands == ['cat /proc/sys/kernel/random/boot_id']
s.state = {'boot': 'same'}
s.remote = lambda command: commands.append(command) or b'same\n'
s.no_owners = lambda: None
s.stop()
s.stop()
# Signalling is guarded by both the exact executable path and its recorded start time.
for command in commands[2::2]:
    assert 'readlink "/proc/$p/exe"' in command
    assert 'watchdog.start' in command
    assert 'kill -TERM "$p"' in command
    assert 'killall' not in command
print('CONTROLLER_STALE_BOOT_REPEAT_STOP_IDENTITY_GUARDS_PASS')

# Failed launches must still collect postflight/UFS evidence, without deleting the RAM tree.
import tempfile
class FailedProcess:
    returncode = 1
    def poll(self): return self.returncode
    def wait(self, **kw): return self.returncode
old_popen = m.subprocess.Popen
old_log, old_state, old_root = m.LOG, m.STATE, m.ROOT
try:
    with tempfile.TemporaryDirectory() as directory:
        m.ROOT = Path(directory)
        m.LOG = Path(directory)/"logs"
        m.STATE = m.LOG/'current.json'
        m.subprocess.Popen = lambda *a, **kw: FailedProcess()
        s = object.__new__(m.Session)
        s.args = SimpleNamespace(mode='C', seconds=60, profile='baseline', test_actions=False, measure=False)
        s.base = '/tmp/lemon-gnome-v21.ABC123'
        s.state = {'base':s.base}
        s.ssh = []
        s.preflight = lambda: 'boot'
        s.prepare = lambda boot: None
        events = []
        snapshot = b'UPTIME 1\nDISPLAY_ISOLATED_1\n' + b''.join(name.encode()+b' '+b'0 '*17+b'\n' for name in ('sda','sdb','sdc','sdd','sde','sdf'))
        s.remote = lambda command: events.append(command) or snapshot
        s.collect = lambda: events.append('COLLECTED')
        s.no_owners = lambda: events.append('OWNERS_CHECKED')
        try: s.start()
        except RuntimeError as error: assert 'Session/TTY restoration exited 1' in str(error)
        else: raise AssertionError('Failure was lost')
        assert 'COLLECTED' in events and 'OWNERS_CHECKED' in events
        assert (s.log/'after.txt').is_file()
        assert not any('rm -rf' in command for command in events)
        print('CONTROLLER_FAILURE_POSTFLIGHT_UFS_NO_DELETE_PASS')
        class SuccessProcess(FailedProcess): returncode = 0
        m.subprocess.Popen = lambda *a, **kw: SuccessProcess()
        events.clear()
        s.start()
        assert any('rm -rf' in command for command in events)
        assert s.state['base'] == ''
        print('CONTROLLER_SUCCESS_COLLECT_BEFORE_RAM_DELETE_PASS')
finally:
    m.subprocess.Popen = old_popen
    m.LOG, m.STATE, m.ROOT = old_log, old_state, old_root
