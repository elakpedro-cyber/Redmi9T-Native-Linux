#define _GNU_SOURCE
#include <dlfcn.h>
#include <gio/gio.h>
#include <stdio.h>
#include <time.h>

GVariant *g_dbus_connection_call_sync(GDBusConnection *connection, const gchar *bus,
    const gchar *path, const gchar *interface, const gchar *method, GVariant *parameters,
    const GVariantType *reply_type, GDBusCallFlags flags, gint timeout,
    GCancellable *cancellable, GError **error)
{
    static GVariant *(*call)(GDBusConnection *, const gchar *, const gchar *, const gchar *,
        const gchar *, GVariant *, const GVariantType *, GDBusCallFlags, gint,
        GCancellable *, GError **);
    if (!call)
        call = dlsym(RTLD_NEXT, "g_dbus_connection_call_sync");
    gint64 before = g_get_monotonic_time();
    fprintf(stderr, "DBUS_CONNECTION_CALL interface=%s method=%s start_us=%lld\n",
            interface ? interface : "(none)", method, (long long)before);
    GVariant *result = call(connection, bus, path, interface, method, parameters,
        reply_type, flags, timeout, cancellable, error);
    fprintf(stderr, "DBUS_CONNECTION_RETURN method=%s elapsed_us=%lld ok=%d error_code=%d\n",
            method, (long long)(g_get_monotonic_time()-before), result != NULL,
            error && *error ? (*error)->code : 0);
    return result;
}

GVariant *g_dbus_proxy_call_sync(GDBusProxy *proxy, const gchar *method,
                                GVariant *parameters, GDBusCallFlags flags,
                                gint timeout, GCancellable *cancellable, GError **error)
{
    static GVariant *(*call)(GDBusProxy *, const gchar *, GVariant *, GDBusCallFlags,
                             gint, GCancellable *, GError **);
    if (!call)
        call = dlsym(RTLD_NEXT, "g_dbus_proxy_call_sync");
    gint64 before = g_get_monotonic_time();
    fprintf(stderr, "DBUS_CALL interface=%s method=%s start_us=%lld\n",
            g_dbus_proxy_get_interface_name(proxy), method, (long long)before);
    GVariant *result = call(proxy, method, parameters, flags, timeout, cancellable, error);
    fprintf(stderr, "DBUS_RETURN method=%s elapsed_us=%lld ok=%d error_code=%d\n",
            method, (long long)(g_get_monotonic_time() - before), result != NULL,
            error && *error ? (*error)->code : 0);
    return result;
}
