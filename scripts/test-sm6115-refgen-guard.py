from pathlib import Path
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).read_text()
start = source.index("\t/* Review guard: do not probe SM6115")
guard = source[start:source.index("\n\tmsm_host = devm_kzalloc", start)]
test = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#define EPROBE_DEFER 517
struct device_node { bool available; };
struct device { struct device_node *of_node; };
struct platform_device { struct device dev; };
struct regulator {};
static struct device_node supplier;
static struct regulator regulator;
static bool sm6115, has_supplier;
static int get_error, gets, node_puts, regulator_puts;

static bool of_device_is_compatible(struct device_node *node, const char *name)
{ (void)node; return sm6115 && !strcmp(name, "qcom,sm6115-dsi-ctrl"); }
static struct device_node *of_parse_phandle(struct device_node *node, const char *prop, int index)
{ (void)node; assert(!strcmp(prop, "refgen-supply") && index == 0); return has_supplier ? &supplier : 0; }
static bool of_device_is_available(struct device_node *node) { return node->available; }
static void of_node_put(struct device_node *node) { if (node) node_puts++; }
static struct regulator *regulator_get_optional(struct device *dev, const char *name)
{ (void)dev; assert(!strcmp(name, "refgen")); gets++; return get_error ? (void *)(intptr_t)get_error : &regulator; }
static void regulator_put(struct regulator *r) { assert(r == &regulator); regulator_puts++; }
#define IS_ERR(p) ((intptr_t)(p) < 0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define dev_err_probe(dev, error, message) (error)

static int check(struct platform_device *pdev)
{
""" + guard + r"""
    return 0;
}

int main(void)
{
    struct platform_device pdev = {};
    assert(check(&pdev) == 0 && gets == 0);
    sm6115 = true;
    assert(check(&pdev) == -ENODEV && gets == 0);
    has_supplier = true;
    assert(check(&pdev) == -ENODEV && gets == 0 && node_puts == 1);
    supplier.available = true;
    get_error = -EPROBE_DEFER;
    assert(check(&pdev) == -EPROBE_DEFER && gets == 1 && !regulator_puts);
    get_error = -ENODEV;
    assert(check(&pdev) == -ENODEV && gets == 2 && !regulator_puts);
    get_error = 0;
    assert(check(&pdev) == 0 && gets == 3 && regulator_puts == 1);
}
"""

with tempfile.TemporaryDirectory(prefix="lemon-refgen-") as tmp:
    src = Path(tmp) / "test.c"
    exe = src.with_suffix("")
    src.write_text(test)
    subprocess.run(["aarch64-linux-gnu-gcc", "-static", "-Wall", "-Wextra",
                    "-Werror", src, "-o", exe], check=True)
    subprocess.run(["qemu-aarch64-static", exe], check=True, timeout=10)
print("PASS: ARM64 QEMU REFGEN missing/disabled/deferred/unavailable/available and other SoC")

