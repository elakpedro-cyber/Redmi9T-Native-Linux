/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef LEMON_NVT_FRAME_H
#define LEMON_NVT_FRAME_H
#include <linux/types.h>
#include <linux/input.h>
#include <linux/input/touchscreen.h>
#define NVT_REPORT_SIZE 66
#define NVT_CONTACTS 10
struct lemon_nvt_contact { u16 x, y; bool active; };
struct lemon_nvt_frame { struct lemon_nvt_contact contacts[NVT_CONTACTS]; };
int lemon_nvt_decode_frame(const u8 *data, size_t len, u16 width, u16 height,
                          struct lemon_nvt_frame *frame);
void lemon_nvt_report_frame(struct input_dev *input,
                           const struct touchscreen_properties *props,
                           const struct lemon_nvt_frame *frame);
#endif
