"""Apply narrowly scoped fixes to the exact JS extracted from the frozen v2 Shell."""
import difflib
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root / 'logs/gnome-physical-v2.1'
output = Path(__file__).with_name('shell-ui')
output.mkdir(exist_ok=True)
main = (source / 'actual-main.js').read_text()
start = main.index('async function _notifyGnomeSessionReady() {')
end = main.index('\nfunction _handleShowWelcomeScreen()', start)
fixed = '''async function _notifyGnomeSessionReady() {
    let ending = false;
    global.context.connect('prepare-shutdown', () => (ending = true));
    try {
        const reply = await Gio.DBus.session.call(
            'org.gnome.SessionManager', '/org/gnome/SessionManager',
            'org.gnome.SessionManager', 'RegisterClient',
            new GLib.Variant('(ss)', ['org.gnome.Shell.desktop', '']), null,
            Gio.DBusCallFlags.NONE, 3000, null);
        const [client] = reply.deepUnpack();
        print(`LEMON_SESSION_REGISTERED client=${client}`);
        const subscription = Gio.DBus.session.signal_subscribe(
            'org.gnome.SessionManager', 'org.gnome.SessionManager.ClientPrivate',
            null, client, null, Gio.DBusSignalFlags.NONE,
            async (_connection, _sender, _path, _iface, signal) => {
                if (signal === 'QueryEndSession' || signal === 'EndSession') {
                    try {
                        await Gio.DBus.session.call(
                            'org.gnome.SessionManager', client,
                            'org.gnome.SessionManager.ClientPrivate', 'EndSessionResponse',
                            new GLib.Variant('(bs)', [true, '']), null,
                            Gio.DBusCallFlags.NONE, 1500, null);
                        print(`LEMON_SESSION_ACK ${signal}`);
                    } catch (error) {
                        logError(error, `Session response failed: ${signal}`);
                    }
                }
                if ((signal === 'EndSession' || signal === 'Stop') && !ending) {
                    ending = true;
                    global.context.terminate();
                }
            });
        global.connect('shutdown', () => Gio.DBus.session.signal_unsubscribe(subscription));
    } catch (error) {
        logError(error, 'Unable to register Shell session lifecycle');
    }
}
'''
preview = (source / 'actual-windowPreview.js').read_text()
needle = 'const scale = (origSize + activeExtraSize) / origSize;'
assert preview.count(needle) == 1
new_preview = preview.replace(needle, 'const scale = origSize > 0 ? (origSize + activeExtraSize) / origSize : 1;')
new_preview = new_preview.replace('    _restack() {\n', '    _restack() {\n        if (this._destroyed)\n            return;\n')
new_preview = new_preview.replace('} else if (this._stackAbove === null) {',
    '} else if (this._stackAbove === null || this._stackAbove._destroyed ||\n                this._stackAbove.get_parent() !== parent) {\n                this._stackAbove = null;')
new_preview = new_preview.replace('                if (above === null)\n',
    '                if (above === null || above._destroyed || above.get_parent() !== parent)\n')
records = []
remote = (source / 'actual-remoteAccess.js').read_text()
split = remote.index('export const ScreenSharingIndicator')
head, indicator = remote[:split], remote[split:]
indicator = indicator.replace("this._controller?.connect('new-handle',\n            (o, handle) => this._onNewHandle(handle));",
    "this._controller?.connectObject('new-handle',\n            (o, handle) => this._onNewHandle(handle), this);")
indicator = indicator.replace("handle.connect('stopped', () => {\n            this._handles.delete(handle);\n            this._sync();\n        });",
    "handle.connectObject('stopped', () => {\n            this._handles.delete(handle);\n            this._sync();\n        }, this);")
indicator = indicator.replace('        this._sync();\n\n        this._clickGesture',
    "        this.connect('destroy', () => {\n            if (this._hideIndicatorId) {\n                GLib.source_remove(this._hideIndicatorId);\n                delete this._hideIndicatorId;\n            }\n        });\n        this._sync();\n\n        this._clickGesture")
for name, original, modified in [('main.js', main, main[:start]+fixed+main[end:]),
                                  ('windowPreview.js', preview, new_preview),
                                  ('status/remoteAccess.js', remote, head+indicator)]:
    (output/name).parent.mkdir(parents=True, exist_ok=True)
    (output/name).write_bytes(modified.encode())
    patch = ''.join(difflib.unified_diff(original.splitlines(True), modified.splitlines(True),
                                       fromfile='v2/'+name, tofile='v2.1/'+name))
    (output/(name+'.patch')).write_bytes(patch.encode())
    records.append({'file': name, 'base_sha256': hashlib.sha256(original.encode()).hexdigest(),
                    'patched_sha256': hashlib.sha256(modified.encode()).hexdigest()})
(output/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
print('SHELL_OVERLAY_BUILT', records)
