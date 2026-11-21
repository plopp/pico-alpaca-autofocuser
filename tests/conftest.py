"""Shared test helpers. Board code in pico/ is imported directly on CPython."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pico'))


class FakePin:
    """Stands in for machine.Pin; records every value written."""

    def __init__(self, value=0):
        self._value = value
        self.history = []

    def value(self, v=None):
        if v is None:
            return self._value
        self._value = 1 if v else 0
        self.history.append(self._value)


class FakeTimer:
    """Stands in for machine.Timer; the test advances it with tick()."""

    PERIODIC = 1

    def __init__(self):
        self.running = False
        self.freq = None
        self._callback = None

    def init(self, mode=None, freq=None, callback=None):
        self.running = True
        self.freq = freq
        self._callback = callback

    def deinit(self):
        self.running = False

    def tick(self, n=1):
        for _ in range(n):
            if not self.running:
                return
            self._callback(self)


# ---------------------------------------------------------------------------
# HTTP client fixture: runs the real Microdot app on a free localhost port
# ---------------------------------------------------------------------------
import asyncio
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

UNIQUE_ID = '01234567-89ab-cdef-0123-456789abcdef'


class Client:
    def __init__(self, port, stepper, timer, en, state=None, config=None, restarts=None):
        self.base = f'http://127.0.0.1:{port}'
        self.stepper = stepper
        self.timer = timer
        self.en = en
        self.state = state
        self.config = config
        self.restarts = restarts

    def _send(self, req):
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                status, body, ctype = r.status, r.read().decode(), r.headers.get('Content-Type', '')
        except urllib.error.HTTPError as e:
            status, body, ctype = e.code, e.read().decode(), e.headers.get('Content-Type', '')
        if ctype.startswith('application/json'):
            body = json.loads(body)
        return status, body

    def get(self, path, **params):
        url = self.base + path + ('?' + urllib.parse.urlencode(params) if params else '')
        return self._send(urllib.request.Request(url, method='GET'))

    def put(self, path, data=None):
        body = urllib.parse.urlencode(data or {}).encode()
        req = urllib.request.Request(self.base + path, data=body, method='PUT')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        return self._send(req)

    def post(self, path, data=None):
        body = urllib.parse.urlencode(data or {}).encode()
        req = urllib.request.Request(self.base + path, data=body, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        return self._send(req)

    def connect(self):
        return self.put('/api/v1/focuser/0/connect')


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture
def client(tmp_path):
    from alpaca import create_app
    from settings import load_settings
    from stepper import Stepper

    settings = load_settings(str(tmp_path / 'none.toml'), str(tmp_path / 'none.toml'))
    timer, en = FakeTimer(), FakePin()
    stepper = Stepper(FakePin(), FakePin(), en, timer, settings['steps_per_sec'],
                      settings['start_position'], settings['max_step'],
                      settings['reverse'], settings['hold_when_idle'])
    from state import FocuserState
    config = tmp_path / 'config.toml'
    config.write_text('[device]\nname = "Pico Focuser"\n')
    restarts = []
    state = FocuserState(settings, settings_path=str(config), restart=lambda: restarts.append(1))
    app = create_app(stepper, settings, UNIQUE_ID, lambda: '127.0.0.1', state=state)
    port = _free_port()
    loop_box = {}

    def serve():
        async def main():
            loop_box['loop'] = asyncio.get_running_loop()
            await app.start_server(host='127.0.0.1', port=port)
        asyncio.run(main())

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.02)
    yield Client(port, stepper, timer, en, state, config, restarts)
    loop_box['loop'].call_soon_threadsafe(app.shutdown)
    thread.join(timeout=5)
