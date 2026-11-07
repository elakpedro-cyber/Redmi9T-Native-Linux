"""Offline Stage1 gate/plan runner. Active registration is intentionally unavailable."""
from pathlib import Path
import argparse,json,sys

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--run',action='store_true',help='Request active execution (refused while recovery is unproven)')
p.add_argument('--check-only',action='store_true')
a=p.parse_args()
failures=[]
for name in ['lemon_nt36672a_stage1_r2.ko','spi-geni-qcom-stage1-r2.ko']:
    path=root/'artifacts/touchscreen-stage1-final'/name
    if not path.is_file():failures.append('Missing reviewed r2 module: '+name)
failures += [
    'Current VDDIO/bias electrical state and SRAM firmware handoff are not proven',
    'The old CS1 DTB/driver are revoked for active use; reviewed CS0 child registration is not implemented',
    'CONFIG_MODULE_UNLOAD=n; tested controller/pinctrl/firmware-state rollback is unavailable',
    'SPI page/read exchanges and IRQ changes still require separate hardware permission',
]
plan=[
    'Capture metadata with stage1-readonly.sh only after separate diagnostic permission',
    'Resolve electrical/handoff and recovery gates without changing shared LCD rails',
    'Review an exact CS0 registration mechanism; do not reuse the CS1 candidate',
    'Only then authorize one GENI bind and one sensor identity probe; no firmware upload or reset',
    'On valid FW5/PID5940/1080x2340 authorize one 10-second evdev recording with one finger',
    'Close the owned reader, collect fault/IRQ/DRM/UFS state; do not rmmod or force unbind',
]
print(json.dumps({'decision':'NO-GO','active_requested':a.run,'hardware_actions_executed':False,
                  'blockers':failures,'proposed_stages':plan},indent=2))
if a.run:print('REFUSED before any device access: a reliable hardware rollback is not established',file=sys.stderr)
sys.exit(78)
