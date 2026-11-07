/* SPDX-License-Identifier: MIT
 * Explicit single-contact mouse fallback for the verified wlfreerdp3 3.32.2.
 * Does not use uinput, evdev or display/DRM APIs. Not remote multitouch.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <freerdp/client.h>
#include <freerdp/input.h>

static rdpClientContext *owner;
static INT32 primary = -1, last_x, last_y;
static BOOL down;
static BOOL send_pointer(rdpClientContext *ctx, UINT16 flags, INT32 x, INT32 y)
{
	return freerdp_client_send_button_event(ctx, FALSE, flags, x, y);
}
BOOL freerdp_client_handle_touch(rdpClientContext *ctx, UINT32 flags, INT32 finger,
                                UINT32 pressure, INT32 x, INT32 y)
{
	const char *mode = getenv("LEMON_TOUCH_POINTER");
	if (!mode || (strcmp(mode, "drag") && strcmp(mode, "scroll"))) {
		fprintf(stderr, "LEMON_TOUCH_POINTER must be explicitly drag or scroll\n");
		return FALSE;
	}
	if (owner && owner != ctx) return FALSE;
	owner = ctx;
	(void)pressure; /* Patched Wayland client preserves the real contact ID. */
	if (flags == FREERDP_TOUCH_CANCEL) {
		BOOL ok = !down || send_pointer(ctx, PTR_FLAGS_BUTTON1, last_x, last_y);
		down = FALSE;primary = -1;
		return ok;
	}
	if (finger < 0 || x < 0 || y < 0) return FALSE;
	if (flags == FREERDP_TOUCH_DOWN) {
		if (primary != -1) return TRUE; /* Never promote another finger mid-contact. */
		primary = finger;last_x = x;last_y = y;
		if (!strcmp(mode,"scroll")) return TRUE;
		if (!send_pointer(ctx, PTR_FLAGS_MOVE,x,y)) { primary=-1;return FALSE; }
		down = TRUE;
		return send_pointer(ctx, PTR_FLAGS_BUTTON1|PTR_FLAGS_DOWN,x,y);
	}
	if (finger != primary) return TRUE;
	if (flags == FREERDP_TOUCH_MOTION) {
		if (!strcmp(mode,"scroll")) {
			INT32 delta = last_y-y;
			if (delta >= 24 || delta <= -24) {
				UINT16 wheel = PTR_FLAGS_WHEEL | (delta < 0 ? (PTR_FLAGS_WHEEL_NEGATIVE | (0x100-120)) : 120);
				last_x=x;last_y=y;
				return freerdp_client_send_wheel_event(ctx,wheel);
			}
			return TRUE;
		}
		last_x=x;last_y=y;
		return send_pointer(ctx,PTR_FLAGS_MOVE,x,y);
	}
	if (flags == FREERDP_TOUCH_UP) {
		BOOL ok = !down || send_pointer(ctx,PTR_FLAGS_BUTTON1,x,y);
		down=FALSE;primary=-1;
		return ok;
	}
	return FALSE;
}
