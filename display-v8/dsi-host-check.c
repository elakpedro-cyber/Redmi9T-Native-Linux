// SPDX-License-Identifier: GPL-2.0-only
#include <linux/init.h>
#include <linux/module.h>
#include <linux/of.h>
#include <drm/drm_mipi_dsi.h>

static int __init lemon_dsi_host_check(void)
{
	struct device_node *node;
	bool registered;

	node = of_find_node_by_path("/soc@0/display-subsystem@5e00000/dsi@5e94000");
	if (!node)
		return -ENODEV;

	/* The core looks this up in its registered-host list. */
	registered = of_find_mipi_dsi_host_by_node(node) != NULL;
	of_node_put(node);
	if (!registered)
		return -ENODEV;

	pr_info("lemon-stage-b: DSI0 host registered\n");
	return 0;
}

static void __exit lemon_dsi_host_check_exit(void)
{
}

module_init(lemon_dsi_host_check);
module_exit(lemon_dsi_host_check_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Read-only lemon DSI0 host registration check");
