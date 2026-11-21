"""Runs at power-up: join Wi-Fi, then serve the Alpaca focuser and discovery.

Stop it from the REPL with Ctrl-C.
"""
import asyncio
import time

import machine
import network
from machine import Pin, Timer

from alpaca import create_app
from discovery import run_discovery
from settings import load_settings
from state import FocuserState
from stepper import Stepper
from temperature import TemperatureSensor

WIFI_RETRY_S = 10
WIFI_CHECK_S = 30


def unique_id():
    """Stable GUID-shaped ID from the RP2350's 8-byte board ID."""
    h = ''.join('{:02x}'.format(b) for b in machine.unique_id())
    return '5049434f-4643-5352-{}-{}'.format(h[:4], h[4:16])


def connect_wifi(wlan, settings, led):
    """Block until connected, retrying every WIFI_RETRY_S. LED blinks meanwhile."""
    while not wlan.isconnected():
        print('[main] Connecting to Wi-Fi "{}"...'.format(settings['wifi_ssid']))
        wlan.connect(settings['wifi_ssid'], settings['wifi_password'])
        deadline = time.time() + WIFI_RETRY_S
        while not wlan.isconnected() and time.time() < deadline:
            led.toggle()
            time.sleep(0.25)
        if not wlan.isconnected():
            print('[main] Wi-Fi failed (status {}), retrying'.format(wlan.status()))
            wlan.disconnect()
    led.on()
    print('[main] Wi-Fi connected, IP address', wlan.ifconfig()[0])


async def wifi_watchdog(wlan, settings, led, interval=WIFI_CHECK_S):
    while True:
        await asyncio.sleep(interval)
        try:
            if not wlan.isconnected():
                led.off()
                print('[main] Wi-Fi lost, reconnecting')
                wlan.connect(settings['wifi_ssid'], settings['wifi_password'])
            else:
                led.on()
        except Exception as e:      # Never let a Wi-Fi hiccup stop the server
            print('[main] Wi-Fi watchdog error:', repr(e))


async def serve(app, port, wlan, settings, led, sensor=None):
    tasks = [app.start_server(host='0.0.0.0', port=port), run_discovery(port)]
    if sensor is not None:
        tasks.append(sensor.poll_forever())
    if wlan is not None:
        tasks.append(wifi_watchdog(wlan, settings, led))
    await asyncio.gather(*tasks)


def make_stepper(settings):
    return Stepper(Pin(settings['step_pin'], Pin.OUT, value=0),
                   Pin(settings['dir_pin'], Pin.OUT, value=0),
                   Pin(settings['en_pin'], Pin.OUT, value=1),
                   Timer(-1),
                   settings['steps_per_sec'], settings['start_position'],
                   settings['max_step'], settings['reverse'],
                   settings['hold_when_idle'])


def make_sensor(settings):
    """DS18B20 on the 3.5 mm jack; None if this firmware has no 1-Wire support."""
    try:
        import ds18x20
        import onewire
        bus = onewire.OneWire(Pin(settings['temp_pin']))
        return TemperatureSensor(ds18x20.DS18X20(bus), poll_s=settings['temp_poll_s'])
    except Exception as e:
        print('[main] No temperature support:', repr(e))
        return None


def main():
    settings = load_settings()
    # Drive EN high (driver off) before anything slow, like joining Wi-Fi
    stepper = make_stepper(settings)
    led = Pin('LED', Pin.OUT, value=0)
    wlan = None
    if settings['wifi_ssid']:
        network.hostname(settings['hostname'])
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        pm_none = getattr(network.WLAN, 'PM_NONE', None)
        if pm_none is not None:
            wlan.config(pm=pm_none)       # Wi-Fi power saving adds big latency
        connect_wifi(wlan, settings, led)
    else:
        print('[main] No Wi-Fi configured: put ssid/password in secret.toml')

    ip = (lambda: wlan.ifconfig()[0]) if wlan else (lambda: '')
    sensor = make_sensor(settings)
    state = FocuserState(settings, sensor=sensor, settings_path='config.toml',
                         restart=machine.reset)
    app = create_app(stepper, settings, unique_id(), ip, state=state)
    print('[main] Alpaca focuser on port {}'.format(settings['port']))
    try:
        asyncio.run(serve(app, settings['port'], wlan, settings, led, sensor))
    except KeyboardInterrupt:            # Ctrl-C from the REPL: stop, don't reset
        stepper.disable()
        raise
    except Exception as e:               # Anything else: restart rather than go dark
        stepper.disable()
        print('[main] Server stopped:', repr(e), '- resetting in 5 s')
        time.sleep(5)
        machine.reset()


if __name__ == '__main__':
    main()
