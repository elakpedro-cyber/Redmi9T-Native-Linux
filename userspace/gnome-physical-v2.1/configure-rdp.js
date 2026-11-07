import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const runtime = GLib.getenv('XDG_RUNTIME_DIR');
const common = new Gio.Settings({schema_id: 'org.gnome.desktop.remote-desktop.rdp'});
// Seed both valid paths in one transaction before grdctl constructs GrdSettings.
common.delay();
common.set_string('tls-key', `${runtime}/rdp-test.key`);
common.set_string('tls-cert', `${runtime}/rdp-test.crt`);
common.apply();
const headless = new Gio.Settings({schema_id: 'org.gnome.desktop.remote-desktop.rdp.headless'});
headless.delay();
headless.set_strv('auth-methods', ['credentials']);
headless.set_boolean('negotiate-port', false);
headless.set_boolean('enable', false);
headless.apply();
Gio.Settings.sync();
print('RDP_SETTINGS_PREPARED TLS paths and credentials-only authentication');
