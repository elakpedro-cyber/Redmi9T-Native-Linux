import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("mapping", Path(__file__).with_name("touch-map.py"))
mapping = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapping)
assert mapping.coordinates(0, 0, (0, 1079, 0, 2339)) == (0, 0)
assert mapping.coordinates(1079, 2339, (0, 1079, 0, 2339)) == (1079, 2339)
assert mapping.coordinates(110, 220, (10, 210, 20, 420)) == (540, 1170)
for point, bounds in [((1080, 0), (0, 1079, 0, 2339)), ((0, 0), (0, 0, 0, 1))]:
    try:
        mapping.coordinates(*point, bounds)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid calibration accepted")
print("TOUCH_MAPPING_PASS corners=2 offset_bounds=1 rejected=2; synthetic offline only")
