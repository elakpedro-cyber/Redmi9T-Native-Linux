#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <freerdp/client.h>
#include <freerdp/input.h>
#include "wlfreerdp.h"
#include "wlf_input.h"
BOOL wlf_scale_coordinates(rdpContext *ctx,UINT32 *x,UINT32 *y,BOOL direction)
{ (void)ctx;(void)direction;return *x<1080 && *y<2340; }
static unsigned buttons,wheels;
static UINT16 last_flags;
static INT32 last_x,last_y;
BOOL freerdp_client_send_button_event(rdpClientContext *ctx,BOOL relative,UINT16 flags,INT32 x,INT32 y)
{ (void)ctx;assert(!relative);buttons++;last_flags=flags;last_x=x;last_y=y;return TRUE; }
BOOL freerdp_client_send_wheel_event(rdpClientContext *ctx,UINT16 flags)
{ (void)ctx;assert(flags&PTR_FLAGS_WHEEL);wheels++;return TRUE; }
int main(void)
{
 wlfContext wlf={0};
 rdpClientContext *context=&wlf.common;
 freerdp instance={0};instance.context=&context->context;

 assert(setenv("LEMON_TOUCH_POINTER","drag",1)==0);
 UwacTouchDown ev={.id=4,.x=12,.y=15};
 assert(wlf_handle_touch_down(&instance,&ev));
 assert(buttons==2 && (last_flags&PTR_FLAGS_DOWN));
 assert(freerdp_client_handle_touch(context,FREERDP_TOUCH_DOWN,7,0,900,1200));
 assert(buttons==2);
 UwacTouchMotion motion={.id=4,.x=77,.y=88};
 assert(wlf_handle_touch_motion(&instance,&motion));
 assert(last_x==77 && last_y==88 && buttons==3);
 UwacTouchUp up={.id=4,.x=77,.y=88};
 assert(wlf_handle_touch_up(&instance,&up));
 assert(!(last_flags&PTR_FLAGS_DOWN) && buttons==4);
 assert(freerdp_client_handle_touch(context,FREERDP_TOUCH_DOWN,9,0,20,30));
 assert(freerdp_client_handle_touch(context,FREERDP_TOUCH_CANCEL,9,0,0,0));
 assert(!(last_flags&PTR_FLAGS_DOWN));
 assert(setenv("LEMON_TOUCH_POINTER","scroll",1)==0);
 assert(freerdp_client_handle_touch(context,FREERDP_TOUCH_DOWN,2,0,40,200));
 assert(freerdp_client_handle_touch(context,FREERDP_TOUCH_MOTION,2,0,40,150));
 assert(wheels==1);
 assert(freerdp_client_handle_touch(context,FREERDP_TOUCH_UP,2,0,40,150));
 puts("ARM64_REAL_WLF_CALLBACKS_POINTER_PASS drag second_contact_ignored motion_id up cancel scroll");
 return 0;
}
