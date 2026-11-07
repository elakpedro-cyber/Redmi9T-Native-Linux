"""Check the pinned source ordering and illustrate vote aggregation offline."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
kernel, = (Path.home() / "Redmi9T-Native-Linux").glob("linux-054*")

def block(path, start, end):
    source = path.read_text()
    begin = source.index(start)
    return source[begin:source.index(end, begin + len(start))]

def ordered(code, *calls):
    offset = 0
    for call in calls:
        offset = code.index(call, offset) + len(call)

stock = block(root / "downloads/v8-xiaomi-source/techpack/display/msm/dsi/dsi_pwr.c",
              "static int dsi_pwr_enable_vregs(", "error_disable_opt_mode:")
ordered(stock, "vreg->min_voltage", "regulator_enable(")
off = stock[stock.index("if (regs->vregs[i].off_min_voltage)"):]
ordered(off, "regulator_set_voltage(", "regulator_disable(")

phy = kernel / "drivers/gpu/drm/msm/dsi/phy/dsi_phy.c"
ordered(block(phy, "void msm_dsi_phy_disable(", "void msm_dsi_phy_set_usecase("),
        "phy->cfg->ops.disable(phy)", "regulator_bulk_disable(", "pm_runtime_put(")
ordered(block(phy, "int msm_dsi_phy_enable(", "void msm_dsi_phy_disable("),
        "pm_runtime_resume_and_get(", "phy->cfg->ops.enable(phy, clk_req)")

core = kernel / "drivers/pmdomain/core.c"
ordered(block(core, "static int genpd_runtime_suspend(struct device *dev)\n{",
              "static int genpd_runtime_resume(struct device *dev)\n{"),
        "__genpd_runtime_suspend(dev)", "genpd_stop_dev(genpd, dev)",
        "genpd_power_off(genpd, true, 0)", "genpd_drop_performance_state(dev)")
assert "genpd_set_performance_state(dev, 0)" in block(
    core, "static int genpd_drop_performance_state(", "static void genpd_restore_performance_state(")
ordered(block(core, "static int genpd_runtime_resume(struct device *dev)\n{",
              "static bool pd_ignore_unused"),
        "genpd_restore_performance_state(dev", "genpd_power_on(genpd", "genpd_start_dev(genpd")
rpm = kernel / "drivers/pmdomain/qcom/rpmpd.c"
ordered(block(rpm, "static int rpmpd_power_on(", "static int rpmpd_power_off("),
        "rpmpd_send_enable(pd, true)", "rpmpd_aggregate_corner(pd)")

print("PASS: stock request order, PHY shutdown, genpd suspend/resume and RPM enable verified in pinned source")
print("Illustration only: local vote / possible aggregate by max; 0 is no PHY performance vote, not 0 V")
for other, expected in [(0, (256, 16, 0)), (16, (256, 16, 16)),
                        (256, (256, 256, 256)), (320, (320, 320, 320))]:
    values = tuple(max(other, level) for level in (256, 16, 0))
    assert values == expected
    print(f"other vote={other}: active={values[0]} stock pre-off={values[1]} genpd dropped={values[2]}")
print("PASS: no other consumer exposes the 16-vs-0 difference; stronger consumers can mask it")

