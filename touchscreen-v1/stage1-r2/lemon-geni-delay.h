/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef LEMON_GENI_DELAY_H
#define LEMON_GENI_DELAY_H
#include <linux/types.h>
#include <linux/errno.h>
/* Exact counter bitfields from both source trees; no time-unit conversion. */
static inline int lemon_geni_delay(u32 old, u32 cs, u32 words, u32 *value)
{
	if (cs > 1023 || words > 1023)
		return -EINVAL;
	*value = (old & ~0xfffffU) | (cs << 10) | words;
	return 0;
}
#endif
