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
    s = _load(tmp_path, config='[device]\nmax_step = 2000\n')
    assert s['max_step'] == 2000
    assert s['start_position'] == 50000


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
