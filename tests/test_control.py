import pytest

from temperature import TemperatureStale, TemperatureUnavailable

API = '/api/v1/focuser/0/'


class FakeSensor:
    def __init__(self, value=12.5, error=None):
        self.value, self.error = value, error
        self.available = error is not TemperatureUnavailable

    def read(self):
        if self.error:
            raise self.error('no reading')
        return self.value


# --- Alpaca Temperature -------------------------------------------------------------

def test_alpaca_temperature_with_sensor(client):
    client.state.sensor = FakeSensor(12.5)
    client.connect()
    assert client.get(API + 'temperature')[1]['Value'] == 12.5
    names = [i['Name'] for i in client.get(API + 'devicestate')[1]['Value']]
    assert 'Temperature' in names


def test_alpaca_temperature_without_sensor(client):
    client.connect()
    assert client.get(API + 'temperature')[1]['ErrorNumber'] == 0x400
    names = [i['Name'] for i in client.get(API + 'devicestate')[1]['Value']]
    assert 'Temperature' not in names


def test_alpaca_temperature_sensor_never_found(client):
    client.state.sensor = FakeSensor(error=TemperatureUnavailable)
    client.connect()
    assert client.get(API + 'temperature')[1]['ErrorNumber'] == 0x400


def test_alpaca_temperature_stale(client):
    client.state.sensor = FakeSensor(error=TemperatureStale)
    client.connect()
    assert client.get(API + 'temperature')[1]['ErrorNumber'] == 0x500


# --- Control API --------------------------------------------------------------------

def test_status_json(client):
    client.state.sensor = FakeSensor(7.25)
    status, body = client.get('/control/status')
    assert status == 200
    assert body['position'] == 50000 and body['target'] == 50000
    assert body['moving'] is False and body['connected'] is False
    assert body['temperature'] == 7.25 and body['max_step'] == 100000
    assert body['settings']['steps_per_sec'] == 800


def test_status_temperature_null_without_sensor(client):
    assert client.get('/control/status')[1]['temperature'] is None


def test_move_and_jog(client):
    assert client.post('/control/move', {'position': '50020'})[0] == 200
    client.timer.tick(30)
    assert client.stepper.position == 50020
    assert client.post('/control/jog', {'steps': '-100'})[0] == 200
    client.timer.tick(200)
    assert client.stepper.position == 49920


def test_jog_clamps_to_range(client):
    client.stepper.set_position(99500)
    client.post('/control/jog', {'steps': '1000'})
    assert client.stepper.target == 100000
    client.stepper.halt()
    client.stepper.set_position(300)
    client.post('/control/jog', {'steps': '-1000'})
    assert client.stepper.target == 0


@pytest.mark.parametrize('path,data', [('/control/move', {'position': 'abc'}),
                                       ('/control/move', {'position': '100001'}),
                                       ('/control/jog', {'steps': '1.5'})])
def test_bad_move_values(client, path, data):
    assert client.post(path, data)[0] == 400


def test_halt(client):
    client.post('/control/move', {'position': '50100'})
    client.timer.tick(5)
    assert client.post('/control/halt')[0] == 200
    assert client.stepper.is_moving is False


def test_reset_position(client):
    client.stepper.set_position(61000)
    assert client.post('/control/reset')[0] == 200
    assert client.stepper.position == 50000


def test_reset_refused_while_moving(client):
    client.post('/control/move', {'position': '50100'})
    client.timer.tick(5)
    status, body = client.post('/control/reset')
    assert status == 400
    assert client.stepper.position == 50005


def test_manual_move_when_disconnected_releases_driver(client):
    client.post('/control/move', {'position': '50003'})
    assert client.en.value() == 0
    client.timer.tick(10)
    assert client.en.value() == 1


def test_manual_move_when_connected_keeps_hold(client):
    client.connect()
    client.post('/control/move', {'position': '50003'})
    client.timer.tick(10)
    assert client.en.value() == 0


SETTINGS = {'name': 'Scope 1', 'max_step': '20000', 'start_position': '10000',
            'steps_per_sec': '400', 'reverse': 'on', 'hold_when_idle': 'on'}


def test_settings_get(client):
    status, body = client.get('/control/settings')
    assert status == 200 and body['max_step'] == 100000


def test_settings_post_saves_and_applies(client):
    status, body = client.post('/control/settings', SETTINGS)
    assert status == 200, body
    assert 'max_step = 20000' in client.config.read_text()
    assert body['restart_needed'] is True              # name/max_step/start need a restart
    client.post('/control/move', {'position': '50001'})
    assert client.timer.freq == 400                    # speed applied live


def test_settings_post_rejects_bad_values(client):
    before = client.config.read_text()
    bad = dict(SETTINGS, steps_per_sec='0')
    status, body = client.post('/control/settings', bad)
    assert status == 400
    assert client.config.read_text() == before


def test_restart_calls_hook(client):
    import time
    assert client.post('/control/restart')[0] == 200      # answered before restarting
    deadline = time.time() + 2
    while not client.restarts and time.time() < deadline:
        time.sleep(0.05)
    assert client.restarts == [1]


@pytest.mark.parametrize('path', ['/setup', '/setup/v1/focuser/0/setup'])
def test_control_page_loads(client, path):
    status, body = client.get(path)
    assert status == 200
    for word in ('Jog', 'Move', 'Reset', 'Halt', 'Settings', '/control/status'):
        assert word in body, word


def test_nina_connecting_during_manual_move_keeps_hold(client):
    client.post('/control/move', {'position': '50010'})
    client.timer.tick(3)
    client.connect()
    client.timer.tick(20)
    assert client.en.value() == 0


def test_device_name_is_escaped_in_page(client):
    client.state.settings['name'] = '</title><script>x()</script>@JOG@'
    body = client.get('/setup')[1]
    assert '<script>x()' not in body
    assert '&lt;/title&gt;' in body
    assert body.count('onclick="jog(') == 6          # @JOG@ in the name isn't expanded


def test_restart_stops_the_motor_first(client):
    import time
    client.connect()
    client.post('/control/move', {'position': '50100'})
    client.timer.tick(3)
    assert client.post('/control/restart')[0] == 200
    assert client.stepper.is_moving is False
    assert client.en.value() == 1                     # driver off before the reset
