import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

// GNOME Shell 50 does not register with legacy gnome-session 48. This launcher
// owns the actual Shell child and its session lifecycle, not a placeholder service.
const bus = Gio.bus_get_sync(Gio.BusType.SESSION, null);
const loop = new GLib.MainLoop(null, false);
const child = Gio.Subprocess.new(['/usr/bin/gnome-shell', ...ARGV], Gio.SubprocessFlags.NONE);
let client = null;
let failed = false;
let stopping = false;
function stop() {
    stopping = true;
    child.send_signal(15);
    return GLib.SOURCE_CONTINUE;
}
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 15, stop);
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 1, stop);
child.wait_async(null, (process, result) => {
    process.wait_finish(result);
    if (!process.get_successful() && !stopping)
        failed = true;
    loop.quit();
});
const watch = Gio.bus_watch_name_on_connection(bus, 'org.gnome.Shell',
    Gio.BusNameWatcherFlags.NONE, (_bus, _name, owner) => {
        if (client)
            return;
        try {
            const [pid] = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                'org.freedesktop.DBus', 'GetConnectionUnixProcessID',
                new GLib.Variant('(s)', [owner]), null, Gio.DBusCallFlags.NONE, 3000, null).deepUnpack();
            if (String(pid) !== child.get_identifier())
                throw new Error('Shell D-Bus owner differs from launcher child');
            [client] = bus.call_sync('org.gnome.SessionManager', '/org/gnome/SessionManager',
                'org.gnome.SessionManager', 'RegisterClient', new GLib.Variant('(ss)',
                    ['lemon-headless-shell', GLib.getenv('DESKTOP_AUTOSTART_ID') ?? '']),
                null, Gio.DBusCallFlags.NONE, 3000, null).deepUnpack();
            print(`SHELL_COMPONENT_REGISTERED pid=${pid}`);
            bus.signal_subscribe('org.gnome.SessionManager', 'org.gnome.SessionManager.ClientPrivate',
                null, client, null, Gio.DBusSignalFlags.NONE, (_c, _s, _p, _i, signal) => {
                    if (signal === 'QueryEndSession' || signal === 'EndSession') {
                        bus.call('org.gnome.SessionManager', client,
                            'org.gnome.SessionManager.ClientPrivate', 'EndSessionResponse',
                            new GLib.Variant('(bs)', [true, '']), null,
                            Gio.DBusCallFlags.NONE, 3000, null, null);
                    }
                    if (signal === 'EndSession' || signal === 'Stop')
                        stop();
                });
        } catch (error) {
            console.error(`SHELL_COMPONENT_ERROR ${error.message}`);
            failed = true;
            stop();
        }
    }, () => {});
loop.run();
Gio.bus_unwatch_name(watch);
if (failed)
    throw new Error('Shell component exited unsuccessfully');
