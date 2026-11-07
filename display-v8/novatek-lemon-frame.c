// SPDX-License-Identifier: GPL-2.0-only
/* Offline parser for the normal Xiaomi Novatek NVT SPI report. No SPI I/O. */
#include <linux/errno.h>
#include <linux/input/mt.h>
#include <linux/input/touchscreen.h>
#include <linux/types.h>

#define NVT_REPORT_SIZE 66
#define NVT_CONTACTS 10

struct lemon_nvt_contact {
	u16 x, y;
	bool active;
};

struct lemon_nvt_frame {
	struct lemon_nvt_contact contacts[NVT_CONTACTS];
};

int lemon_nvt_decode_frame(const u8 *data, size_t len, u16 width, u16 height,
			  struct lemon_nvt_frame *frame);

int lemon_nvt_decode_frame(const u8 *data, size_t len, u16 width, u16 height,
			  struct lemon_nvt_frame *frame)
{
	struct lemon_nvt_frame decoded = {};
	bool watchdog = true, handshake = true;
	unsigned int i;
	u8 sum = 0;

	if (!data || !frame || len != NVT_REPORT_SIZE || !width || !height)
		return -EINVAL;

	for (i = 1; i <= 6; i++) {
		watchdog &= data[i] == 0xfd || data[i] == 0xfe;
		handshake &= data[i] == 0x77;
	}
	if (watchdog || handshake)
		return -EAGAIN;

	for (i = 1; i < NVT_REPORT_SIZE; i++)
		sum += data[i];
	if (sum)
		return -EBADMSG;
	if ((data[1] >> 3) == 30)
		return -EOPNOTSUPP;

	for (i = 0; i < NVT_CONTACTS; i++) {
		const u8 *point = data + 1 + 6 * i;
		unsigned int id = point[0] >> 3;
		unsigned int status = point[0] & 7;
		struct lemon_nvt_contact *contact;

		if (status != 1 && status != 2)
			continue;
		if (!id || id > NVT_CONTACTS)
			return -EPROTO;
		contact = &decoded.contacts[id - 1];
		if (contact->active)
			return -EPROTO;
		contact->x = (point[1] << 4) | (point[3] >> 4);
		contact->y = (point[2] << 4) | (point[3] & 0xf);
		if (contact->x >= width || contact->y >= height)
			return -ERANGE;
		contact->active = true;
	}

	*frame = decoded;
	return 0;
}


/* Input must have ten direct MT slots. Publish only a complete decoded frame. */
void lemon_nvt_report_frame(struct input_dev *input,
			    const struct touchscreen_properties *props,
			    const struct lemon_nvt_frame *frame);

void lemon_nvt_report_frame(struct input_dev *input,
			    const struct touchscreen_properties *props,
			    const struct lemon_nvt_frame *frame)
{
	unsigned int i;

	for (i = 0; i < NVT_CONTACTS; i++) {
		const struct lemon_nvt_contact *contact = &frame->contacts[i];

		input_mt_slot(input, i);
		input_mt_report_slot_state(input, MT_TOOL_FINGER, contact->active);
		if (contact->active)
			touchscreen_report_pos(input, props, contact->x, contact->y, true);
	}
	input_mt_sync_frame(input);
	input_sync(input);
}
