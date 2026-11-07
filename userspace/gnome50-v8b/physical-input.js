import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const bus = Gio.bus_get_sync(Gio.BusType.SESSION, null);
const service = 'org.gnome.Mutter.RemoteDesktop';
const iface = 'org.gnome.Mutter.RemoteDesktop.Session';
function call(path, name, method, args) {
    return bus.call_sync(service, path, name, method, args, null,
        Gio.DBusCallFlags.NONE, 3000, null);
}
const reply = call('/org/gnome/Mutter/RemoteDesktop', service, 'CreateSession', null);
const [path] = reply.deepUnpack();
function key(code, state) {
    call(path, iface, 'NotifyKeyboardKeycode', new GLib.Variant('(ub)', [code, state]));
}
function tap(code) {
    key(code, true);
    key(code, false);
}
function pause() {
    GLib.usleep(2500000);
}
function type(text) {
    for (const character of text) {
        const keysym = character === '\n' ? 0xff0d : character.codePointAt(0);
        call(path, iface, 'NotifyKeyboardKeysym', new GLib.Variant('(ub)', [keysym, true]));
        call(path, iface, 'NotifyKeyboardKeysym', new GLib.Variant('(ub)', [keysym, false]));
        GLib.usleep(35000);
    }
}
call(path, iface, 'Start', null);
try {
    tap(1);
    pause();
    type("echo GNOME_LCD_INPUT_OK\n");
    print('INPUT_ACTION=terminal command typed');
    pause();
    tap(125);
    print('INPUT_ACTION=Super overview');
    pause();
    tap(1);
    call(path, iface, 'NotifyPointerMotionRelative', new GLib.Variant('(dd)', [30.0, 20.0]));
    print('INPUT_ACTION=virtual pointer motion');
    key(125, true);
    tap(30);
    key(125, false);
    print('INPUT_ACTION=Super+A applications');
    pause();
    tap(1);
    GLib.setenv('WAYLAND_DISPLAY', 'wayland-0', true);
    Gio.Subprocess.new(['/usr/bin/gnome-control-center'], Gio.SubprocessFlags.NONE);
    print('INPUT_ACTION=Settings opened');
    pause();
    key(56, true);
    tap(15);
    key(56, false);
    print('INPUT_ACTION=Alt+Tab window switching');
} finally {
    call(path, iface, 'Stop', null);
}
