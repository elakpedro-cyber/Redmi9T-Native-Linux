from pathlib import Path
import hashlib
import json
import struct

from fdt_audit import Fdt

root = Path(__file__).resolve().parents[1]
artifacts = root / "artifacts"
reports = root / "reports"
mdss = "/soc@0/display-subsystem@5e00000"
providers = (
    "/soc@0/clock-controller@5f00000",
    mdss,
    mdss + "/dsi@5e94000",
    mdss + "/phy@5e94400",
)
baseline = Fdt(artifacts / "sm6115-xiaomi-lemon-v8.dtb").nodes
for path in providers:
    baseline[path]["status"] = b"okay\0"
del baseline[mdss]["resets"]
assert Fdt(artifacts / "sm6115-xiaomi-lemon-v8b.dtb").nodes == baseline
assert not (reports / "v8b-native-schema.txt").read_bytes()

handoff = Fdt(reports / "emulated-mainline-v8b.dtb").nodes
assert "resets" not in handoff[mdss]
for path in providers:
    assert handoff[path]["status"] == b"okay\0"
assert handoff[mdss + "/display-controller@5e01000"]["status"] == b"disabled\0"
assert handoff["/backlight-dsi"]["status"] == b"disabled\0"
assert not any("/panel@" in path or b"lcdb" in properties.get("compatible", b"") or
               b"novatek," in properties.get("compatible", b"") for path, properties in handoff.items())

config = (root / "config/linux-v8b.config").read_text().splitlines()
for line in ("CONFIG_SM_DISPCC_6115=m", "CONFIG_DRM_MSM=m", "CONFIG_DRM_SIMPLEDRM=y",
             "CONFIG_DRM_MIPI_DSI=y", "CONFIG_USB_CONFIGFS_NCM=y",
             "CONFIG_USB_CONFIGFS_ACM=y", "CONFIG_SCSI_UFS_QCOM=y"):
    assert line in config, line
image = (artifacts / "Image-v8b").read_bytes()
assert len(image) <= struct.unpack_from("<Q", image, 16)[0] <= 32 * 1024 * 1024
emulation = json.loads((reports / "bootshim-v8b-emulation.json").read_text())
assert emulation["status"] == "PASS_OFFLINE_ONLY" and len(emulation["cases"]) == 15
assert sum("native_entry" in case for case in emulation["cases"]) == 8
boot = artifacts / "boot-linux-test-v8b.img"
print("PASS Stage B DT, schema, modular clocks/MSM, bootshim placement and handoff")
print(boot.stat().st_size, hashlib.sha256(boot.read_bytes()).hexdigest())
