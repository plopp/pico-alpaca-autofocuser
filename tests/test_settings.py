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
