"""Check that the offline diagnostic image cannot enumerate the display path."""
import argparse
from pathlib import Path

from fdt_audit import Fdt

parser = argparse.ArgumentParser()
parser.add_argument("dtb", type=Path)
parser.add_argument("--handoff", action="store_true")
args = parser.parse_args()

root = Path(__file__).resolve().parents[1]
dt = Fdt(args.dtb)
mdss = "/soc@0/display-subsystem@5e00000"
fb = "/chosen/framebuffer@5c000000"
phy = mdss + "/phy@5e94400"
host = mdss + "/dsi@5e94000"
lcdb = "/soc@0/spmi@1c40000/pmic@3/regulator@ec00"
disabled = {
    fb, mdss, phy, host, mdss + "/display-controller@5e01000", lcdb,
    "/soc@0/clock-controller@5f00000", "/backlight-dsi",
    "/soc@0/geniqup@4ac0000/i2c@4a84000/led-controller@36",
}
for node in disabled:
    assert dt.nodes.get(node, {}).get("status") == b"disabled\0", node
for node, props in dt.nodes.items():
    assert not any(term in props.get("compatible", b"").lower()
                   for term in (b"td4330", b"novatek", b"refgen")), node
    assert not any(part.startswith(("panel@", "touchscreen@")) or part in ("panel", "touchscreen")
                   for part in node.split("/")), node
assert "refgen-supply" not in dt.nodes[host]

domains = dt.cells(dt.nodes[phy]["power-domains"])
opps = dt.cells(dt.nodes[phy]["required-opps"])
assert domains[1:] == [3] and dt.phandles[domains[0]].endswith("/rpm-requests/power-controller")
assert dt.cells(dt.nodes[dt.phandles[opps[0]]]["opp-level"]) == [256]

if not args.handoff:
    baseline = Fdt(root / "artifacts/sm6115-xiaomi-lemon-v8b.dtb").nodes
    assert set(dt.nodes) - set(baseline) == {lcdb, lcdb + "/ldo", lcdb + "/ncp"}
    for node, original in baseline.items():
        expected = dict(original)
        if node in disabled:
            expected["status"] = b"disabled\0"
        if node == phy:
            for key in ("power-domains", "required-opps"):
                expected[key] = dt.nodes[phy][key]
        assert dt.nodes[node] == expected, node
else:
    fixture = Fdt(root / "artifacts/first-light-diagnostic/sm6115-xiaomi-lemon-first-light-diagnostic.dtb")
    # Bootshim updates memory, reservations, and chosen properties. Check the
    # complete peripheral graph that Linux will actually receive.
    for node, props in fixture.nodes.items():
        if node.startswith(("/soc@", "/remoteproc", "/backlight")) or node == fb:
            assert dt.nodes[node] == props, node
print("PASS: disabled display, framebuffer and bias nodes, no panel/touch/REFGEN provider, NOM on disabled PHY")
