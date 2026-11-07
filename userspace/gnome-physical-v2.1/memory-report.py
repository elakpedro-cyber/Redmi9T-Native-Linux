"""Account for one simultaneous process cohort at a time, never sum independent peaks."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

ROLES = {'gnome-shell': 'Shell/Mutter', 'gnome-remote-de': 'GRD', 'pipewire': 'PipeWire',
         'weston': 'Weston', 'wlfreerdp3': 'RDP client', 'wireplumber': 'WirePlumber'}


def samples(text, page_size):
    result = []
    for chunk in text.split('UPTIME ')[1:]:
        sample = {'uptime': float(chunk.split()[0]), 'processes': [], 'incomplete_pids': []}
        match = re.search(r'^MemAvailable:\s+(\d+)', chunk, re.M)
        sample['mem_available_kib'] = int(match[1]) if match else None
        for block in chunk.split('PROCESS ')[1:]:
            lines = block.splitlines()
            pid = int(lines[0])
            pss = re.search(r'^Pss:\s+(\d+)', block, re.M)
            if len(lines) < 3 or ') ' not in lines[2] or not pss:
                sample['incomplete_pids'].append(pid)
                continue
            fields = lines[2].rsplit(') ', 1)[1].split()
            rss = re.search(r'^Rss:\s+(\d+)', block, re.M)
            process = {'pid': pid, 'name': lines[1], 'role': ROLES.get(lines[1], 'Other'),
                       'pss_kib': int(pss[1]), 'rss_kib': int(rss[1]) if rss else int(fields[21])*page_size//1024,
                       'rss_source': 'smaps_rollup' if rss else 'stat page counter (approximate)',
                       'start_ticks': int(fields[19])}
            sample['processes'].append(process)
        sample['pss_kib'] = sum(p['pss_kib'] for p in sample['processes'])
        sample['rss_kib'] = sum(p['rss_kib'] for p in sample['processes'])
        result.append(sample)
    return result


def account(rows):
    peak = max(rows, key=lambda sample: sample['pss_kib'])
    groups = defaultdict(lambda: {'pss_kib': 0, 'rss_kib': 0, 'pids': []})
    for process in peak['processes']:
        group = groups[process['role']]
        for field in ('pss_kib', 'rss_kib'):
            group[field] += process[field]
        group['pids'].append(process['pid'])
    cohorts = defaultdict(list)
    for sample in rows:
        names = {process['name'] for process in sample['processes']}
        scenario = 'Settings present' if 'gnome-control-c' in names else 'Console present' if 'kgx' in names else 'startup/desktop'
        cohorts[scenario].append(sample['pss_kib'])
    return {'samples': len(rows), 'page_size': None,
            'peak_sample': peak, 'groups_at_same_peak_sample': dict(groups),
            'scenario_ranges_kib': {name: {'minimum': min(values), 'maximum': max(values)} for name, values in cohorts.items()},
            'minimum_mem_available_kib': min((row['mem_available_kib'] for row in rows if row['mem_available_kib'] is not None), default=None),
            'limitations': ['Coherent sampling window, not an atomic snapshot',
                'Missing/exited PIDs are listed, not silently attributed to another cohort',
                'RSS sums double count shared mappings; PSS divides shared pages',
                'PSS excludes unmapped tmpfs/rootfs/kernel/driver memory',
                'Changes with app set and warm caches are not proof of a leak']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--page-size', type=int, required=True)
    args = parser.parse_args()
    data = account(samples((args.log/'samples.txt').read_text(), args.page_size))
    data['page_size'] = args.page_size
    (args.log/'memory-accounting.json').write_text(json.dumps(data, indent=2)+'\n')
    print(json.dumps({key: value for key, value in data.items() if key != 'peak_sample'}, indent=2))
