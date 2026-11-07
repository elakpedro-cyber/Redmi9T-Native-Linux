// SPDX-License-Identifier: GPL-2.0-only
/* Offline panel transport prototype. There is no probe or power sequencing. */
#include <linux/delay.h>
#include <linux/errno.h>
#include <linux/kernel.h>
#include <drm/drm_mipi_dsi.h>
#include <drm/drm_modes.h>

struct td4330_packet {
	u8 type, delay_ms, length;
	u8 payload[4];
};

#include "td4330-packets.h"

const struct drm_display_mode lemon_td4330_mode = {
	.clock = 173517,
	.hdisplay = 1080, .hsync_start = 1140, .hsync_end = 1148, .htotal = 1208,
	.vdisplay = 2340, .vsync_start = 2366, .vsync_end = 2370, .vtotal = 2394,
	.type = DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED,
};

static int lemon_td4330_send(struct mipi_dsi_device *dsi, bool enable)
{
	const struct td4330_packet *packets = enable ? td4330_on : td4330_off;
	size_t count = enable ? ARRAY_SIZE(td4330_on) : ARRAY_SIZE(td4330_off);
	size_t i;

	if (!dsi || !dsi->host || !dsi->host->ops ||
	    !dsi->host->ops->transfer || dsi->channel != 0)
		return -EINVAL;

	for (i = 0; i < count; i++) {
		const struct td4330_packet *packet = &packets[i];
		struct mipi_dsi_msg msg = {
			.channel = dsi->channel,
			.type = packet->type,
			.flags = MIPI_DSI_MSG_USE_LPM,
			.tx_buf = packet->payload,
			.tx_len = packet->length,
		};
		ssize_t sent = dsi->host->ops->transfer(dsi->host, &msg);

		if (sent < 0)
			return sent;
		/* MSM reports the DMA packet length including the header. */
		if ((size_t)sent < msg.tx_len)
			return -EIO;
		if (packet->delay_ms)
			msleep(packet->delay_ms);
	}
	return 0;
}

/* The caller owns rails, reset and the independent backlight gate.
 * Initialize a fresh session only after a verified power/reset sequence.
 */
enum td4330_state {
	TD4330_RESET_REQUIRED,
	TD4330_RESET_READY,
	TD4330_ACTIVE,
	TD4330_SLEEP,
};

int lemon_td4330_transition(struct mipi_dsi_device *dsi,
			   enum td4330_state *state, bool enable);

int lemon_td4330_transition(struct mipi_dsi_device *dsi,
			   enum td4330_state *state, bool enable)
{
	int ret;

	if (!state)
		return -EINVAL;
	if (*state == TD4330_RESET_REQUIRED)
		return -EIO;
	if (enable && *state != TD4330_RESET_READY)
		return -EINVAL;
	if (!enable && *state != TD4330_ACTIVE)
		return -EINVAL;

	ret = lemon_td4330_send(dsi, enable);
	*state = ret ? TD4330_RESET_REQUIRED :
		       (enable ? TD4330_ACTIVE : TD4330_SLEEP);
	return ret;
}
