// SPDX-License-Identifier: GPL-2.0-only
/*
 * Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
 * Experimental lemon safety variant. Offline review only.
 */

#include <linux/bits.h>
#include <linux/delay.h>
#include <linux/interrupt.h>
#include <linux/ktime.h>
#include <linux/minmax.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/pm.h>
#include <linux/property.h>
#include <linux/regmap.h>
#include <linux/regulator/driver.h>
#include <linux/regulator/of_regulator.h>

#define LCDB_INT_RT_STS			0x10
#define  LCDB_VREG_OK_RT_STS		BIT(0)
#define  LCDB_SC_ERROR_RT_STS		BIT(1)

#define LCDB_BST_OUTPUT_VOLTAGE		0x41
#define  LCDB_BST_OUTPUT_VOLTAGE_MASK	GENMASK(5, 0)

#define LCDB_MODULE_RDY			0x45
#define  LCDB_MODULE_RDY_BIT		BIT(7)

#define LCDB_ENABLE_CTL1		0x46
#define  LCDB_MODULE_EN			BIT(7)

#define LCDB_LDO_OUTPUT_VOLTAGE		0x71
#define LCDB_LDO_FORCE_PD_CTL		0x79
#define  LCDB_LDO_FORCE_PD_EN		BIT(0)
#define  LCDB_LDO_FORCE_PD_MODE		BIT(7)

#define LCDB_NCP_OUTPUT_VOLTAGE		0x81

#define LCDB_OUTPUT_VOLTAGE_MASK	GENMASK(4, 0)

#define LCDB_MIN_UV			4000000
#define LCDB_STEP_100MV_UV		100000
#define LCDB_50MV_MIN_UV		4950000
#define LCDB_STEP_50MV_UV		50000
#define LCDB_50MV_MIN_SEL		10
#define LCDB_N_VOLTAGES			32

#define LCDB_BST_MIN_UV			4700000
#define LCDB_BST_MAX_UV			6275000
#define LCDB_BST_STEP_UV		25000
#define LCDB_BST_HEADROOM_UV		150000

#define LCDB_RAMP_START_UV		4500000
#define LCDB_RAMP_STEP_UV		500000

#define LCDB_OFF_ON_DELAY_US		20000
#define LCDB_VREG_OK_TIMEOUT_US		50000


enum {
	LCDB_LDO,
	LCDB_NCP,
	LCDB_NUM_RAILS,
};

enum lcdb_state {
	LCDB_UNKNOWN,
	LCDB_DISABLED,
	LCDB_ENABLED,
	LCDB_TRANSITIONING,
	LCDB_FAULT,
};

struct qcom_lcdb {
	struct device *dev;
	struct regmap *regmap;
	u32 base;

	struct mutex lock;
	struct regulator_dev *rdev[LCDB_NUM_RAILS];
	int uV[LCDB_NUM_RAILS];
	unsigned int enabled_mask;
	ktime_t off_time;

	enum lcdb_state state;
	bool armed;
	bool suspended;
};

static const u8 qcom_lcdb_vreg[LCDB_NUM_RAILS] = {
	[LCDB_LDO] = LCDB_LDO_OUTPUT_VOLTAGE,
	[LCDB_NCP] = LCDB_NCP_OUTPUT_VOLTAGE,
};

static unsigned int qcom_lcdb_uV_to_sel(int uV)
{
	if (uV < LCDB_50MV_MIN_UV)
		return (uV - LCDB_MIN_UV) / LCDB_STEP_100MV_UV;

	return LCDB_50MV_MIN_SEL + (uV - LCDB_50MV_MIN_UV) / LCDB_STEP_50MV_UV;
}

static int qcom_lcdb_sel_to_uV(unsigned int sel)
{
	if (sel < LCDB_50MV_MIN_SEL)
		return LCDB_MIN_UV + sel * LCDB_STEP_100MV_UV;

	return LCDB_50MV_MIN_UV + (sel - LCDB_50MV_MIN_SEL) * LCDB_STEP_50MV_UV;
}

static int qcom_lcdb_write_voltages(struct qcom_lcdb *lcdb, int ldo_uV, int ncp_uV)
{
	const int uV[LCDB_NUM_RAILS] = { ldo_uV, ncp_uV };
	unsigned int bst_sel, cur_sel;
	int bst_uV, ret, i;

	bst_uV = clamp(max(ldo_uV, ncp_uV) + LCDB_BST_HEADROOM_UV,
		       LCDB_BST_MIN_UV, LCDB_BST_MAX_UV);
	bst_sel = DIV_ROUND_UP(bst_uV - LCDB_BST_MIN_UV, LCDB_BST_STEP_UV);

	ret = regmap_read(lcdb->regmap, lcdb->base + LCDB_BST_OUTPUT_VOLTAGE, &cur_sel);
	if (ret)
		return ret;
	cur_sel &= LCDB_BST_OUTPUT_VOLTAGE_MASK;

	/* The boost has to stay above both outputs while they are changing */
	if (bst_sel > cur_sel) {
		ret = regmap_update_bits(lcdb->regmap,
					 lcdb->base + LCDB_BST_OUTPUT_VOLTAGE,
					 LCDB_BST_OUTPUT_VOLTAGE_MASK, bst_sel);
		if (ret)
			return ret;
	}

	for (i = 0; i < LCDB_NUM_RAILS; i++) {
		ret = regmap_update_bits(lcdb->regmap,
					 lcdb->base + qcom_lcdb_vreg[i],
					 LCDB_OUTPUT_VOLTAGE_MASK,
					 qcom_lcdb_uV_to_sel(uV[i]));
		if (ret)
			return ret;
	}

	if (bst_sel < cur_sel)
		ret = regmap_update_bits(lcdb->regmap,
					 lcdb->base + LCDB_BST_OUTPUT_VOLTAGE,
					 LCDB_BST_OUTPUT_VOLTAGE_MASK, bst_sel);

	return ret;
}

static int qcom_lcdb_write_limited(struct qcom_lcdb *lcdb, int limit_uV)
{
	return qcom_lcdb_write_voltages(lcdb,
					min(lcdb->uV[LCDB_LDO], limit_uV),
					min(lcdb->uV[LCDB_NCP], limit_uV));
}

/* Caller holds lock. Software control readback does not measure either rail. */
static int qcom_lcdb_read_gate(struct qcom_lcdb *lcdb, bool enabled, bool reject_sc)
{
	unsigned int control, status;
	int ret;

	ret = regmap_read(lcdb->regmap, lcdb->base + LCDB_ENABLE_CTL1, &control);
	if (ret)
		return ret;
	ret = regmap_read(lcdb->regmap, lcdb->base + LCDB_INT_RT_STS, &status);
	if (ret)
		return ret;
	if (!!(control & LCDB_MODULE_EN) != enabled ||
	    !!(status & LCDB_VREG_OK_RT_STS) != enabled ||
	    (reject_sc && (status & LCDB_SC_ERROR_RT_STS)))
		return -EIO;
	return 0;
}

static int qcom_lcdb_check_off(struct qcom_lcdb *lcdb)
{
	unsigned int pd;
	int ret;

	ret = qcom_lcdb_read_gate(lcdb, false, true);
	if (ret)
		return ret;
	ret = regmap_read(lcdb->regmap, lcdb->base + LCDB_LDO_FORCE_PD_CTL, &pd);
	if (ret)
		return ret;
	return pd & (LCDB_LDO_FORCE_PD_EN | LCDB_LDO_FORCE_PD_MODE) ? -EIO : 0;
}

static int qcom_lcdb_module_disable(struct qcom_lcdb *lcdb)
{
	unsigned int pd;
	int pd_on, off, verify, pd_off, pd_verify;

	lockdep_assert_held(&lcdb->lock);
	lcdb->state = LCDB_TRANSITIONING;
	pd_on = regmap_write(lcdb->regmap, lcdb->base + LCDB_LDO_FORCE_PD_CTL,
			     LCDB_LDO_FORCE_PD_EN | LCDB_LDO_FORCE_PD_MODE);
	/* Always request off. This fallback needs PMI632 validation before use. */
	off = regmap_write(lcdb->regmap, lcdb->base + LCDB_ENABLE_CTL1, 0);
	usleep_range(10000, 11000);
	pd_off = regmap_write(lcdb->regmap, lcdb->base + LCDB_LDO_FORCE_PD_CTL, 0);
	verify = qcom_lcdb_read_gate(lcdb, false, false);
	pd_verify = regmap_read(lcdb->regmap, lcdb->base + LCDB_LDO_FORCE_PD_CTL, &pd);
	if (!pd_verify && (pd & (LCDB_LDO_FORCE_PD_EN | LCDB_LDO_FORCE_PD_MODE)))
		pd_verify = -EIO;
	if (pd_on || off || pd_off || verify || pd_verify) {
		lcdb->state = LCDB_UNKNOWN;
		dev_err(lcdb->dev, "shutdown unconfirmed: pull-down=%d off=%d release=%d readback=%d pd_readback=%d\n",
			pd_on, off, pd_off, verify, pd_verify);
		return pd_on ?: off ?: pd_off ?: verify ?: pd_verify;
	}

	lcdb->off_time = ktime_get();
	lcdb->state = LCDB_DISABLED;
	return 0;
}

static void qcom_lcdb_fault(struct qcom_lcdb *lcdb, int cause)
{
	lockdep_assert_held(&lcdb->lock);
	dev_err(lcdb->dev, "LCDB fault: %d; automatic restart blocked\n", cause);
	if (!qcom_lcdb_module_disable(lcdb))
		lcdb->state = LCDB_FAULT;
}

static int qcom_lcdb_module_enable(struct qcom_lcdb *lcdb)
{
	int target_uV = max(lcdb->uV[LCDB_LDO], lcdb->uV[LCDB_NCP]);
	int uV = LCDB_RAMP_START_UV;
	unsigned int val;
	s64 off_us;
	int ret;

	off_us = ktime_us_delta(ktime_get(), lcdb->off_time);
	if (off_us < LCDB_OFF_ON_DELAY_US)
		usleep_range(LCDB_OFF_ON_DELAY_US - off_us,
			     LCDB_OFF_ON_DELAY_US - off_us + 1000);

	ret = regmap_set_bits(lcdb->regmap, lcdb->base + LCDB_MODULE_RDY,
			      LCDB_MODULE_RDY_BIT);
	if (ret)
		return ret;

	/* Start low and ramp the outputs up in steps to limit the inrush current */
	ret = qcom_lcdb_write_limited(lcdb, uV);
	if (ret)
		return ret;

	ret = regmap_write(lcdb->regmap, lcdb->base + LCDB_ENABLE_CTL1,
			   LCDB_MODULE_EN);
	if (ret)
		return ret;

	ret = regmap_read_poll_timeout(lcdb->regmap,
				       lcdb->base + LCDB_INT_RT_STS, val,
				       val & (LCDB_VREG_OK_RT_STS | LCDB_SC_ERROR_RT_STS),
				       1000, LCDB_VREG_OK_TIMEOUT_US);
	if (ret) {
		dev_err(lcdb->dev, "outputs failed to come up: %d\n", ret);
		return ret;
	}

	if (val & LCDB_SC_ERROR_RT_STS)
		return -EIO;

	usleep_range(10000, 11000);

	while (uV < target_uV) {
		ret = qcom_lcdb_read_gate(lcdb, true, true);
		if (ret)
			return ret;
		uV += LCDB_RAMP_STEP_UV;

		ret = qcom_lcdb_write_limited(lcdb, uV);
		if (ret)
			return ret;

		usleep_range(1000, 1100);
	}

	return qcom_lcdb_read_gate(lcdb, true, true);
}

static int qcom_lcdb_check_state(struct qcom_lcdb *lcdb)
{
	int ret;

	lockdep_assert_held(&lcdb->lock);
	if (lcdb->state != LCDB_DISABLED && lcdb->state != LCDB_ENABLED)
		return -EIO;

	ret = lcdb->state == LCDB_ENABLED ? qcom_lcdb_read_gate(lcdb, true, true) :
		qcom_lcdb_check_off(lcdb);
	if (ret) {
		if (lcdb->state == LCDB_ENABLED)
			qcom_lcdb_fault(lcdb, ret);
		else
			/* A gate we did not enable may belong to firmware. */
			lcdb->state = LCDB_UNKNOWN;
	}
	return ret;
}

static int qcom_lcdb_enable(struct regulator_dev *rdev)
{
	struct qcom_lcdb *lcdb = rdev_get_drvdata(rdev);
	int ret;

	guard(mutex)(&lcdb->lock);
	if (!lcdb->armed)
		return -EAGAIN;
	if (lcdb->suspended)
		return -EBUSY;
	ret = qcom_lcdb_check_state(lcdb);
	if (ret)
		return ret;
	if (lcdb->state == LCDB_DISABLED) {
		lcdb->state = LCDB_TRANSITIONING;
		ret = qcom_lcdb_module_enable(lcdb);
		if (ret) {
			qcom_lcdb_fault(lcdb, ret);
			return ret;
		}
		lcdb->state = LCDB_ENABLED;
	}

	lcdb->enabled_mask |= BIT(rdev_get_id(rdev));
	return 0;
}

static int qcom_lcdb_disable(struct regulator_dev *rdev)
{
	struct qcom_lcdb *lcdb = rdev_get_drvdata(rdev);
	unsigned int bit = BIT(rdev_get_id(rdev));
	unsigned int mask;
	int ret;

	guard(mutex)(&lcdb->lock);
	if (lcdb->state == LCDB_UNKNOWN || lcdb->state == LCDB_TRANSITIONING)
		return -EIO;
	if (!(lcdb->enabled_mask & bit))
		return 0;
	mask = lcdb->enabled_mask & ~bit;
	if (lcdb->state == LCDB_ENABLED) {
		ret = qcom_lcdb_check_state(lcdb);
		if (ret)
			return ret;
		if (!mask) {
			ret = qcom_lcdb_module_disable(lcdb);
			if (ret)
				return ret;
		}
	}
	lcdb->enabled_mask = mask;
	return 0;
}

static int qcom_lcdb_is_enabled(struct regulator_dev *rdev)
{
	struct qcom_lcdb *lcdb = rdev_get_drvdata(rdev);

	guard(mutex)(&lcdb->lock);
	switch (lcdb->state) {
	case LCDB_DISABLED:
	case LCDB_FAULT:
		return 0;
	case LCDB_ENABLED:
		return !!(lcdb->enabled_mask & BIT(rdev_get_id(rdev)));
	default:
		return -EIO;
	}
}

static int qcom_lcdb_set_voltage_sel(struct regulator_dev *rdev, unsigned int sel)
{
	struct qcom_lcdb *lcdb = rdev_get_drvdata(rdev);
	int id = rdev_get_id(rdev);
	int uV;

	if (sel >= LCDB_N_VOLTAGES)
		return -EINVAL;
	uV = qcom_lcdb_sel_to_uV(sel);

	guard(mutex)(&lcdb->lock);
	if (lcdb->state != LCDB_DISABLED && lcdb->state != LCDB_ENABLED)
		return -EIO;
	if (lcdb->state == LCDB_ENABLED)
		return uV == lcdb->uV[id] ? 0 : -EBUSY;
	if (lcdb->suspended)
		return -EBUSY;
	/* Stage both settings before the first consumer enables the shared gate. */
	lcdb->uV[id] = uV;
	return 0;
}

static int qcom_lcdb_get_voltage_sel(struct regulator_dev *rdev)
{
	struct qcom_lcdb *lcdb = rdev_get_drvdata(rdev);

	guard(mutex)(&lcdb->lock);
	if (lcdb->state != LCDB_DISABLED && lcdb->state != LCDB_ENABLED)
		return -EIO;
	return qcom_lcdb_uV_to_sel(lcdb->uV[rdev_get_id(rdev)]);
}

static const struct regulator_ops qcom_lcdb_ops = {
	.enable			= qcom_lcdb_enable,
	.disable		= qcom_lcdb_disable,
	.is_enabled		= qcom_lcdb_is_enabled,
	.set_voltage_sel	= qcom_lcdb_set_voltage_sel,
	.get_voltage_sel	= qcom_lcdb_get_voltage_sel,
	.list_voltage		= regulator_list_voltage_linear_range,
	.map_voltage		= regulator_map_voltage_linear_range,
};

static const struct linear_range qcom_lcdb_ranges[] = {
	REGULATOR_LINEAR_RANGE(LCDB_MIN_UV, 0, LCDB_50MV_MIN_SEL - 1,
			       LCDB_STEP_100MV_UV),
	REGULATOR_LINEAR_RANGE(LCDB_50MV_MIN_UV, LCDB_50MV_MIN_SEL,
			       LCDB_N_VOLTAGES - 1, LCDB_STEP_50MV_UV),
};

static const struct regulator_desc qcom_lcdb_descs[LCDB_NUM_RAILS] = {
	[LCDB_LDO] = {
		.name			= "lcdb_ldo",
		.of_match		= "ldo",
		.id			= LCDB_LDO,
		.ops			= &qcom_lcdb_ops,
		.type			= REGULATOR_VOLTAGE,
		.linear_ranges		= qcom_lcdb_ranges,
		.n_linear_ranges	= ARRAY_SIZE(qcom_lcdb_ranges),
		.n_voltages		= LCDB_N_VOLTAGES,
		.owner			= THIS_MODULE,
	},
	[LCDB_NCP] = {
		.name			= "lcdb_ncp",
		.of_match		= "ncp",
		.id			= LCDB_NCP,
		.ops			= &qcom_lcdb_ops,
		.type			= REGULATOR_VOLTAGE,
		.linear_ranges		= qcom_lcdb_ranges,
		.n_linear_ranges	= ARRAY_SIZE(qcom_lcdb_ranges),
		.n_voltages		= LCDB_N_VOLTAGES,
		.owner			= THIS_MODULE,
	},
};

static bool qcom_lcdb_handle_irq(struct qcom_lcdb *lcdb)
{
	unsigned int status;
	int ret;

	guard(mutex)(&lcdb->lock);
	if (lcdb->state != LCDB_ENABLED)
		return false;

	ret = regmap_read(lcdb->regmap, lcdb->base + LCDB_INT_RT_STS, &status);
	if (!ret && (status & LCDB_VREG_OK_RT_STS) &&
	    !(status & LCDB_SC_ERROR_RT_STS))
		return false;
	qcom_lcdb_fault(lcdb, ret ?: -EIO);
	return true;
}

static irqreturn_t qcom_lcdb_sc_irq(int irq, void *data)
{
	struct qcom_lcdb *lcdb = data;
	int i;

	if (qcom_lcdb_handle_irq(lcdb)) {
		for (i = 0; i < LCDB_NUM_RAILS; i++)
			regulator_notifier_call_chain(lcdb->rdev[i],
						      REGULATOR_EVENT_FAIL, NULL);
	}

	return IRQ_HANDLED;
}

static int qcom_lcdb_suspend_off(struct qcom_lcdb *lcdb)
{
	int ret;

	guard(mutex)(&lcdb->lock);
	if (lcdb->state != LCDB_DISABLED || lcdb->enabled_mask)
		return -EBUSY;
	ret = qcom_lcdb_check_state(lcdb);
	if (!ret)
		lcdb->suspended = true;
	return ret;
}

static int qcom_lcdb_resume_off(struct qcom_lcdb *lcdb)
{
	int ret;

	guard(mutex)(&lcdb->lock);
	if (!lcdb->suspended)
		return 0;
	ret = qcom_lcdb_check_state(lcdb);
	lcdb->suspended = false;
	return ret;
}

static int qcom_lcdb_hw_init(struct qcom_lcdb *lcdb)
{
	unsigned int val;
	int i, ret;

	ret = qcom_lcdb_check_off(lcdb);
	if (ret)
		return ret;

	for (i = 0; i < LCDB_NUM_RAILS; i++) {
		ret = regmap_read(lcdb->regmap, lcdb->base + qcom_lcdb_vreg[i], &val);
		if (ret)
			return ret;
		lcdb->uV[i] = qcom_lcdb_sel_to_uV(val & LCDB_OUTPUT_VOLTAGE_MASK);
	}
	lcdb->state = LCDB_DISABLED;
	return 0;
}

static int qcom_lcdb_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct regulator_config cfg = {};
	struct qcom_lcdb *lcdb;
	int irq, ret, i;

	if (!of_machine_is_compatible("xiaomi,lemon"))
		return -ENODEV;

	lcdb = devm_kzalloc(dev, sizeof(*lcdb), GFP_KERNEL);
	if (!lcdb)
		return -ENOMEM;

	lcdb->dev = dev;

	lcdb->regmap = dev_get_regmap(dev->parent, NULL);
	if (!lcdb->regmap)
		return dev_err_probe(dev, -ENODEV, "failed to get the parent regmap\n");

	ret = device_property_read_u32(dev, "reg", &lcdb->base);
	if (ret)
		return dev_err_probe(dev, ret, "failed to get the base address\n");

	ret = devm_mutex_init(dev, &lcdb->lock);
	if (ret)
		return ret;

	ret = qcom_lcdb_hw_init(lcdb);
	if (ret)
		return dev_err_probe(dev, ret, "failed to read the initial state\n");

	for (i = 0; i < LCDB_NUM_RAILS; i++) {
		struct device_node *node = of_get_child_by_name(dev->of_node,
							      qcom_lcdb_descs[i].of_match);
		bool allowed = node && of_device_is_available(node) &&
			       !of_property_read_bool(node, "regulator-boot-on") &&
			       !of_property_read_bool(node, "regulator-always-on");

		of_node_put(node);
		if (!allowed)
			return dev_err_probe(dev, -EINVAL, "explicit non-boot bias consumers required\n");
	}

	cfg.dev = dev;
	cfg.regmap = lcdb->regmap;
	cfg.driver_data = lcdb;

	for (i = 0; i < LCDB_NUM_RAILS; i++) {
		lcdb->rdev[i] = devm_regulator_register(dev, &qcom_lcdb_descs[i], &cfg);
		if (IS_ERR(lcdb->rdev[i]))
			return dev_err_probe(dev, PTR_ERR(lcdb->rdev[i]),
					     "failed to register %s\n",
					     qcom_lcdb_descs[i].name);
	}

	irq = platform_get_irq(pdev, 0);
	if (irq < 0)
		return irq;

	ret = devm_request_threaded_irq(dev, irq, NULL, qcom_lcdb_sc_irq,
					IRQF_ONESHOT, "lcdb-sc", lcdb);
	if (ret)
		return ret;
	platform_set_drvdata(pdev, lcdb);
	scoped_guard(mutex, &lcdb->lock)
		lcdb->armed = true;
	return 0;
}

static int qcom_lcdb_suspend(struct device *dev)
{
	return qcom_lcdb_suspend_off(dev_get_drvdata(dev));
}

static int qcom_lcdb_resume(struct device *dev)
{
	return qcom_lcdb_resume_off(dev_get_drvdata(dev));
}

static DEFINE_SIMPLE_DEV_PM_OPS(qcom_lcdb_pm, qcom_lcdb_suspend, qcom_lcdb_resume);

static const struct of_device_id qcom_lcdb_match[] = {
	{ .compatible = "qcom,pmi632-lcdb" },
	{ }
};
MODULE_DEVICE_TABLE(of, qcom_lcdb_match);

static struct platform_driver qcom_lcdb_driver = {
	.driver = {
		.name = "qcom-lcdb-regulator",
		.of_match_table = qcom_lcdb_match,
		.pm = pm_sleep_ptr(&qcom_lcdb_pm),
	},
	.probe = qcom_lcdb_probe,
};
module_platform_driver(qcom_lcdb_driver);

MODULE_DESCRIPTION("Qualcomm LCDB (LCD bias) regulator driver");
MODULE_LICENSE("GPL");
