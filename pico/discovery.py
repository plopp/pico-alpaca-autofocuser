"""Alpaca discovery responder (UDP 32227) so NINA can find the focuser."""
import asyncio
import json
import socket

DISCOVERY_PORT = 32227
_REQUEST = b'alpacadiscovery1'


def discovery_reply(data, alpaca_port):
    if not data.startswith(_REQUEST):
        return None
    return json.dumps({'AlpacaPort': alpaca_port}).encode()


async def run_discovery(alpaca_port, udp_port=DISCOVERY_PORT, sock=None):
    if sock is None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', udp_port))
        sock.setblocking(False)
    while True:
        try:
            data, addr = sock.recvfrom(64)
        except OSError:            # Nothing waiting (EAGAIN)
            await asyncio.sleep(0.1)
            continue
        reply = discovery_reply(data, alpaca_port)
        if reply:
            try:
                sock.sendto(reply, addr)
            except Exception as e:  # e.g. no route during a Wi-Fi blip: keep serving
                print('[discovery] reply failed:', repr(e))
