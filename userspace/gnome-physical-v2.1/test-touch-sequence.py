import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('touch', Path(__file__).with_name('touch-sequence.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.validate([('down', 0), ('down', 1), ('motion', 1), ('up', 0), ('up', 1)])
m.validate([('down', 7), ('cancel', None)])
for events in [[('motion', 0)], [('down', 0), ('down', 0)], [('down', 0)], [('up', 1)]]:
    try: m.validate(events)
    except ValueError: pass
    else: raise AssertionError('Invalid touch sequence accepted')
print('TOUCH_MULTICONTACT_CANCEL_RELEASE_PASS positive=2 negative=4 synthetic_only')
