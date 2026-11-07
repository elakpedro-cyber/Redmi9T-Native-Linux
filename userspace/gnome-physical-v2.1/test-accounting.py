import importlib.util
from pathlib import Path
p = Path(__file__).with_name('memory-report.py')
spec = importlib.util.spec_from_file_location('memory', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
rows = [
    {'uptime': 1, 'mem_available_kib': 200, 'pss_kib': 110, 'rss_kib': 220,
     'processes': [{'role':'Shell/Mutter', 'pid':1, 'pss_kib':100, 'rss_kib':200},
                   {'role':'GRD', 'pid':2, 'pss_kib':10, 'rss_kib':20}]},
    {'uptime': 2, 'mem_available_kib': 180, 'pss_kib': 105, 'rss_kib': 210,
     'processes': [{'role':'Shell/Mutter', 'pid':1, 'pss_kib':5, 'rss_kib':10},
                   {'role':'GRD', 'pid':2, 'pss_kib':100, 'rss_kib':200}]}]
for row in rows:
    for process in row['processes']: process['name'] = 'fixture'
result = m.account(rows)
assert result['peak_sample']['pss_kib'] == 110
assert result['groups_at_same_peak_sample']['GRD']['pss_kib'] == 10
assert sum(g['pss_kib'] for g in result['groups_at_same_peak_sample'].values()) != 200
print('SIMULTANEOUS_COHORT_NO_SUM_OF_PEAKS_PASS')
