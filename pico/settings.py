"""Settings: defaults, overridden by config.toml, plus Wi-Fi from secret.toml."""
import toml

# (section, key in file, setting name, default)
_FIELDS = (
    ('network', 'port', 'port', 5555),
    ('network', 'hostname', 'hostname', 'pico-focuser'),
    ('device', 'name', 'name', 'Pico Focuser'),
    ('device', 'location', 'location', 'Observatory'),
    ('device', 'max_step', 'max_step', 100000),
    ('device', 'start_position', 'start_position', None),   # None: middle of range
    ('device', 'max_increment', 'max_increment', 100000),
    ('device', 'steps_per_sec', 'steps_per_sec', 800),
    ('device', 'reverse', 'reverse', False),
    ('device', 'hold_when_idle', 'hold_when_idle', True),
    ('pins', 'step', 'step_pin', 16),
    ('pins', 'dir', 'dir_pin', 20),
    ('pins', 'en', 'en_pin', 21),
    ('temperature', 'pin', 'temp_pin', 22),
    ('temperature', 'poll_s', 'temp_poll_s', 5),
)

_PLACEHOLDER_SSID = 'your-network-name'


def _read(path):
    try:
        return toml.load(path)
    except OSError:
        return {}


def load_settings(config_path='config.toml', secret_path='secret.toml'):
    config = _read(config_path)
    settings = {}
    for section, key, name, default in _FIELDS:
        settings[name] = config.get(section, {}).get(key, default)

    # Start in the middle of the range unless set; never outside 0..max_step
    if settings['start_position'] is None:
        settings['start_position'] = settings['max_step'] // 2
    settings['start_position'] = max(0, min(settings['start_position'], settings['max_step']))

    wifi = _read(secret_path).get('wifi', {})
    ssid = wifi.get('ssid', '')
    if ssid == _PLACEHOLDER_SSID:
        ssid = ''
    settings['wifi_ssid'] = ssid
    settings['wifi_password'] = wifi.get('password', '') if ssid else ''
    return settings


# --- Editing from the web page -------------------------------------------------------
EDITABLE = ('name', 'max_step', 'start_position', 'steps_per_sec', 'reverse', 'hold_when_idle')
_BOOL_TRUE = ('true', 'on', '1', 'yes')


def _int(values, key, low, high):
    raw = str(values.get(key, '')).strip()
    digits = raw[1:] if raw[:1] == '-' else raw
    if not digits.isdigit():
        raise ValueError('{} must be a whole number'.format(key))
    value = int(raw)
    if not low <= value <= high:
        raise ValueError('{} must be between {} and {}'.format(key, low, high))
    return value


def validate_settings(values):
    """Check form values; return them typed. Raises ValueError with a readable message."""
    name = str(values.get('name', '')).strip()
    if not 1 <= len(name) <= 40 or any(c in name for c in '"#\n'):
        raise ValueError('name must be 1-40 characters, without " or #')
    max_step = _int(values, 'max_step', 100, 1000000)
    return {
        'name': name,
        'max_step': max_step,
        'start_position': _int(values, 'start_position', 0, max_step),
        'steps_per_sec': _int(values, 'steps_per_sec', 1, 5000),
        # An unchecked HTML checkbox is simply missing from the form
        'reverse': str(values.get('reverse', 'false')).lower() in _BOOL_TRUE,
        'hold_when_idle': str(values.get('hold_when_idle', 'false')).lower() in _BOOL_TRUE,
    }


def _toml_value(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    return '"{}"'.format(value)


def save_settings(path, values):
    """Write validated values into the [device] section of config.toml, keeping every other
    line and comment. Written to a temp file and renamed, so a power cut can't half-write it."""
    import os
    try:
        with open(path) as f:
            lines = f.read().split('\n')
    except OSError:
        lines = []
    pending = dict(values)
    section, device_header = None, None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            section = stripped[1:-1].strip()
            if section == 'device':
                device_header = i
            continue
        if section != 'device' or '=' not in stripped or stripped.startswith('#'):
            continue
        key = stripped.split('=', 1)[0].strip()
        if key in pending:
            comment = line[line.index('#'):] if '#' in line.split('=', 1)[1] else ''
            text = '{} = {}'.format(key, _toml_value(pending.pop(key)))
            lines[i] = (text.ljust(27) + comment) if comment else text
    new_lines = ['{} = {}'.format(k, _toml_value(v)) for k, v in pending.items()]
    if new_lines:
        if device_header is None:
            if lines and lines[-1] != '':
                lines.append('')
            lines += ['[device]'] + new_lines
        else:
            lines[device_header + 1:device_header + 1] = new_lines
    tmp = path + '.new'
    with open(tmp, 'w') as f:
        f.write('\n'.join(lines))
    os.rename(tmp, path)
