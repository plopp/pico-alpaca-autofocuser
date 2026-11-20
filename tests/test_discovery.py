import json

from discovery import discovery_reply


def test_discovery_reply():
    reply = discovery_reply(b'alpacadiscovery1', 5555)
    assert json.loads(reply) == {'AlpacaPort': 5555}


def test_discovery_ignores_other_packets():
    assert discovery_reply(b'hello', 5555) is None
    assert discovery_reply(b'', 5555) is None
