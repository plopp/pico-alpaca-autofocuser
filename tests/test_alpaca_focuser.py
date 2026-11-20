import pytest

from conftest import UNIQUE_ID

API = '/api/v1/focuser/0/'


def value(client, member):
    return client.get(API + member)[1]


def test_static_focuser_values(client):
    client.connect()
    assert value(client, 'absolute')['Value'] is True
    assert value(client, 'maxstep')['Value'] == 100000
    assert value(client, 'maxincrement')['Value'] == 100000
    assert value(client, 'tempcompavailable')['Value'] is False
    assert value(client, 'tempcomp')['Value'] is False
    assert value(client, 'stepsize')['ErrorNumber'] == 0x400
    assert value(client, 'temperature')['ErrorNumber'] == 0x400


def test_position_needs_connection(client):
    assert value(client, 'position')['ErrorNumber'] == 0x407


def test_tempcomp_put(client):
    client.connect()
    assert client.put(API + 'tempcomp', {'TempComp': 'false'})[1]['ErrorNumber'] == 0
    assert client.put(API + 'tempcomp', {'TempComp': 'true'})[1]['ErrorNumber'] == 0x400


def test_move_and_position(client):
    client.connect()
    _, body = client.put(API + 'move', {'Position': '50020'})
    assert body['ErrorNumber'] == 0
    assert value(client, 'ismoving')['Value'] is True
    client.timer.tick(50)
    assert value(client, 'ismoving')['Value'] is False
    assert value(client, 'position')['Value'] == 50020


def test_halt_member(client):
    client.connect()
    client.put(API + 'move', {'Position': '50020'})
    client.timer.tick(5)
    assert client.put(API + 'halt')[1]['ErrorNumber'] == 0
    assert value(client, 'ismoving')['Value'] is False
    assert value(client, 'position')['Value'] == 50005


@pytest.mark.parametrize('bad', ['12.5', 'abc', ''])
def test_move_bad_position_format(client, bad):
    client.connect()
    status, _ = client.put(API + 'move', {'Position': bad})
    assert status == 400


@pytest.mark.parametrize('bad', ['-1', '100001'])
def test_move_bad_position_range(client, bad):
    client.connect()
    _, body = client.put(API + 'move', {'Position': bad})
    assert body['ErrorNumber'] == 0x401
    assert client.stepper.is_moving is False


def test_move_not_connected(client):
    _, body = client.put(API + 'move', {'Position': '50010'})
    assert body['ErrorNumber'] == 0x407


def test_management(client):
    _, body = client.get('/management/apiversions')
    assert body['Value'] == [1]
    _, body = client.get('/management/v1/description')
    for key in ('ServerName', 'Manufacturer', 'ManufacturerVersion', 'Location'):
        assert key in body['Value']
    _, body = client.get('/management/v1/configureddevices')
    assert body['Value'] == [{'DeviceName': 'Pico Focuser', 'DeviceType': 'Focuser',
                              'DeviceNumber': 0, 'UniqueID': UNIQUE_ID}]


@pytest.mark.parametrize('path', ['/setup', '/setup/v1/focuser/0/setup'])
def test_setup_pages(client, path):
    status, body = client.get(path)
    assert status == 200
    assert '<html' in body.lower()
    assert '50000' in body
