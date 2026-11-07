from pathlib import Path
import sys, difflib

p = Path(sys.argv[1])
s = p.read_text()
old = s
s = s.replace('#include <linux/property.h>', '#include <linux/property.h>\n#include "lemon-geni-delay.h"')
s = s.replace('static void setup_spi_params(', 'static int setup_spi_params(')
needle = '\tu32 mode_changed = mas->last_mode ^ spi_slv->mode;'
assert s.count(needle) == 1
s = s.replace(needle, needle + '''
	u32 cs_delay = 0, word_delay = 0, delay_value;
	bool raw_delay = device_property_present(&spi_slv->dev, "qcom,cs-delay-counter");

	if (raw_delay &&
	    (device_property_read_u32(&spi_slv->dev, "qcom,cs-delay-counter", &cs_delay) ||
	    device_property_read_u32(&spi_slv->dev, "qcom,inter-word-delay-counter", &word_delay) ||
	    lemon_geni_delay(0, cs_delay, word_delay, &delay_value)))
		return -EINVAL;
''')
needle = '\ttrace_geni_spi_setup_params(mas->dev, chipselect, spi_slv->mode,\n\t\t\t\t    mode_changed, cs_changed);'
assert s.count(needle) == 1
s = s.replace(needle, '''	if (raw_delay) {
		lemon_geni_delay(readl(se->base + SE_SPI_DELAY_COUNTERS),
				 cs_delay, word_delay, &delay_value);
		writel(delay_value, se->base + SE_SPI_DELAY_COUNTERS);
	}
''' + needle + '\n\treturn 0;')
s = s.replace('\t\tsetup_spi_params(spi_msg->spi, spi);\n\t\treturn 0;', '\t\treturn setup_spi_params(spi_msg->spi, spi);')
s = s.replace('\tcase GENI_GPI_DMA:\n\t\t/* nothing to do for GPI DMA */', '''	case GENI_GPI_DMA:
		if (device_property_present(&spi_msg->spi->dev, "qcom,cs-delay-counter"))
			return -EOPNOTSUPP;
		/* nothing to do for GPI DMA */''')
s += '\nMODULE_VERSION("lemon-touch-v1");\n'
p.write_bytes(s.encode())
description = """Subject: [LOCAL REVIEW] spi: geni: preserve lemon stock raw delay counters

The stock NT36672A SPI profile uses raw CS counter 200 and inter-word
counter 0. Add opt-in raw fields without guessing their time units.
Reject this opt-in in GPI DMA mode until that path is separately verified.
This is a private experimental module patch, not an upstream submission.

---
"""
Path(__file__).with_name('geni-stock-delay.patch').write_bytes((description + ''.join(difflib.unified_diff(
    old.splitlines(True), s.splitlines(True), fromfile='a/drivers/spi/spi-geni-qcom.c',
    tofile='b/drivers/spi/spi-geni-qcom.c'))).encode())
