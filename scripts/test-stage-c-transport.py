from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
display = root / "display-v8"
stub = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#include <sys/types.h>
typedef uint8_t u8;
#define ARRAY_SIZE(a) (sizeof(a) / sizeof(*(a)))
#define MIPI_DSI_MSG_USE_LPM 2
#define DRM_MODE_TYPE_DRIVER 1
#define DRM_MODE_TYPE_PREFERRED 2
struct drm_display_mode {
    int clock, hdisplay, hsync_start, hsync_end, htotal;
    int vdisplay, vsync_start, vsync_end, vtotal, type;
};
struct mipi_dsi_msg {
    int channel, type, flags;
    const void *tx_buf;
    size_t tx_len;
};
struct mipi_dsi_host;
struct mipi_dsi_host_ops {
    ssize_t (*transfer)(struct mipi_dsi_host *, const struct mipi_dsi_msg *);
};
struct mipi_dsi_host { const struct mipi_dsi_host_ops *ops; };
struct mipi_dsi_device { struct mipi_dsi_host *host; int channel; };
static unsigned calls, failure, delay, fault_kind;
static void msleep(unsigned ms) { delay += ms; }
static ssize_t transfer(struct mipi_dsi_host *host, const struct mipi_dsi_msg *msg)
{
    (void)host;
    assert(msg->channel == 0 && msg->flags == MIPI_DSI_MSG_USE_LPM);
    assert(msg->type == 0x05 || msg->type == 0x39);
    assert(msg->tx_len > 0);
    if (++calls == failure)
        return fault_kind ? 1 : -ETIMEDOUT;
    return msg->tx_len + 4;
}
"""
checks = r"""
int main(void)
{
    const struct mipi_dsi_host_ops ops = { transfer };
    struct mipi_dsi_host host = { &ops };
    struct mipi_dsi_device dsi = { &host, 0 };
    for (unsigned on = 0; on <= 1; on++) {
        unsigned count = on ? ARRAY_SIZE(td4330_on) : ARRAY_SIZE(td4330_off);
        const struct td4330_packet *packets = on ? td4330_on : td4330_off;
        unsigned expected_delay = 0;
        for (failure = 1; failure <= count; failure++) {
            for (fault_kind = 0; fault_kind <= 1; fault_kind++) {
                calls = delay = 0;
                assert(lemon_td4330_send(&dsi, on) == (fault_kind ? -EIO : -ETIMEDOUT));
                assert(calls == failure && delay == expected_delay);
            }
            expected_delay += packets[failure - 1].delay_ms;
        }
        calls = delay = 0;
        assert(lemon_td4330_send(&dsi, on) == 0);
        assert(calls == count && delay == expected_delay);
    }

    enum td4330_state state = 0;
    calls = 0;
    assert(lemon_td4330_transition(&dsi, &state, true) == -EIO && calls == 0);
    state = TD4330_RESET_READY;
    failure = 3; fault_kind = 0;
    assert(lemon_td4330_transition(&dsi, &state, true) == -ETIMEDOUT);
    assert(state == TD4330_RESET_REQUIRED && calls == 3);
    assert(lemon_td4330_transition(&dsi, &state, true) == -EIO);
    assert(lemon_td4330_transition(&dsi, &state, false) == -EIO && calls == 3);

    state = TD4330_RESET_READY;
    calls = failure = 0;
    assert(lemon_td4330_transition(&dsi, &state, true) == 0 && state == TD4330_ACTIVE);
    failure = calls + 2;
    assert(lemon_td4330_transition(&dsi, &state, false) == -ETIMEDOUT);
    assert(state == TD4330_RESET_REQUIRED && calls == failure);
    assert(lemon_td4330_transition(&dsi, &state, true) == -EIO && calls == failure);

    state = TD4330_RESET_READY;
    calls = failure = 0;
    assert(lemon_td4330_transition(&dsi, &state, true) == 0 && state == TD4330_ACTIVE);
    assert(lemon_td4330_transition(&dsi, &state, false) == 0 && state == TD4330_SLEEP);
    assert(lemon_td4330_transition(&dsi, &state, true) == -EINVAL);
    calls = 0;
    dsi.channel = 1;
    assert(lemon_td4330_send(&dsi, true) == -EINVAL && calls == 0);
    return 0;
}
"""
source = (display / "td4330-profile.c").read_text()
source = re.sub(r"^#include <[^>]+>\n", "", source, flags=re.M)
with tempfile.TemporaryDirectory(prefix="lemon-transport-") as temp:
    test = Path(temp) / "transport.c"
    binary = test.with_suffix("")
    test.write_text(stub + source + checks)
    subprocess.run(["cc", "-Wall", "-Wextra", "-Werror", "-I", display, test, "-o", binary], check=True)
    subprocess.run([binary], check=True)
print("PASS: TD4330 transport, two complete sequences and 158 injected packet errors and no retry after partial init/off; no hardware")
