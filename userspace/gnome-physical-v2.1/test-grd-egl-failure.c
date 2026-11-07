#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <epoxy/egl.h>
#include "grd-egl-thread.h"
/* Force the first EGL initialization failure, never create a GPU context. */
bool epoxy_has_egl_extension(EGLDisplay display, const char *extension)
{
    (void)display; (void)extension;
    return false;
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    int fd = open("/dev/null", O_RDONLY);
    assert(fd >= 0 && dup2(fd, 0) == 0);
    if (fd != 0) close(fd);
    GError *error = NULL;
    assert(grd_egl_thread_new(&error) == NULL);
    assert(error && strstr(error->message, "EGL_EXT_platform_base"));
    int intact = fcntl(0, F_GETFD) != -1;
    printf("FORCED_EGL_FAILURE stdin_intact=%d expected=%s error=%s\n", intact, argv[1], error->message);
    assert(intact == (strcmp(argv[1], "fixed") == 0));
    g_error_free(error);
    return 0;
}
