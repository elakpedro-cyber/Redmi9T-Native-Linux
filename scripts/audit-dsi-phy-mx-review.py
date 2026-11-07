from pathlib import Path
import sys

from fdt_audit import Fdt

before, review = (Fdt(Path(path)).nodes for path in sys.argv[1:])
phy = "/soc@0/display-subsystem@5e00000/phy@5e94400"
rpm = "/remoteproc/glink-edge/rpm-requests/power-controller"
opp = rpm + "/opp-table/opp5"
assert before.keys() == review.keys()
assert all(review[path] == props for path, props in before.items() if path != phy)
assert before[phy]["status"] == review[phy]["status"] == b"disabled\0"
assert set(review[phy]) - set(before[phy]) == {"power-domains", "required-opps"}
assert all(review[phy][key] == value for key, value in before[phy].items())
assert review[rpm]["compatible"] == b"qcom,sm6115-rpmpd\0"
assert Fdt.cells(review[phy]["power-domains"]) == [Fdt.cells(review[rpm]["phandle"])[0], 3]
assert review[phy]["required-opps"] == review[opp]["phandle"]
assert Fdt.cells(review[opp]["opp-level"]) == [256]
assert not any("refgen-supply" in props for props in review.values())
print("PASS: only disabled PHY changed, SM6115 VDDMX domain 3 and NOM OPP 256")

