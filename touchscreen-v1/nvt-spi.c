// SPDX-License-Identifier: GPL-2.0-only
/* NT36672A SPI handoff input driver. Protocol derived from Xiaomi lime-q-oss
 * 02ca1a919564a9b176a79cce09c40977f833e9ac, NT36672A/nt36xxx.c.
 * No reset, regulator switching, firmware upload, ESD recovery or raw proc I/O.
 */
#include <linux/device.h>
#include <linux/input/mt.h>
#include <linux/interrupt.h>
#include <linux/irq.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/property.h>
#include <linux/spi/spi.h>
#include "nvt-frame.h"

#define NVT_EVENT 0x21c00
#define NVT_FWINFO 0x78
#define NVT_PID 0x9a
#define NVT_MAX_ERRORS 3

static bool stage1_authorized;
module_param(stage1_authorized, bool, 0400);
MODULE_PARM_DESC(stage1_authorized, "Explicit experimental handoff-only probe authorization");

struct lemon_nvt {
	struct spi_device *spi;
	struct input_dev *input;
	struct touchscreen_properties props;
	struct mutex lock;
	bool irq_enabled, opened, suspended, fault;
	unsigned int errors;
	u8 tx[NVT_REPORT_SIZE + 1], rx[NVT_REPORT_SIZE + 1];
};

static int nvt_page(struct lemon_nvt *ts, u32 address)
{
	/* Only event-buffer pages. No arbitrary register writes. */
	if ((address >> 7) != (NVT_EVENT >> 7) &&
	    (address >> 7) != ((NVT_EVENT + NVT_PID) >> 7))
		return -EPERM;
	ts->tx[0] = 0xff;
	ts->tx[1] = address >> 15;
	ts->tx[2] = address >> 7;
	return spi_write(ts->spi, ts->tx, 3);
}

static int nvt_read(struct lemon_nvt *ts, u8 offset, u8 *data, size_t len)
{
	struct spi_transfer transfer = {
		.tx_buf = ts->tx, .rx_buf = ts->rx, .len = len + 2,
	};
	int ret;

	if (!len || len > NVT_REPORT_SIZE - 1)
		return -EINVAL;
	memset(ts->tx, 0, sizeof(ts->tx));
	ts->tx[0] = offset & 0x7f;
	ret = spi_sync_transfer(ts->spi, &transfer, 1);
	if (!ret)
		memcpy(data, ts->rx + 2, len);
	return ret;
}

static int nvt_identity(struct lemon_nvt *ts)
{
	u8 info[16], pid[2];
	int ret;

	ret = nvt_page(ts, NVT_EVENT + NVT_FWINFO);
	if (!ret)
		ret = nvt_read(ts, NVT_FWINFO, info, sizeof(info));
	if (ret)
		return ret;
	if ((unsigned int)info[0] + info[1] != 0xff || info[0] != 5 ||
	    ((info[4] << 8) | info[5]) != 1080 ||
	    ((info[6] << 8) | info[7]) != 2340)
		return -ENODEV;
	ret = nvt_page(ts, NVT_EVENT + NVT_PID);
	if (!ret)
		ret = nvt_read(ts, NVT_PID, pid, sizeof(pid));
	if (!ret && ((pid[1] << 8) | pid[0]) != 0x5940)
		ret = -ENODEV;
	/* Restore event page even on a project mismatch; no reset fallback. */
	if (nvt_page(ts, NVT_EVENT) && !ret)
		ret = -EIO;
	return ret;
}

static void nvt_release(struct lemon_nvt *ts)
{
	const struct lemon_nvt_frame empty = {};

	lemon_nvt_report_frame(ts->input, &ts->props, &empty);
}

static irqreturn_t nvt_irq(int irq, void *data)
{
	struct lemon_nvt *ts = data;
	struct lemon_nvt_frame frame;
	u8 report[NVT_REPORT_SIZE] = {};
	int ret;

	mutex_lock(&ts->lock);
	if (!ts->irq_enabled || ts->fault || ts->suspended)
		goto out;
	ret = nvt_read(ts, 0, report + 1, sizeof(report) - 1);
	if (!ret)
		ret = lemon_nvt_decode_frame(report, sizeof(report), 1080, 2340, &frame);
	if (ret) {
		/* Never retain a pressed slot after a corrupt or failed transfer. */
		nvt_release(ts);
		if (++ts->errors >= NVT_MAX_ERRORS) {
			ts->fault = true;
			ts->irq_enabled = false;
			disable_irq_nosync(irq);
			dev_err(&ts->spi->dev, "input fault latched (%d); no reset/retry\n", ret);
		}
		goto out;
	}
	ts->errors = 0;
	lemon_nvt_report_frame(ts->input, &ts->props, &frame);
out:
	mutex_unlock(&ts->lock);
	return IRQ_HANDLED;
}

static int nvt_open(struct input_dev *input)
{
	struct lemon_nvt *ts = input_get_drvdata(input);
	int ret = 0;

	mutex_lock(&ts->lock);
	if (ts->fault || ts->suspended) {
		ret = -EIO;
		goto out;
	}
	ret = nvt_identity(ts);
	if (ret) {
		ts->fault = true;
		goto out;
	}
	ts->opened = true;
	ts->irq_enabled = true;
	enable_irq(ts->spi->irq);
out:
	mutex_unlock(&ts->lock);
	return ret;
}

static void nvt_stop(struct lemon_nvt *ts)
{
	mutex_lock(&ts->lock);
	if (ts->irq_enabled) {
		ts->irq_enabled = false;
		disable_irq_nosync(ts->spi->irq);
	}
	mutex_unlock(&ts->lock);
	/* Do not wait while holding the mutex taken by the IRQ thread. */
	synchronize_irq(ts->spi->irq);
	mutex_lock(&ts->lock);
	nvt_release(ts);
	mutex_unlock(&ts->lock);
}

static void nvt_close(struct input_dev *input)
{
	struct lemon_nvt *ts = input_get_drvdata(input);

	mutex_lock(&ts->lock);
	ts->opened = false;
	mutex_unlock(&ts->lock);
	nvt_stop(ts);
}

static void nvt_cleanup(void *data)
{
	nvt_stop(data);
}

static ssize_t fault_show(struct device *dev, struct device_attribute *attr, char *buf)
{
	struct lemon_nvt *ts = dev_get_drvdata(dev);

	return sysfs_emit(buf, "%u\n", READ_ONCE(ts->fault));
}
static DEVICE_ATTR_RO(fault);
static struct attribute *nvt_attrs[] = { &dev_attr_fault.attr, NULL };
ATTRIBUTE_GROUPS(nvt);

static int nvt_probe(struct spi_device *spi)
{
	struct device *dev = &spi->dev;
	struct lemon_nvt *ts;
	int ret;
	u32 cs_delay, word_delay;

	if (!stage1_authorized || !device_property_read_bool(dev, "xiaomi,validated-touch-handoff"))
		return dev_err_probe(dev, -EPERM, "handoff validation/authorization required\n");
	if (spi_get_chipselect(spi, 0) != 1 || spi->irq <= 0 ||
	    irq_get_trigger_type(spi->irq) != IRQ_TYPE_EDGE_RISING ||
	    !spi->max_speed_hz || spi->max_speed_hz > 9600000 ||
	    (spi->mode & (SPI_CPOL | SPI_CPHA | SPI_CS_HIGH | SPI_LSB_FIRST)))
		return dev_err_probe(dev, -EINVAL, "unexpected SPI/IRQ configuration\n");
	if (device_property_read_u32(dev, "qcom,cs-delay-counter", &cs_delay) || cs_delay != 200 ||
	    device_property_read_u32(dev, "qcom,inter-word-delay-counter", &word_delay) || word_delay)
		return dev_err_probe(dev, -EINVAL, "stock raw SPI delay counters required\n");
	ts = devm_kzalloc(dev, sizeof(*ts), GFP_KERNEL);
	if (!ts)
		return -ENOMEM;
	ts->spi = spi;
	mutex_init(&ts->lock);
	spi_set_drvdata(spi, ts);
	spi->bits_per_word = 8;
	ret = spi_setup(spi);
	if (ret)
		return ret;
	ret = nvt_identity(ts);
	if (ret)
		return dev_err_probe(dev, ret, "expected live PID5940 FW5 1080x2340; no reset/upload\n");
	ts->input = devm_input_allocate_device(dev);
	if (!ts->input)
		return -ENOMEM;
	ts->input->name = "Lemon NT36672A handoff touchscreen";
	ts->input->id.bustype = BUS_SPI;
	ts->input->open = nvt_open;
	ts->input->close = nvt_close;
	input_set_drvdata(ts->input, ts);
	input_set_abs_params(ts->input, ABS_MT_POSITION_X, 0, 1079, 0, 0);
	input_set_abs_params(ts->input, ABS_MT_POSITION_Y, 0, 2339, 0, 0);
	touchscreen_parse_properties(ts->input, true, &ts->props);
	ret = input_mt_init_slots(ts->input, NVT_CONTACTS, INPUT_MT_DIRECT);
	if (ret)
		return ret;
	ret = devm_request_threaded_irq(dev, spi->irq, NULL, nvt_irq,
				       IRQF_ONESHOT | IRQF_NO_AUTOEN, dev_name(dev), ts);
	if (ret)
		return ret;
	ret = input_register_device(ts->input);
	if (ret)
		return ret;
	ret = devm_add_action_or_reset(dev, nvt_cleanup, ts);
	if (ret)
		return ret;
	dev_info(dev, "handoff input ready: PID5940 FW5; reset/power/upload disabled\n");
	return 0;
}

static int nvt_suspend(struct device *dev)
{
	struct lemon_nvt *ts = dev_get_drvdata(dev);

	mutex_lock(&ts->lock);
	ts->suspended = true;
	mutex_unlock(&ts->lock);
	nvt_stop(ts);
	return 0;
}

static int nvt_resume(struct device *dev)
{
	struct lemon_nvt *ts = dev_get_drvdata(dev);
	int ret;

	mutex_lock(&ts->lock);
	if (ts->fault) {
		mutex_unlock(&ts->lock);
		return -EIO;
	}
	ret = nvt_identity(ts);
	if (ret) {
		ts->fault = true;
		ret = ret ?: -EIO;
	} else {
		ts->suspended = false;
		if (ts->opened) {
			ts->irq_enabled = true;
			enable_irq(ts->spi->irq);
		}
	}
	mutex_unlock(&ts->lock);
	return ret;
}
static void nvt_shutdown(struct spi_device *spi)
{
	nvt_stop(spi_get_drvdata(spi));
}

static DEFINE_SIMPLE_DEV_PM_OPS(nvt_pm, nvt_suspend, nvt_resume);
static const struct of_device_id nvt_of_match[] = {
	{ .compatible = "xiaomi,lemon-nt36672a-handoff" }, { }
};
MODULE_DEVICE_TABLE(of, nvt_of_match);
static const struct spi_device_id nvt_ids[] = { { "lemon-nvt-handoff", 0 }, { } };
MODULE_DEVICE_TABLE(spi, nvt_ids);
static struct spi_driver nvt_driver = {
	.driver = { .name = "lemon-nvt-handoff", .of_match_table = nvt_of_match,
		    .pm = pm_sleep_ptr(&nvt_pm), .dev_groups = nvt_groups },
	.probe = nvt_probe, .shutdown = nvt_shutdown, .id_table = nvt_ids,
};
module_spi_driver(nvt_driver);
MODULE_DESCRIPTION("Redmi 9T NT36672A SPI handoff-only experimental input driver");
MODULE_LICENSE("GPL");
