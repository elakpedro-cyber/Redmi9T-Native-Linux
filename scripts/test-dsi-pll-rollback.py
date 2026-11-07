from pathlib import Path
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).read_text()
prepare = source[source.index("static int dsi_pll_14nm_vco_prepare("):
                 source.index("static void dsi_pll_14nm_vco_unprepare(")]
test = r"""
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#define __iomem
#define unlikely(x) (x)
#define DBG(...) ((void)0)
#define DRM_DEV_ERROR(...) ((void)0)
#define REG_DSI_14nm_PHY_PLL_VREF_CFG1 0
#define REG_DSI_14nm_PHY_CMN_PLL_CNTRL 0
#define VCO_REF_CLK_RATE 19200000
#define POLL_MAX_READS 3
#define POLL_TIMEOUT_US 10
struct cfg { unsigned long min_pll_rate; };
struct phy { bool pll_on; unsigned int *base, *pll_base; struct cfg *cfg; };
struct dsi_pll_14nm { struct phy *phy; };
struct clk_hw { struct dsi_pll_14nm *pll; };
#define to_pll_14nm(hw) ((hw)->pll)
static bool locked;
static unsigned int starts, stops, reads, pll_control;
static void writel(unsigned int value, unsigned int *addr)
{
    if (addr == &pll_control) {
        if (value) starts++; else stops++;
    }
    *addr = value;
}
static unsigned int readl(unsigned int *addr)
{
    reads++;
    return *addr;
}
static unsigned long dsi_pll_14nm_vco_recalc_rate(struct clk_hw *hw, unsigned long rate)
{ (void)hw; return rate; }
static int dsi_pll_14nm_vco_set_rate(struct clk_hw *hw, unsigned long rate, unsigned long parent)
{ (void)hw; (void)rate; (void)parent; return 0; }
static bool pll_14nm_poll_for_ready(struct dsi_pll_14nm *pll, unsigned int reads, unsigned int timeout)
{ (void)pll; (void)reads; (void)timeout; return locked; }
""" + prepare + r"""
int main(void)
{
    unsigned int vref = 0;
    struct cfg cfg = {};
    struct phy phy = { false, &pll_control, &vref, &cfg };
    struct dsi_pll_14nm pll = { &phy };
    struct clk_hw hw = { &pll };
    assert(dsi_pll_14nm_vco_prepare(&hw) == -ETIMEDOUT);
    assert(!phy.pll_on && !pll_control && starts == 1 && stops == 1 && reads == 1);
    locked = true;
    assert(dsi_pll_14nm_vco_prepare(&hw) == 0);
    assert(phy.pll_on && pll_control == 1 && starts == 2 && stops == 1);
    assert(dsi_pll_14nm_vco_prepare(&hw) == 0 && starts == 2);
}
"""
with tempfile.TemporaryDirectory(prefix="lemon-pll-") as tmp:
    src = Path(tmp) / "test.c"
    exe = src.with_suffix("")
    src.write_text(test)
    subprocess.run(["aarch64-linux-gnu-gcc", "-static", "-Wall", "-Wextra",
                    "-Werror", src, "-o", exe], check=True)
    subprocess.run(["qemu-aarch64-static", exe], check=True, timeout=10)
print("PASS: ARM64 QEMU PLL prepare timeout clears PLL control; success and idempotence")

