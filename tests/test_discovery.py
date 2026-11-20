import json

from discovery import discovery_reply


def test_discovery_reply():
    reply = discovery_reply(b'alpacadiscovery1', 5555)
    assert json.loads(reply) == {'AlpacaPort': 5555}


def test_discovery_ignores_other_packets():
    assert discovery_reply(b'hello', 5555) is None
    assert discovery_reply(b'', 5555) is None


class _Stop(BaseException):
    pass


def test_discovery_survives_send_error():
    import asyncio
    from discovery import run_discovery

    class FlakySocket:
        def __init__(self):
            self.recv_calls = 0
            self.sent = []

        def recvfrom(self, n):
            self.recv_calls += 1
            if self.recv_calls > 2:
                raise _Stop()
            return b'alpacadiscovery1', ('10.0.0.9', 40000)

        def sendto(self, data, addr):
            if not self.sent and self.recv_calls == 1:
                self.sent.append(None)
                raise OSError('ENOMEM')
            self.sent.append(data)

    sock = FlakySocket()
    try:
        asyncio.run(run_discovery(5555, sock=sock))
    except _Stop:
        pass
    assert sock.sent[-1] == b'{"AlpacaPort": 5555}'
