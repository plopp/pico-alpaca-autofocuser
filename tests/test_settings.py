import pytest

from settings import load_settings


def _load(tmp_path, config=None, secret=None):
    cfg = tmp_path / 'config.toml'
    sec = tmp_path / 'secret.toml'
    if config is not None:
        cfg.write_text(config)
    if secret is not None:
        sec.write_text(secret)
    return load_settings(str(cfg), str(sec))


def test_defaults_when_no_files(tmp_path):
    s = _load(tmp_path)
    assert s['port'] == 5555
    assert s['max_step'] == 100000
    assert s['start_position'] == 50000
    assert s['max_increment'] == 100000
    assert s['steps_per_sec'] == 800
    assert s['reverse'] is False
    assert s['hold_when_idle'] is True
    assert (s['step_pin'], s['dir_pin'], s['en_pin']) == (16, 20, 21)
    assert s['name'] == 'Pico Focuser'
    assert s['hostname'] == 'pico-focuser'
    assert (s['temp_pin'], s['temp_poll_s']) == (22, 5)


def test_config_overrides(tmp_path):
    s = _load(tmp_path, config='[device]\nsteps_per_sec = 400\n')
    assert s['steps_per_sec'] == 400
    assert s['max_step'] == 100000


def test_start_position_defaults_to_middle_of_max_step(tmp_path):
    s = _load(tmp_path, config='[device]\nmax_step = 2000\n')
    assert s['max_step'] == 2000
    assert s['start_position'] == 1000


@pytest.mark.parametrize('start,expected', [(5000, 2000), (-5, 0), (700, 700)])
def test_start_position_clamped_to_range(tmp_path, start, expected):
    s = _load(tmp_path, config='[device]\nmax_step = 2000\nstart_position = {}\n'.format(start))
    assert s['start_position'] == expected


def test_missing_secret_gives_empty_wifi(tmp_path):
    s = _load(tmp_path)
    assert s['wifi_ssid'] == ''
    assert s['wifi_password'] == ''


def test_placeholder_ssid_is_empty(tmp_path):
    s = _load(tmp_path, secret='[wifi]\nssid = "your-network-name"\npassword = "x"\n')
    assert s['wifi_ssid'] == ''


def test_secret_is_read(tmp_path):
    s = _load(tmp_path, secret='[wifi]\nssid = "home"\npassword = "pw"\n')
    assert (s['wifi_ssid'], s['wifi_password']) == ('home', 'pw')


from settings import EDITABLE, save_settings, validate_settings  # noqa: E402

GOOD = {'name': 'Scope 1', 'max_step': '20000', 'start_position': '10000',
        'steps_per_sec': '600', 'reverse': 'true', 'hold_when_idle': 'false'}


def test_validate_accepts_good_values():
    v = validate_settings(GOOD)
    assert v == {'name': 'Scope 1', 'max_step': 20000, 'start_position': 10000,
                 'steps_per_sec': 600, 'reverse': True, 'hold_when_idle': False}
    assert set(v) == set(EDITABLE)


def test_validate_unchecked_checkbox_is_false():
    values = dict(GOOD)
    del values['reverse']                  # HTML forms omit unchecked boxes
    values['hold_when_idle'] = 'on'
    v = validate_settings(values)
    assert v['reverse'] is False and v['hold_when_idle'] is True


@pytest.mark.parametrize('key,bad', [('max_step', 'abc'), ('max_step', '50'),
                                     ('steps_per_sec', '0'), ('steps_per_sec', '9000'),
                                     ('start_position', '30000'), ('name', ''),
                                     ('start_position', '-1'), ('name', 'Scope #1')])
def test_validate_rejects_bad_values(key, bad):
    values = dict(GOOD)
    values[key] = bad
    with pytest.raises(ValueError):
        validate_settings(values)


SHIPPED = '''# Pico Alpaca focuser settings. Wi-Fi credentials go in secret.toml.

[network]
port = 5555
hostname = "pico-focuser"

[device]
name = "Pico Focuser"
location = "Observatory"
max_step = 100000          # 1/8 microstep: 1600 steps per motor turn
# start_position = 50000   # Position at every power-up; default is max_step / 2
max_increment = 100000
steps_per_sec = 800
reverse = false            # Flip if "out" moves the wrong way
hold_when_idle = true      # Keep the driver enabled between moves while connected

[pins]
step = 16
dir = 20
en = 21                    # Active low
'''


def test_save_settings_round_trip(tmp_path):
    cfg = tmp_path / 'config.toml'
    cfg.write_text(SHIPPED)
    save_settings(str(cfg), validate_settings(GOOD))
    s = load_settings(str(cfg), str(tmp_path / 'none.toml'))
    assert (s['name'], s['max_step'], s['start_position']) == ('Scope 1', 20000, 10000)
    assert (s['steps_per_sec'], s['reverse'], s['hold_when_idle']) == (600, True, False)
    text = cfg.read_text()
    assert 'port = 5555' in text and '[pins]' in text and 'location = "Observatory"' in text
    assert '# 1/8 microstep: 1600 steps per motor turn' in text      # comments kept


def test_save_adds_missing_keys(tmp_path):
    cfg = tmp_path / 'config.toml'
    cfg.write_text('[network]\nport = 5555\n')
    save_settings(str(cfg), validate_settings(GOOD))
    s = load_settings(str(cfg), str(tmp_path / 'none.toml'))
    assert s['start_position'] == 10000 and s['port'] == 5555
