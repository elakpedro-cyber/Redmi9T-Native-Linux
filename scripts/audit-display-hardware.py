from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess
import sys
import tempfile

from fdt_audit import Fdt

root = Path(__file__).resolve().parents[1]
backup = root.parent / "platform-tools/Redmi9T_Backup"
manifest = json.loads((root / "reports/backup-sha256-before.json").read_text())
results = {}
for filename, expected in manifest.items():
    image = backup / filename
    with image.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assert {"size": image.stat().st_size, "sha256": digest} == expected, image
    results[filename] = expected

dtbo = (backup / "dtbo.img").read_bytes()
magic, total, header, stride, count, entries, page, version = struct.unpack_from(">8I", dtbo)
assert magic == 0xd7b7ab1e and header == stride == 32 and entries == header
assert count == 1 and entries + count * stride <= total <= len(dtbo)
length, offset, ident, rev, *custom = struct.unpack_from(">8I", dtbo, entries)
assert entries + stride <= offset < offset + length <= total
payload = dtbo[offset:offset + length]
assert payload == (root / "reports/stock-overlay-0.dtbo").read_bytes()
results["dtbo_table"] = dict(count=count, entry_id=ident, entry_rev=rev, custom=custom,
                             table_bytes=total, entry_bytes=length, page=page, version=version)

with tempfile.TemporaryDirectory(prefix="lemon-display-evidence-") as tmp:
    tmp = Path(tmp)
    subprocess.run([sys.executable, root / "tools/unpack_bootimg.py", "--boot_img",
                    backup / "boot.img", "--out", tmp], check=True, capture_output=True)
    dtb = tmp / "dtb"
    assert dtb.read_bytes() == (root / "reports/stock-boot/dtb").read_bytes()
    overlay = tmp / "overlay.dtbo"
    overlay.write_bytes(payload)
    merged = tmp / "merged.dtb"
    subprocess.run(["fdtoverlay", "-i", dtb, "-o", merged, overlay], check=True)
    assert Fdt(merged).nodes == Fdt(root / "reports/stock-overlay-result.dtb").nodes
    trees = {
        "original_boot": Fdt(dtb),
        "original_overlay": Fdt(overlay),
        "original_merge": Fdt(merged),
        "archived_twrp": Fdt(root / "reports/live.dtb"),
    }

panel = "qcom,mdss_dsi_td4330_truly_v2_video"
assert panel.encode() in trees["archived_twrp"].nodes["/chosen"]["bootargs"]
results["twrp_selected_panel"] = panel
for name, tree in trees.items():
    results[name] = {key: tree.cells(tree.nodes["/"][key])
                     for key in ("qcom,board-id", "qcom,msm-id")
                     if key in tree.nodes["/"]}

def describe(tree):
    supplies = {}
    providers = {tree.cells(props["phandle"])[0]: path
                 for path, props in tree.nodes.items() if "phandle" in props}
    for path in ("/soc/qcom,dsi-display-primary", "/soc/qcom,mdss_dsi0_ctrl",
                 "/soc/qcom,mdss_dsi_phy0", "/soc/qcom,mdss_dsi0_pll"):
        supplies[path] = {}
        for key, value in tree.nodes[path].items():
            if key.endswith("-supply"):
                phandle, = tree.cells(value)
                target = providers[phandle]
                props = tree.nodes[target]
                supplies[path][key] = {"provider": target,
                    "name": props.get("regulator-name", b"").rstrip(b"\0").decode()}
    return supplies

stock = trees["original_merge"]
live = trees["archived_twrp"]
results["stock_display_supplies"] = describe(stock)
assert results["stock_display_supplies"] == describe(live)
phy_supply = results["stock_display_supplies"]["/soc/qcom,mdss_dsi_phy0"]["vdda-0p9-supply"]
phy_rail = phy_supply["provider"]
assert "qcom,use-voltage-level" in stock.nodes[phy_rail]
phy_resource = stock.nodes[phy_rail.rsplit("/", 1)[0]]
results["phy_rpm_resource"] = [phy_resource["qcom,resource-name"].rstrip(b"\0").decode(),
                              stock.cells(phy_resource["qcom,resource-id"])[0]]
phy_entry = stock.nodes["/soc/qcom,mdss_dsi_phy0/qcom,phy-supply-entries/qcom,phy-supply-entry@0"]
results["stock_phy_level_values"] = [stock.cells(phy_entry[f"qcom,supply-{field}-voltage"])[0]
                                     for field in ("min", "max", "off-min")]
ctrl = "/soc/qcom,mdss_dsi0_ctrl"
for tree in (stock, live):
    assert not any("refgen-supply" in props for props in tree.nodes.values())
    entry = tree.nodes[ctrl + "/qcom,core-supply-entries/qcom,core-supply-entry@0"]
    assert entry["qcom,supply-name"] == b"refgen\0"
    assert all(tree.cells(entry[f"qcom,supply-{field}"]) == [0] for field in
               ("min-voltage", "max-voltage", "enable-load", "disable-load"))
results["refgen"] = "Stock and TWRP name the consumer without a supplier"
v8b = Fdt(root / "artifacts/sm6115-xiaomi-lemon-v8b.dtb")
phy = v8b.nodes["/soc@0/display-subsystem@5e00000/phy@5e94400"]
assert "power-domains" not in phy and not any(k.endswith("-supply") for k in phy)
results["v8b_phy"] = "No explicit power domain or regulator on the PHY node"
pattern = r"buf\[\d\]=0x([0-9A-Fa-f]{2})"
for version in ("v7", "v8"):
    log = (root / f"logs/{version}-authorized/twrp-dmesg-before.txt").read_text()
    trim_line, = [line for line in log.splitlines() if "nvt_ts_check_chip_ver_trim" in line and "buf[1]=" in line]
    trim = re.findall(pattern, trim_line)
    assert trim == ["0A", "00", "00", "72", "66", "03"]
    assert re.search(r"nvt_read_pid \d+: PID=5940\b", log)
    assert "[TP-IC]NT36672A, [FW]Ver :5" in log
results["archived_novatek"] = {"trim": trim, "project_id": "0x5940", "driver_model": "NT36672A", "fw": 5}
print(json.dumps(results, indent=2))

