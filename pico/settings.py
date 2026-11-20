"""Settings: defaults, overridden by config.toml, plus Wi-Fi from secret.toml."""
import toml

# (section, key in file, setting name, default)
_FIELDS = (
    ('network', 'port', 'port', 5555),
    ('network', 'hostname', 'hostname', 'pico-focuser'),
    ('device', 'name', 'name', 'Pico Focuser'),
    ('device', 'location', 'location', 'Observatory'),
    ('device', 'max_step', 'max_step', 100000),
    ('device', 'start_position', 'start_position', 50000),
    ('device', 'max_increment', 'max_increment', 100000),
    ('device', 'steps_per_sec', 'steps_per_sec', 800),
    ('device', 'reverse', 'reverse', False),
    ('device', 'hold_when_idle', 'hold_when_idle', True),
    ('pins', 'step', 'step_pin', 16),
    ('pins', 'dir', 'dir_pin', 20),
    ('pins', 'en', 'en_pin', 21),
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

    wifi = _read(secret_path).get('wifi', {})
    ssid = wifi.get('ssid', '')
    if ssid == _PLACEHOLDER_SSID:
        ssid = ''
    settings['wifi_ssid'] = ssid
    settings['wifi_password'] = wifi.get('password', '') if ssid else ''
    return settings
