from pathlib import Path
from html import unescape
import re
import shutil
import subprocess
import sys
import tempfile

from fdt_audit import Fdt

root = Path(__file__).resolve().parents[1]
work = Path.home() / "Redmi9T-Native-Linux"
source, = work.glob("linux-054*")
logs = root / "logs/v8-stage-c"
tools = work / "v7-python/bin"
base = root / "artifacts/sm6115-xiaomi-lemon-v8b.dtb"
review = logs / "lcdb-review.dtb"
overlay = logs / "lcdb-review.dtbo"


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def mail_additions(name):
    lines = (logs / name).read_text(encoding="utf-8").splitlines()
    return "\n".join(unescape(re.sub("<[^>]+>", "", line[1:]))
                     for line in lines if line.startswith("+") and not line.startswith("+++")) + "\n"


run("dtc", "-@", "-Wno-interrupts_property", "-I", "dts", "-O", "dtb",
    "-o", overlay, root / "display-v8/lcdb-stage-c-review.dts")
run("fdtoverlay", "-i", base, "-o", review, overlay)
native = Fdt(base)
nodes = Fdt(review).nodes
spmi = "/soc@0/spmi@1c40000"
lcdb = spmi + "/pmic@3/regulator@ec00"
assert {path: props for path, props in nodes.items() if path in native.nodes} == native.nodes
assert set(nodes) - set(native.nodes) == {lcdb, lcdb + "/ldo", lcdb + "/ncp"}
assert nodes[lcdb]["status"] == b"disabled\0"
assert native.cells(nodes[lcdb]["interrupts"]) == [3, 0xec, 1, 1]
assert native.cells(nodes[spmi]["#interrupt-cells"]) == [4]
assert "interrupt-controller" in nodes[spmi]
for child in ("ldo", "ncp"):
    for bound in ("min", "max"):
        assert native.cells(nodes[f"{lcdb}/{child}"][f"regulator-{bound}-microvolt"]) == [5500000]
print("PASS: only the disabled LCDB subtree was added; active DT unchanged")

with tempfile.TemporaryDirectory(prefix="lemon-stage-c-") as temp:
    bindings = Path(temp) / "bindings"
    shutil.copytree(source / "Documentation/devicetree/bindings", bindings)
    lcdb_schema = bindings / "regulator/qcom,pm8150l-lcdb.yaml"
    lcdb_schema.write_text(mail_additions("lcdb-binding-mail.html"), encoding="utf-8")
    pmic_schema = bindings / "mfd/qcom,spmi-pmic.yaml"
    old = pmic_schema.read_text(encoding="utf-8")
    assert old.count("\npatternProperties:\n") == 1
    pmic_schema.write_text(old.replace("\npatternProperties:\n", "\npatternProperties:\n" +
                           mail_additions("lcdb-mfd-mail.html")), encoding="utf-8")
    schema = Path(temp) / "processed.json"
    with schema.open("w") as output:
        subprocess.run([tools / "dt-mk-schema", "-j", bindings], check=True, stdout=output)
    result = subprocess.run([tools / "dt-validate", "-s", schema, base, review, *sys.argv[1:]],
                            capture_output=True, text=True, check=True)
    assert not (result.stdout or result.stderr), result.stdout + result.stderr
print("PASS: native and disabled fixture DT match kernel schemas plus LCDB v2 binding patches")

