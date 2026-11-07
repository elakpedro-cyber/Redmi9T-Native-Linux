from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "reports/v8-panel-packets.json").read_text())
standard = {
    0x10: "DCS enter sleep",
    0x11: "DCS exit sleep",
    0x28: "DCS display off",
    0x29: "DCS display on",
    0x35: "DCS tear signal on",
    0x51: "DCS panel brightness payload; keep external HWEN low",
    0x53: "DCS write control display",
    0x55: "DCS write CABC mode",
}

print("sequence	index	DT byte offset	wire type	delay ms	payload	interpretation")
for state in ("on", "off"):
    page = 0x10 if state == "off" else None
    offset = 0
    for index, packet in enumerate(data[state]["packets"], 1):
        payload = bytes.fromhex(packet["payload"])
        command = payload[0]
        if command == 0xff and len(payload) == 2:
            page = payload[1]
            meaning = f"observed vendor page selection 0x{page:02x}"
        elif page == 0x10 and command in standard:
            meaning = standard[command]
        else:
            meaning = "vendor register; semantics unverified"
            if page is not None:
                meaning += f" (page 0x{page:02x})"
        print(f"{state}\t{index}\t{offset}\t{packet['type']:#04x}\t{packet['delay_ms']}\t{payload.hex(' ')}\t{meaning}")
        offset += 7 + len(payload)
