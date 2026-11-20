"""DS18B20 temperature, polled in the background and cached.

The Alpaca Temperature member reads the cache, so an HTTP request never waits for the
750 ms conversion. `driver` behaves like MicroPython's ds18x20.DS18X20 (scan, convert_temp,
read_temp), which lets the tests use a fake.
"""
import time

try:
    import asyncio
except ImportError:          # pragma: no cover
    import uasyncio as asyncio

POWER_ON_VALUE = 85.0        # what a DS18B20 reports before its first real conversion
CONVERSION_S = 0.8


class TemperatureUnavailable(Exception):
    """No sensor has ever been found."""


class TemperatureStale(Exception):
    """A sensor was found, but there has been no good reading for too long."""


class TemperatureSensor:
    def __init__(self, driver, clock=time.time, poll_s=5, stale_s=60, rescan_s=30):
        self._ds = driver
        self._clock = clock
        self.poll_s = poll_s
        self._stale_s = stale_s
        self._rescan_s = rescan_s
        self._roms = []
        self._last_scan = None
        self._value = None
        self._value_time = None
        self.available = False

    def _scan_due(self, now):
        if self._last_scan is None:
            return True
        if now - self._last_scan < self._rescan_s:
            return False
        no_recent_value = self._value_time is None or now - self._value_time >= self._rescan_s
        return not self._roms or no_recent_value

    def _scan(self, now):
        self._last_scan = now
        try:
            self._roms = list(self._ds.scan())
        except OSError:
            self._roms = []
        if self._roms:
            self.available = True

    def _start(self):
        """Scan if due and start a conversion. Returns False if there's nothing to read."""
        now = self._clock()
        if self._scan_due(now):
            self._scan(now)
        if not self._roms:
            return False
        try:
            self._ds.convert_temp()
        except OSError:
            return False
        return True

    def _finish(self):
        try:
            value = self._ds.read_temp(self._roms[0])
        except (OSError, IndexError):
            return
        if value is None or value == POWER_ON_VALUE or value < -55 or value > 125:
            return
        self._value = value
        self._value_time = self._clock()

    def poll_once(self):
        """One reading without waiting for the conversion (tests and simulator)."""
        if self._start():
            self._finish()

    async def poll_forever(self):
        while True:
            if self._start():
                await asyncio.sleep(CONVERSION_S)
                self._finish()
            await asyncio.sleep(self.poll_s)

    def read(self):
        if not self.available:
            raise TemperatureUnavailable('no temperature sensor connected')
        if self._value_time is None or self._clock() - self._value_time > self._stale_s:
            raise TemperatureStale('no reading from the temperature sensor')
        return self._value
