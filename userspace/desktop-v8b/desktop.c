#define _POSIX_C_SOURCE 200809L
#include <cairo.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include "xdg-shell.h"

enum { W = 360, H = 800, STRIDE = W * 4, BYTES = STRIDE * H };
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct xdg_wm_base *wm;
static struct wl_surface *surface;
struct frame { struct wl_buffer *buffer; cairo_surface_t *pixels; bool busy; };
static struct frame frames[2];
static bool configured, dirty = true, running = true, light;
static int pointer_x = -1, pointer_y = -1, pulse;
static char input[72], system_name[80], cpu[40], ram[48], usb[48], ssh_status[48];
static long last_frame, last_info, last_animation;
static const char *mode;

static long now_ms(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000L + t.tv_nsec / 1000000;
}

static void info(void)
{
    struct utsname u;
    snprintf(system_name, sizeof system_name, "Linux");
    if (!uname(&u)) snprintf(system_name, sizeof system_name, "%.68s", u.release);
    long n = sysconf(_SC_NPROCESSORS_ONLN);
    snprintf(cpu, sizeof cpu, "%ld logical CPU%s", n, n == 1 ? "" : "s");
    snprintf(ram, sizeof ram, "Memory unavailable");
    FILE *f = fopen("/proc/meminfo", "r");
    if (f) {
        char line[96]; long kb;
        while (fgets(line, sizeof line, f))
            if (sscanf(line, "MemAvailable: %ld", &kb) == 1) {
                snprintf(ram, sizeof ram, "%ld MiB available", kb / 1024);
                break;
            }
        fclose(f);
    }
    int carrier = '0';
    f = fopen("/sys/class/net/usb0/carrier", "r");
    if (f) { carrier = fgetc(f); fclose(f); }
    snprintf(usb, sizeof usb, "USB NCM %s", carrier == '1' ? "connected" : "unavailable");
    snprintf(ssh_status, sizeof ssh_status, "SSH listener unavailable");
    f = fopen("/proc/net/tcp", "r");
    if (f) {
        char line[240];
        unsigned port, state;
        snprintf(ssh_status, sizeof ssh_status, "SSH not listening");
        while (fgets(line, sizeof line, f)) {
            if (sscanf(line, " %*u: %*8[0-9A-Fa-f]:%4x %*s %2x", &port, &state) == 2 &&
                port == 22 && state == 0x0a) {
                snprintf(ssh_status, sizeof ssh_status, "SSH listening on port 22");
                break;
            }
        }
        fclose(f);
    }
}

static void color(cairo_t *c, unsigned rgb)
{
    cairo_set_source_rgb(c, ((rgb >> 16) & 255) / 255.0,
                         ((rgb >> 8) & 255) / 255.0, (rgb & 255) / 255.0);
}

static void text(cairo_t *c, double x, double y, double size, unsigned rgb, const char *s)
{
    color(c, rgb);
    cairo_select_font_face(c, "DejaVu Sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
    cairo_set_font_size(c, size);
    cairo_move_to(c, x, y);
    cairo_show_text(c, s);
}

static void box(cairo_t *c, int x, int y, int w, int h, unsigned rgb)
{
    color(c, rgb);
    cairo_rectangle(c, x, y, w, h);
    cairo_fill(c);
}

static void draw(cairo_surface_t *pixels)
{
    cairo_t *c = cairo_create(pixels);
    unsigned bg = light ? 0xe8eff6 : 0x101a2b;
    unsigned card = light ? 0xffffff : 0x192942;
    unsigned fg = light ? 0x172337 : 0xf1f6ff;
    unsigned muted = light ? 0x485c72 : 0xa8b9d4;
    time_t now = time(NULL);
    char clock[24];
    strftime(clock, sizeof clock, "%H:%M", localtime(&now));
    box(c, 0, 0, W, H, bg);
    box(c, 0, 0, W, 48, 0x243d5a);
    text(c, 20, 30, 14, 0xffffff, "LEMON  /  REMOTE DESKTOP");
    text(c, 288, 30, 14, 0xffffff, clock);
    text(c, 22, 128, 64, fg, clock);
    text(c, 24, 160, 15, muted, "ALPINE LINUX   /   RAM SESSION");
    box(c, 18, 194, 324, 162, card);
    text(c, 32, 225, 13, muted, "SYSTEM");
    text(c, 32, 255, 12, fg, system_name);
    text(c, 32, 288, 16, fg, cpu);
    text(c, 32, 320, 16, fg, ram);
    box(c, 18, 374, 324, 136, card);
    text(c, 32, 404, 13, muted, "TRANSPORT AND RENDERER");
    text(c, 32, 434, 16, fg, usb);
    text(c, 32, 460, 13, fg, ssh_status);
    text(c, 32, 485, 15, fg, mode);
    box(c, 18, 532, 98, 52, 0x285477);
    box(c, 130, 532, 98, 52, 0x285477);
    box(c, 242, 532, 100, 52, 0x285477);
    text(c, 35, 563, 14, 0xffffff, "Theme");
    text(c, 144, 563, 14, 0xffffff, "Refresh");
    text(c, 260, 563, 14, 0xffffff, "Clear");
    box(c, 18, 609, 324, 102, card);
    text(c, 32, 639, 13, muted, "APP-ONLY KEYBOARD");
    cairo_save(c);
    cairo_rectangle(c, 32, 652, 288, 35);
    cairo_clip(c);
    text(c, 32, 676, 16, fg, input[0] ? input : "Type from the PC viewer");
    cairo_restore(c);
    box(c, 18, 742, 324, 3, 0x33516e);
    if (pulse) box(c, 18, 742, 54 * pulse, 3, 0x56e2c2);
    if (pointer_x >= 0) {
        color(c, 0xf8b551);
        cairo_arc(c, pointer_x, pointer_y, 6, 0, 6.284);
        cairo_stroke(c);
    }
    cairo_destroy(c);
    cairo_surface_flush(pixels);
}

static void release(void *data, struct wl_buffer *b)
{ (void)b; ((struct frame *)data)->busy = false; }
static const struct wl_buffer_listener buffer_listener = { release };

static void configure(void *data, struct xdg_surface *s, uint32_t serial)
{ (void)data; xdg_surface_ack_configure(s, serial); configured = dirty = true; }
static const struct xdg_surface_listener surface_listener = { configure };

static void close_window(void *data, struct xdg_toplevel *top)
{ (void)data; (void)top; running = false; }
static void size_window(void *data, struct xdg_toplevel *top, int32_t w, int32_t h, struct wl_array *states)
{ (void)data; (void)top; (void)w; (void)h; (void)states; }
static const struct xdg_toplevel_listener toplevel_listener = {
    .configure = size_window, .close = close_window
};

static void ping(void *data, struct xdg_wm_base *base, uint32_t serial)
{ (void)data; xdg_wm_base_pong(base, serial); }
static const struct xdg_wm_base_listener wm_listener = { ping };

static void global(void *data, struct wl_registry *r, uint32_t id, const char *name, uint32_t version)
{
    (void)data; (void)version;
    if (!strcmp(name, wl_compositor_interface.name))
        compositor = wl_registry_bind(r, id, &wl_compositor_interface, 1);
    else if (!strcmp(name, wl_shm_interface.name))
        shm = wl_registry_bind(r, id, &wl_shm_interface, 1);
    else if (!strcmp(name, xdg_wm_base_interface.name))
        wm = wl_registry_bind(r, id, &xdg_wm_base_interface, 1);
}
static void remove_global(void *data, struct wl_registry *r, uint32_t id)
{ (void)data; (void)r; (void)id; }
static const struct wl_registry_listener registry_listener = { global, remove_global };

static bool valid_command(const char *s)
{
    int x, y; char extra;
    if (!strncmp(s, "move ", 5) || !strncmp(s, "click ", 6)) {
        const char *coords = strchr(s, ' ') + 1;
        if (strspn(coords, "0123456789 ") != strlen(coords) || strlen(coords) > 7)
            return false;
        return sscanf(coords, "%d %d%c", &x, &y, &extra) == 2 &&
               x >= 0 && x < W && y >= 0 && y < H;
    }
    if (!strcmp(s, "backspace") || !strcmp(s, "quit")) return true;
    return strlen(s) == 5 && !strncmp(s, "key ", 4) && s[4] >= 32 && s[4] <= 126;
}

static void input_event(const char *cmd)
{
    if (!valid_command(cmd)) return;
    if (!strcmp(cmd, "quit")) { running = false; return; }
    if (!strncmp(cmd, "move ", 5) || !strncmp(cmd, "click ", 6)) {
        sscanf(strchr(cmd, ' ') + 1, "%d %d", &pointer_x, &pointer_y);
        if (cmd[0] == 'c') {
            pulse = 6;
            if (pointer_y >= 532 && pointer_y < 584) {
                if (pointer_x >= 18 && pointer_x < 116) light = !light;
                else if (pointer_x >= 130 && pointer_x < 228) info();
                else if (pointer_x >= 242 && pointer_x < 342) input[0] = 0;
            }
        }
    } else {
        size_t len = strlen(input);
        if (cmd[0] == 'k' && len < sizeof(input) - 1) input[len] = cmd[4];
        if (cmd[0] == 'b' && len) input[len - 1] = 0;
    }
    dirty = true;
}

int main(int argc, char **argv)
{
    struct sockaddr_un addr = { .sun_family = AF_UNIX };
    if (argc != 3 || strlen(argv[2]) >= sizeof addr.sun_path) return 2;
    strcpy(addr.sun_path, argv[2]);
    int sock = socket(AF_UNIX, SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    if (sock < 0) return 1;
    if (!strcmp(argv[1], "input")) {
        char cmd[32];
        if (!fgets(cmd, sizeof cmd, stdin) || !strchr(cmd, '\n')) return 2;
        *strchr(cmd, '\n') = 0;
        if (!valid_command(cmd)) return 2;
        return sendto(sock, cmd, strlen(cmd), 0, (struct sockaddr *)&addr, sizeof addr) < 0;
    }
    if (strcmp(argv[1], "gl") && strcmp(argv[1], "pixman")) return 2;
    mode = !strcmp(argv[1], "gl") ? "Adreno 610  /  FD610 GL" : "Pixman  /  software";
    umask(077);
    if (bind(sock, (struct sockaddr *)&addr, sizeof addr)) return 1;

    struct wl_display *display = wl_display_connect(NULL);
    if (!display) return 1;
    struct wl_registry *registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    if (wl_display_roundtrip(display) < 0 || !compositor || !shm || !wm) return 1;
    xdg_wm_base_add_listener(wm, &wm_listener, NULL);

    const char *dir = getenv("XDG_RUNTIME_DIR");
    char path[256];
    if (!dir || snprintf(path, sizeof path, "%s/shm.XXXXXX", dir) >= (int)sizeof path) return 1;
    int fd = mkstemp(path);
    if (fd < 0) return 1;
    unlink(path);
    if (ftruncate(fd, 2 * BYTES)) return 1;
    unsigned char *data = mmap(NULL, 2 * BYTES, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (data == MAP_FAILED) return 1;
    struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, 2 * BYTES);
    for (int i = 0; i < 2; i++) {
        frames[i].buffer = wl_shm_pool_create_buffer(pool, i * BYTES, W, H, STRIDE, WL_SHM_FORMAT_XRGB8888);
        frames[i].pixels = cairo_image_surface_create_for_data(data + i * BYTES, CAIRO_FORMAT_RGB24, W, H, STRIDE);
        wl_buffer_add_listener(frames[i].buffer, &buffer_listener, &frames[i]);
    }
    wl_shm_pool_destroy(pool);
    close(fd);
    surface = wl_compositor_create_surface(compositor);
    struct xdg_surface *xs = xdg_wm_base_get_xdg_surface(wm, surface);
    xdg_surface_add_listener(xs, &surface_listener, NULL);
    struct xdg_toplevel *top = xdg_surface_get_toplevel(xs);
    xdg_toplevel_add_listener(top, &toplevel_listener, NULL);
    xdg_toplevel_set_title(top, "Lemon Desktop");
    xdg_toplevel_set_fullscreen(top, NULL);
    wl_surface_commit(surface);
    info();
    unsigned long sequence = 0;
    char sequence_path[sizeof addr.sun_path + 16], sequence_tmp[sizeof addr.sun_path + 16];
    snprintf(sequence_path, sizeof sequence_path, "%s.frame", addr.sun_path);
    snprintf(sequence_tmp, sizeof sequence_tmp, "%s.frame.new", addr.sun_path);

    while (running) {
        long now = now_ms();
        if (now - last_info >= 60000) { info(); dirty = true; last_info = now; }
        if (pulse && now - last_animation >= 85) { pulse--; dirty = true; last_animation = now; }
        struct frame *frame = !frames[0].busy ? &frames[0] : !frames[1].busy ? &frames[1] : NULL;
        if (configured && dirty && frame && now - last_frame >= 85) {
            draw(frame->pixels);
            wl_surface_attach(surface, frame->buffer, 0, 0);
            wl_surface_damage(surface, 0, 0, W, H);
            wl_surface_commit(surface);
            frame->busy = true; dirty = false; last_frame = now;
            FILE *marker = fopen(sequence_tmp, "w");
            if (marker) {
                fprintf(marker, "%lu\n", ++sequence);
                if (!fclose(marker)) rename(sequence_tmp, sequence_path);
            }
        }
        int flushed = wl_display_flush(display);
        if (flushed < 0 && errno != EAGAIN) break;
        struct pollfd fds[] = {{wl_display_get_fd(display), POLLIN | (flushed < 0 ? POLLOUT : 0), 0},
                               {sock, POLLIN, 0}};
        if (poll(fds, 2, dirty || pulse ? 85 : 1000) < 0 && errno != EINTR) break;
        if (fds[0].revents & (POLLERR | POLLHUP | POLLNVAL)) break;
        if ((fds[0].revents & POLLIN) && wl_display_dispatch(display) < 0) break;
        if (fds[1].revents & POLLIN) {
            char cmd[32]; ssize_t n = recv(sock, cmd, sizeof cmd - 1, 0);
            if (n > 0 && n < (ssize_t)sizeof cmd - 1) { cmd[n] = 0; input_event(cmd); }
        }
    }
    for (int i = 0; i < 2; i++) cairo_surface_destroy(frames[i].pixels);
    wl_display_disconnect(display);
    munmap(data, 2 * BYTES);
    close(sock);
    unlink(addr.sun_path);
    return 0;
}
