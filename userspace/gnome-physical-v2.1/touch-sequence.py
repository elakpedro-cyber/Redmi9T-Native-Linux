"""Validate recorded/synthetic Wayland touch sequences; opens no input devices."""
def validate(events):
    active = set()
    for kind, contact in events:
        if kind == 'down':
            if not isinstance(contact, int) or contact < 0 or contact in active:
                raise ValueError('Invalid or repeated contact ID')
            active.add(contact)
        elif kind in ('motion', 'up'):
            if contact not in active:
                raise ValueError('Contact has no matching down')
            if kind == 'up': active.remove(contact)
        elif kind == 'cancel':
            active.clear()
        else:
            raise ValueError('Unknown touch event')
    if active:
        raise ValueError('Contacts remain active at disconnect')
