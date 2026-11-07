#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <wayland-client-core.h>

#ifdef PROVIDER
struct wl_proxy *wl_proxy_marshal_flags(struct wl_proxy *proxy, uint32_t opcode,
    const struct wl_interface *interface, uint32_t version, uint32_t flags, ...)
{
    if (proxy != (void *)0x1234 || opcode != 99 || interface || version != 17 || flags != 3)
        abort();
    va_list args;
    va_start(args, flags);
    for (unsigned long i = 1; i <= 12; i++) {
        if (va_arg(args, unsigned long) != i * 101 || va_arg(args, double) != i + .25)
            abort();
    }
    va_end(args);
    return proxy;
}
#else
int main(void)
{
    struct wl_proxy *result = wl_proxy_marshal_flags((void *)0x1234, 99, NULL, 17, 3,
        101UL,1.25,202UL,2.25,303UL,3.25,404UL,4.25,505UL,5.25,606UL,6.25,
        707UL,7.25,808UL,8.25,909UL,9.25,1010UL,10.25,1111UL,11.25,1212UL,12.25);
    if (result != (void *)0x1234)
        return 1;
    puts("TRACE_AARCH64_VARIADIC_ABI_PASS integers=12 doubles=12 stack_arguments=yes");
    return 0;
}
#endif
