"""Desktop simulator: the Pico focuser app on CPython with simulated hardware.

    python3 sim.py [port]

Then point ConformU (or NINA) at http://localhost:5555/api/v1/focuser/0.
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pico'))

from alpaca import create_app  # noqa: E402
from settings import load_settings  # noqa: E402
from stepper import Stepper  # noqa: E402

PICO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pico')


class SimPin:
    def __init__(self, value=0):
        self._value = value

    def value(self, v=None):
        if v is None:
            return self._value
        self._value = v


class ThreadTimer:
    """machine.Timer look-alike that calls the callback from a thread."""

    PERIODIC = 1

    def __init__(self):
        self._generation = 0

    def init(self, mode=None, freq=1, callback=None):
        self._generation += 1
        generation = self._generation

        def run():
            while self._generation == generation:
                callback(self)
                time.sleep(1.0 / freq)

        threading.Thread(target=run, daemon=True).start()

    def deinit(self):
        self._generation += 1


def main():
    settings = load_settings(os.path.join(PICO_DIR, 'config.toml'), os.devnull)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else settings['port']
    stepper = Stepper(SimPin(), SimPin(), SimPin(1), ThreadTimer(),
                      settings['steps_per_sec'], settings['start_position'],
                      settings['max_step'], settings['reverse'],
                      settings['hold_when_idle'])
    app = create_app(stepper, settings, '5049434f-4643-5352-0000-000000000000',
                     lambda: '127.0.0.1')
    print('Simulated focuser on http://localhost:{}/api/v1/focuser/0'.format(port))
    app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
