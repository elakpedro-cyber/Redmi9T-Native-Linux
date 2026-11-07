#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <pipewire/stream.h>
#include <spa/buffer/buffer.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client-core.h>

static int trace_fd = -1;
static void *marshal;
static int (*queue_buffer)(struct pw_stream *, struct pw_buffer *);
static _Thread_local int tracing;

static void event(const char *name, unsigned id, unsigned bytes)
{
    if (trace_fd < 0 || tracing)
        return;
    tracing = 1;
    struct timespec now;
    char line[256];
    clock_gettime(CLOCK_MONOTONIC, &now);
    long long ns = now.tv_sec * 1000000000LL + now.tv_nsec;
    int size = snprintf(line, sizeof(line),
        "{\"event\":\"%s\",\"ns\":%lld,\"pid\":%d,\"id\":%u,\"bytes\":%u}\n",
        name, ns, getpid(), id, bytes);
    if (size > 0 && size < (int)sizeof(line))
        (void)write(trace_fd, line, size);
    tracing = 0;
}

__attribute__((constructor)) static void setup(void)
{
    marshal = dlsym(RTLD_NEXT, "wl_proxy_marshal_flags");
    queue_buffer = dlsym(RTLD_NEXT, "pw_stream_queue_buffer");
    const char *file = getenv("LEMON_FRAME_TRACE");
    if (file)
        trace_fd = open(file, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    event("clock_ticks", (unsigned)sysconf(_SC_CLK_TCK), 0);
}

void *lemon_trace_wayland(struct wl_proxy *proxy, unsigned opcode)
{
    if (!marshal)
        _exit(126);
    if (opcode == 6 && !strcmp(wl_proxy_get_class(proxy), "wl_surface"))
        event("wayland_surface_commit", wl_proxy_get_id(proxy), 0);
    return marshal;
}

int pw_stream_queue_buffer(struct pw_stream *stream, struct pw_buffer *buffer)
{
    if (!queue_buffer)
        _exit(126);
    if (buffer && buffer->buffer && buffer->buffer->n_datas) {
        struct spa_data *data = &buffer->buffer->datas[0];
        if (data->chunk && data->chunk->size &&
            !(data->chunk->flags & SPA_CHUNK_FLAG_CORRUPTED))
            event("pipewire_nonempty_buffer", pw_stream_get_node_id(stream), data->chunk->size);
    }
    return queue_buffer(stream, buffer);
}
