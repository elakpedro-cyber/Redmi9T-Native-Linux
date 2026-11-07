// SPDX-License-Identifier: GPL-2.0-only
/* OFFLINE QEMU ONLY: real evdev emission without SPI, GPIO or regulators. */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/input/mt.h>
#include <linux/workqueue.h>
#include "nvt-frame.h"
static struct input_dev *test_input;
static struct delayed_work work;
static unsigned int phase;
static void emit(struct work_struct *unused)
{
 struct lemon_nvt_frame frame = {};
 const struct touchscreen_properties props = {};
 if (phase < 2) {
  frame.contacts[0].active = true;
  frame.contacts[0].x = phase ? 1000 : 1079;
  frame.contacts[0].y = phase ? 2200 : 2339;
  frame.contacts[9].active = true;
  frame.contacts[9].x = phase ? 40 : 0;
  frame.contacts[9].y = phase ? 80 : 0;
 }
 lemon_nvt_report_frame(test_input, &props, &frame);
 if (++phase < 3) schedule_delayed_work(&work,msecs_to_jiffies(200));
}
static int start(struct input_dev *input)
{ phase=0; schedule_delayed_work(&work,msecs_to_jiffies(200));return 0; }
static void stop(struct input_dev *input)
{ cancel_delayed_work_sync(&work); }
static int __init test_init(void)
{
 int ret;
 if (!of_machine_is_compatible("linux,dummy-virt")) return -ENODEV;
 test_input=input_allocate_device();if (!test_input)return -ENOMEM;
 test_input->name="lemon-nvt-offline-test";
 test_input->open=start;test_input->close=stop;
 input_set_abs_params(test_input,ABS_MT_POSITION_X,0,1079,0,0);
 input_set_abs_params(test_input,ABS_MT_POSITION_Y,0,2339,0,0);
 ret=input_mt_init_slots(test_input,10,INPUT_MT_DIRECT);
 if (ret)goto fail;
 INIT_DELAYED_WORK(&work,emit);
 ret=input_register_device(test_input);
 if (!ret)return 0;
fail: input_free_device(test_input);return ret;
}
static void __exit test_exit(void)
{ input_unregister_device(test_input); }
module_init(test_init);module_exit(test_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("QEMU dummy-virt only evdev regression; refuses Redmi 9T");
