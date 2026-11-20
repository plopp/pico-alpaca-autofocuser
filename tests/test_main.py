"""main.py startup order and crash handling, with fake machine/network modules."""
import asyncio
import sys
import types

import pytest


class Stop(BaseException):
    """Ends an endless loop in a test without being caught by `except Exception`."""


@pytest.fixture
def main_module(monkeypatch):
    events = []

    machine = types.ModuleType('machine')

    class Pin:
        OUT = 1

        def __init__(self, ident, mode=None, value=None):
            self.ident = ident
            events.append(('pin', ident, value))

        def value(self, v=None):
            if v is not None:
                events.append(('pin_value', self.ident, v))

        def on(self):
            pass

        def off(self):
            pass

        def toggle(self):
            pass

    class Timer:
        PERIODIC = 1

        def __init__(self, ident=-1):
            pass

        def init(self, **kw):
            pass

        def deinit(self):
            pass

    machine.Pin = Pin
    machine.Timer = Timer
    machine.unique_id = lambda: bytes(range(8))
    machine.reset = lambda: events.append(('reset',))

    network = types.ModuleType('network')
    network.STA_IF = 0
    network.hostname = lambda name: None

    class WLAN:
        PM_NONE = 0

        def __init__(self, iface):
            self._connected = False

        def active(self, on):
            pass

        def config(self, **kw):
            pass

        def connect(self, ssid, password):
            events.append(('wifi_connect',))
            self._connected = True

        def isconnected(self):
            return self._connected

        def status(self):
            return 3

        def ifconfig(self):
            return ('10.0.0.2', '', '', '')

        def disconnect(self):
            pass

    network.WLAN = WLAN

    monkeypatch.setitem(sys.modules, 'machine', machine)
    monkeypatch.setitem(sys.modules, 'network', network)
    sys.modules.pop('main', None)
    import main
    monkeypatch.setattr(main.time, 'sleep', lambda s: None)
    from settings import load_settings
    settings = load_settings('/nonexistent', '/nonexistent')
    settings['wifi_ssid'], settings['wifi_password'] = 'home', 'pw'
    monkeypatch.setattr(main, 'load_settings', lambda: settings)
    yield main, events
    sys.modules.pop('main', None)


def test_importing_main_does_not_start(main_module):
    main, events = main_module
    assert events == []


def test_driver_disabled_before_wifi(main_module, monkeypatch):
    main, events = main_module
    monkeypatch.setattr(main.asyncio, 'run', lambda coro: (coro.close(), (_ for _ in ()).throw(Stop()))[1])
    with pytest.raises(Stop):
        main.main()
    en_index = events.index(('pin', 21, 1))
    assert en_index < events.index(('wifi_connect',))


def test_server_crash_resets_board(main_module, monkeypatch):
    main, events = main_module

    def crash(coro):
        coro.close()
        raise RuntimeError('boom')

    monkeypatch.setattr(main.asyncio, 'run', crash)
    main.main()
    assert events[-1] == ('reset',)
    assert ('pin_value', 21, 1) in events          # driver switched off first


def test_ctrl_c_does_not_reset(main_module, monkeypatch):
    main, events = main_module

    def interrupt(coro):
        coro.close()
        raise KeyboardInterrupt

    monkeypatch.setattr(main.asyncio, 'run', interrupt)
    with pytest.raises(KeyboardInterrupt):
        main.main()
    assert ('reset',) not in events


def test_watchdog_survives_connect_error(main_module):
    main, _ = main_module
    calls = []

    class FlakyWlan:
        def isconnected(self):
            return False

        def connect(self, ssid, password):
            calls.append(1)
            if len(calls) == 1:
                raise OSError('wifi chip busy')
            if len(calls) == 3:
                raise Stop()

    class Led:
        def on(self):
            pass

        def off(self):
            pass

    with pytest.raises(Stop):
        asyncio.run(main.wifi_watchdog(FlakyWlan(), {'wifi_ssid': 'a', 'wifi_password': 'b'},
                                       Led(), interval=0))
    assert len(calls) == 3
