from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "display-v8/novatek-lemon-frame.c").read_text()
source = re.sub(r"^#include <linux/[^>]+>\n", "", source, flags=re.M)
test = r"""
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8;
typedef uint16_t u16;
#define MT_TOOL_FINGER 0
struct input_dev {
    unsigned slot, frames, syncs, positions;
    bool active[10];
};
struct touchscreen_properties {};
static void input_mt_slot(struct input_dev *in, unsigned i) { in->slot = i; }
static void input_mt_report_slot_state(struct input_dev *in, int tool, bool active)
{ assert(tool == MT_TOOL_FINGER); in->active[in->slot] = active; }
static void touchscreen_report_pos(struct input_dev *in, const struct touchscreen_properties *props,
                                   unsigned x, unsigned y, bool mt)
{ assert(props && x < 1080 && y < 2340 && mt); in->positions++; }
static void input_mt_sync_frame(struct input_dev *in) { in->frames++; }
static void input_sync(struct input_dev *in) { in->syncs++; }
""" + source + r"""
static void checksum(u8 *d)
{
    d[65] = 0;
    for (unsigned i = 1; i < 65; i++)
        d[65] -= d[i];
}

static void contact(u8 *d, unsigned pos, unsigned id, unsigned x, unsigned y)
{
    u8 *p = d + 1 + 6 * pos;
    p[0] = id << 3 | 1;
    p[1] = x >> 4;
    p[2] = y >> 4;
    p[3] = (x & 15) << 4 | (y & 15);
    checksum(d);
}

int main(void)
{
    u8 d[NVT_REPORT_SIZE] = {};
    struct lemon_nvt_frame frame = {};
    assert(!lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame));
    assert(!frame.contacts[0].active);

    contact(d, 0, 1, 1079, 2339);
    contact(d, 9, 10, 0, 0);
    assert(!lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame));
    assert(frame.contacts[0].active && frame.contacts[0].x == 1079);
    assert(frame.contacts[0].y == 2339 && frame.contacts[9].active);
    assert(!frame.contacts[1].active);
    struct input_dev in = {};
    const struct touchscreen_properties props = {};
    lemon_nvt_report_frame(&in, &props, &frame);
    assert(in.active[0] && in.active[9] && !in.active[1]);
    assert(in.frames == 1 && in.syncs == 1 && in.positions == 2);


    contact(d, 9, 1, 0, 0);
    assert(lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame) == -EPROTO);
    assert(frame.contacts[0].x == 1079 && frame.contacts[9].active);
    contact(d, 9, 10, 1080, 2340);
    assert(lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame) == -ERANGE);
    contact(d, 9, 0, 0, 0);
    assert(lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame) == -EPROTO);
    d[65]++;
    assert(lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame) == -EBADMSG);
    assert(lemon_nvt_decode_frame(d, 65, 1080, 2340, &frame) == -EINVAL);

    memset(d + 1, 0x77, 6);
    assert(lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame) == -EAGAIN);
    memset(d + 1, 0xfd, 6);
    d[3] = 0xfe;
    assert(lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame) == -EAGAIN);
    d[1] = 30 << 3;
    checksum(d);
    assert(lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame) == -EOPNOTSUPP);

    memset(d, 0, sizeof(d));
    assert(!lemon_nvt_decode_frame(d, sizeof(d), 1080, 2340, &frame));
    assert(!frame.contacts[0].active && !frame.contacts[9].active);
    lemon_nvt_report_frame(&in, &props, &frame);
    assert(!in.active[0] && !in.active[9]);
    assert(in.frames == 2 && in.syncs == 2 && in.positions == 2);

}
"""

with tempfile.TemporaryDirectory(prefix="lemon-nvt-") as tmp:
    src = Path(tmp) / "test.c"
    exe = src.with_suffix("")
    src.write_text(test)
    subprocess.run(["aarch64-linux-gnu-gcc", "-static", "-Wall", "-Wextra",
                    "-Werror", src, "-o", exe], check=True)
    subprocess.run(["qemu-aarch64-static", exe], check=True, timeout=10)
print("PASS: ARM64 QEMU NVT contact slots, frame release, checksum, bounds, duplicate ID, watchdog/palm")

