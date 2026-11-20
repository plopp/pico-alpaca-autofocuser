import pytest

API = '/api/v1/focuser/0/'


def test_response_envelope(client):
    status, body = client.get(API + 'name', ClientID=1, ClientTransactionID=7)
    assert status == 200
    assert body['Value'] == 'Pico Focuser'
    assert body['ClientTransactionID'] == 7
    assert body['ErrorNumber'] == 0
    assert body['ErrorMessage'] == ''
    _, body2 = client.get(API + 'name', ClientTransactionID=8)
    assert body2['ServerTransactionID'] > body['ServerTransactionID']


def test_missing_transaction_id_echoes_zero(client):
    _, body = client.get(API + 'name')
    assert body['ClientTransactionID'] == 0


def test_get_params_case_insensitive(client):
    _, body = client.get(API + 'name', clienttransactionid=9)
    assert body['ClientTransactionID'] == 9


def test_put_params_case_sensitive(client):
    status, _ = client.put(API + 'connected', {'connected': 'True'})
    assert status == 400


@pytest.mark.parametrize('params', [{'ClientID': '-1'}, {'ClientTransactionID': 'abc'}])
def test_bad_client_ids(client, params):
    status, _ = client.get(API + 'name', **params)
    assert status == 400


def test_bad_device_number(client):
    status, _ = client.get('/api/v1/focuser/1/name')
    assert status in (400, 404)


def test_unknown_member(client):
    status, _ = client.get(API + 'nosuchmember')
    assert status in (400, 404)


def test_identity_members(client):
    assert client.get(API + 'interfaceversion')[1]['Value'] == 4
    assert client.get(API + 'supportedactions')[1]['Value'] == []
    for member in ('driverversion', 'description', 'driverinfo'):
        value = client.get(API + member)[1]['Value']
        assert isinstance(value, str) and value


def test_connect_cycle(client):
    assert client.get(API + 'connected')[1]['Value'] is False
    assert client.connect()[1]['ErrorNumber'] == 0
    assert client.get(API + 'connected')[1]['Value'] is True
    assert client.get(API + 'connecting')[1]['Value'] is False
    assert client.en.value() == 0
    client.put(API + 'disconnect')
    assert client.get(API + 'connected')[1]['Value'] is False
    assert client.en.value() == 1

    client.put(API + 'connected', {'Connected': 'True'})
    assert client.get(API + 'connected')[1]['Value'] is True
    client.put(API + 'connected', {'Connected': 'False'})
    assert client.get(API + 'connected')[1]['Value'] is False


def test_connected_bad_bool(client):
    status, _ = client.put(API + 'connected', {'Connected': 'maybe'})
    assert status == 400


def test_not_connected_errors(client):
    _, body = client.get(API + 'devicestate')
    assert body['ErrorNumber'] == 0x407


@pytest.mark.parametrize('member,data', [
    ('action', {'Action': 'x', 'Parameters': ''}),
    ('commandblind', {'Command': 'x', 'Raw': 'false'}),
    ('commandbool', {'Command': 'x', 'Raw': 'false'}),
    ('commandstring', {'Command': 'x', 'Raw': 'false'}),
])
def test_action_members_not_implemented(client, member, data):
    client.connect()
    _, body = client.put(API + member, data)
    assert body['ErrorNumber'] == 0x400


def test_disconnect_halts_and_disables(client):
    client.connect()
    client.stepper.move_to(50100)
    client.timer.tick(5)
    client.put(API + 'disconnect')
    assert client.stepper.is_moving is False
    assert client.en.value() == 1


def test_devicestate(client):
    client.connect()
    _, body = client.get(API + 'devicestate')
    names = [item['Name'] for item in body['Value']]
    assert names == ['IsMoving', 'Position', 'TimeStamp']
