from pathlib import Path
import hashlib
import html
import json
import re
import struct

from fdt_audit import Fdt

root = Path(__file__).resolve().parents[1]
output = root / "display-v8"
output.mkdir(exist_ok=True)
name = "qcom,mdss_dsi_td4330_truly_v2_video"
trees = [Fdt(root / p) for p in (
    "reports/live.dtb", "reports/v8-android-merged.dtb", "reports/v7-xiaomi-panel.dtb"
)]
prefixes = [next(p for p in t.nodes if p.endswith("/" + name)) for t in trees]
suffix = "/qcom,mdss-dsi-display-timings/timing@0"
live, merged, source = [t.nodes[p + suffix] for t, p in zip(trees, prefixes)]
assert all(live[k] == merged[k] == value for k, value in source.items())
assert name.encode() in trees[0].nodes["/chosen"]["bootargs"]

lines = ["/* Generated from matching Xiaomi source, TWRP FDT and Android overlay 0. */"]
report = {}
for state in ("on", "off"):
    blob = live[f"qcom,mdss-dsi-{state}-command"]
    assert live[f"qcom,mdss-dsi-{state}-command-state"] == b"dsi_lp_mode\0"
    offset = 0
    packets = []
    lines.append(f"static const struct td4330_packet td4330_{state}[] = {{")
    while offset < len(blob):
        kind, last, channel, ack, delay, length = struct.unpack_from(">BBBBBH", blob, offset)
        offset += 7
        assert (last, channel, ack) == (1, 0, 0)
        assert (kind == 0x05 and length == 2) or (kind == 0x39 and 2 <= length <= 4)
        payload = blob[offset:offset + length]
        assert len(payload) == length
        offset += length
        data = ", ".join(f"0x{byte:02x}" for byte in payload)
        lines.append(f"\t{{ 0x{kind:02x}, {delay}, {length}, {{ {data} }} }},")
        packets.append({"type": kind, "delay_ms": delay, "payload": payload.hex()})
    lines.append("};")
    report[state] = {"sha256": hashlib.sha256(blob).hexdigest(), "packets": packets}
assert [len(report[s]["packets"]) for s in ("on", "off")] == [77, 2]
(output / "td4330-packets.h").write_text("\n".join(lines) + "\n", newline="\n")
(root / "reports/v8-panel-packets.json").write_text(json.dumps(report, indent=2) + "\n")

archive = (root / "reports/v8-lcdb-source-0.html").read_text(encoding="utf-8")
patch = archive.split("+++ b/drivers/regulator/qcom-lcdb-regulator.c\n", 1)[1]
source_lines = [html.unescape(line[1:]) for line in patch.split("\n-- \n", 1)[0].splitlines()
                if line.startswith("+")]
assert len(source_lines) == 494
assert re.search(r'MODULE_LICENSE\("GPL"\);', "\n".join(source_lines))
(output / "qcom-lcdb-regulator.c").write_text("\n".join(source_lines) + "\n", newline="\n")
print("PASS: 77 init and 2 shutdown packets match three DT inputs; 494 LCDB source lines extracted")
