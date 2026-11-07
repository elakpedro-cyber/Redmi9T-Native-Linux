from pathlib import Path
import sys

from fdt_audit import Fdt

tree = Fdt(Path(sys.argv[1]))
nodes = tree.nodes
soc = "/soc@0"
mdss = soc + "/display-subsystem@5e00000"
dpu = mdss + "/display-controller@5e01000"
dsi = mdss + "/dsi@5e94000"
phy = mdss + "/phy@5e94400"
lcdb = soc + "/spmi@1c40000/pmic@3/regulator@ec00"
dispcc = soc + "/clock-controller@5f00000"
backlight_ic = soc + "/geniqup@4ac0000/i2c@4a84000/led-controller@36"
for node in (dispcc, mdss, dpu, dsi, phy, lcdb, backlight_ic, "/backlight-dsi"):
    if nodes[node].get("status") != b"disabled\0":
        raise SystemExit(f"unsafe review fixture: {node}")
    print(f"disabled {node}")

def check(condition, message):
    if not condition:
        raise SystemExit(message)
    print(message)

in_port = dsi + "/ports/port@0/endpoint"
out_port = dpu + "/ports/port@0/endpoint"
panel_port = dsi + "/ports/port@1/endpoint"
check(nodes[in_port]["remote-endpoint"] == nodes[out_port]["phandle"] and
      nodes[out_port]["remote-endpoint"] == nodes[in_port]["phandle"], "PASS: reciprocal DPU/DSI endpoints")
check(nodes[dsi]["phys"] == nodes[phy]["phandle"], "PASS: DSI uses the 14nm PHY node")
check(Fdt.cells(nodes[panel_port]["data-lanes"]) == [0, 1, 2, 3] and
      "remote-endpoint" not in nodes[panel_port], "PASS: four DSI lanes; no panel endpoint")
check("refgen-supply" not in nodes[dsi], "PASS: fixture makes no unverified REFGEN assignment")
check(not any(b"novatek," in props.get("compatible", b"") for props in nodes.values()),
      "PASS: no Novatek consumer in the fixture")

providers = {Fdt.cells(props["phandle"])[0]: path
             for path, props in nodes.items() if "phandle" in props}

def references(node, key, arg_cells):
    cells = Fdt.cells(nodes[node][key])
    result = []
    while cells:
        provider = providers[cells[0]]
        count, = Fdt.cells(nodes[provider][arg_cells])
        if len(cells) <= count:
            raise SystemExit(f"truncated {node} {key} specifier")
        result.append((provider, cells[1:1 + count]))
        cells = cells[1 + count:]
    return result

for node in (dispcc, mdss, dpu, dsi, phy):
    clocks = references(node, "clocks", "#clock-cells")
    if "clock-names" in nodes[node]:
        names = nodes[node]["clock-names"].rstrip(b"\0").split(b"\0")
        check(len(clocks) == len(names), f"PASS: {node} clocks/name count")
    print(f"{node} clocks: {clocks}")
    if "power-domains" in nodes[node]:
        print(f"{node} domains: {references(node, 'power-domains', '#power-domain-cells')}")
check(references(dsi, "assigned-clock-parents", "#clock-cells") == [(phy, [0]), (phy, [1])],
      "PASS: byte and pixel clock parents are PHY outputs 0/1")
vdda, = Fdt.cells(nodes[dsi]["vdda-supply"])
rail = providers[vdda]
check(rail.endswith("/l18") and
      nodes[rail.rsplit("/", 1)[0]]["compatible"] == b"qcom,rpm-pm6125-regulators\0" and
      Fdt.cells(nodes[rail]["regulator-min-microvolt"]) == [1232000] and
      Fdt.cells(nodes[rail]["regulator-max-microvolt"]) == [1232000],
      "PASS: DSI VDDA refers to the PM6125 L18 rail")
check(Fdt.cells(nodes[backlight_ic]["reg"]) == [0x36] and
      Fdt.cells(nodes[backlight_ic]["enable-gpios"])[1:] == [99, 0],
      "PASS: disabled LM36923 candidate at 0x36, GPIO99 active high")
