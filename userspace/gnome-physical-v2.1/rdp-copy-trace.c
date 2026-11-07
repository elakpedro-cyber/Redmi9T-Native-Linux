#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <freerdp/codec/color.h>
#include <freerdp/codec/nsc.h>

static unsigned long long ns(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (unsigned long long)t.tv_sec * 1000000000 + t.tv_nsec;
}
static void record(const char *kind, unsigned long long start, UINT32 width, UINT32 height, BOOL ok)
{
    const char *path = getenv("LEMON_RDP_COPY_TRACE");
    if (!path) return;
    unsigned long long end = ns();
    char line[256];
    int n = snprintf(line, sizeof(line), "{\"event\":\"%s\",\"start_ns\":%llu,\"duration_ns\":%llu,\"pixels\":%llu,\"ok\":%d}\n",
                     kind, start, end-start, (unsigned long long)width*height, !!ok);
    int fd = open(path, O_WRONLY | O_APPEND | O_CREAT | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd >= 0) {
        if (write(fd, line, n) != n) perror("RDP trace write");
        close(fd);
    } else perror("RDP trace open");
}
#define RESOLVE(name) __typeof__(&name) real = dlsym(RTLD_NEXT, #name); \
    if (!real) { fprintf(stderr, "RDP_TRACE_SYMBOL_MISSING %s\n", #name); return FALSE; }
BOOL freerdp_image_copy(BYTE *dst, DWORD df, UINT32 ds, UINT32 x, UINT32 y, UINT32 w, UINT32 h,
                       const BYTE *src, DWORD sf, UINT32 ss, UINT32 sx, UINT32 sy,
                       const gdiPalette *pal, UINT32 flags)
{
    RESOLVE(freerdp_image_copy);
    unsigned long long start = ns();
    BOOL ok = real(dst, df, ds, x, y, w, h, src, sf, ss, sx, sy, pal, flags);
    record("copy_rectangle", start, w, h, ok);
    return ok;
}
BOOL freerdp_image_scale(BYTE *dst, DWORD df, UINT32 ds, UINT32 x, UINT32 y, UINT32 w, UINT32 h,
                        const BYTE *src, DWORD sf, UINT32 ss, UINT32 sx, UINT32 sy, UINT32 sw, UINT32 sh)
{
    RESOLVE(freerdp_image_scale);
    unsigned long long start = ns();
    BOOL ok = real(dst, df, ds, x, y, w, h, src, sf, ss, sx, sy, sw, sh);
    record("scale_rectangle", start, w, h, ok);
    return ok;
}
BOOL nsc_process_message(NSC_CONTEXT *context, UINT16 bpp, UINT32 width, UINT32 height,
                         const BYTE *data, UINT32 length, BYTE *dst, UINT32 format,
                         UINT32 stride, UINT32 x, UINT32 y, UINT32 w, UINT32 h, UINT32 flip)
{
    RESOLVE(nsc_process_message);
    unsigned long long start = ns();
    BOOL ok = real(context, bpp, width, height, data, length, dst, format, stride, x, y, w, h, flip);
    record("nsc_decode_rectangle", start, w, h, ok);
    return ok;
}
