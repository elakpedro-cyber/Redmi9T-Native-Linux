import Gtk from 'gi://Gtk?version=4.0';

const app = new Gtk.Application({application_id: 'org.lemon.RdpInputProbe'});
app.connect('activate', () => {
    print('GTK_PROBE_ACTIVATED');
    const window = new Gtk.ApplicationWindow({
        application: app, title: 'RDP input check', default_width: 440, default_height: 600,
    });
    const button = new Gtk.Button({label: 'Click here, then press X'});
    window.set_child(button);
    button.connect('clicked', () => {
        print('RDP_MOUSE_OK');
        button.label = 'Mouse received. Press X.';
    });
    const keys = new Gtk.EventControllerKey();
    keys.connect('key-pressed', (_controller, keyval) => {
        if (keyval === 120 || keyval === 88) {
            print('RDP_KEYBOARD_OK');
            button.label = 'Mouse and keyboard received.';
            return true;
        }
        return false;
    });
    window.add_controller(keys);
    window.connect('map', () => print('GTK_PROBE_MAPPED'));
    window.present();
});
app.run([]);
