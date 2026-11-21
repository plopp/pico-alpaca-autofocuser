import pytest

from temperature import TemperatureSensor, TemperatureStale, TemperatureUnavailable

ROM = b'\x28\x01\x02\x03\x04\x05\x06\x07'


class FakeOneWireError(Exception):
    """MicroPython's onewire.OneWireError derives from Exception, NOT OSError (checked on
    the Pico); ds18x20.read_scratch raises a plain Exception('CRC error')."""


class FakeDS:
    """Stands in for MicroPython's ds18x20.DS18X20, raising what the real driver raises."""

    def __init__(self, roms=(), temp=12.5):
        self.roms = list(roms)
        self.temp = temp
        self.fail = False

    def scan(self):
        return list(self.roms)

    def convert_temp(self):
        if self.fail:
            raise FakeOneWireError()

    def read_temp(self, rom):
        if self.fail or rom not in self.roms:
            raise Exception('CRC error')
        return self.temp


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def make(roms=(ROM,), temp=12.5):
    ds, clock = FakeDS(roms, temp), Clock()
    return TemperatureSensor(ds, clock=clock), ds, clock


def test_no_sensor_unavailable():
    sensor, ds, clock = make(roms=())
    sensor.poll_once()
    assert sensor.available is False
    with pytest.raises(TemperatureUnavailable):
        sensor.read()


def test_reads_value():
    sensor, ds, clock = make()
    sensor.poll_once()
    assert sensor.available is True
    assert sensor.read() == 12.5


def test_sensor_lost_then_found():
    sensor, ds, clock = make()
    sensor.poll_once()
    ds.fail = True
    clock.t += 30
    sensor.poll_once()
    assert sensor.read() == 12.5               # last value, still fresh enough
    clock.t += 31                              # 61 s since the last good reading
    sensor.poll_once()
    with pytest.raises(TemperatureStale):
        sensor.read()
    ds.fail = False
    ds.temp = 9.0
    clock.t += 31                              # past the rescan interval
    sensor.poll_once()
    assert sensor.read() == 9.0


def test_plugged_in_later():
    sensor, ds, clock = make(roms=())
    sensor.poll_once()
    ds.roms = [ROM]
    clock.t += 5
    sensor.poll_once()
    assert sensor.available is False           # no rescan yet
    clock.t += 30
    sensor.poll_once()
    assert sensor.available is True
    assert sensor.read() == 12.5


@pytest.mark.parametrize('bad', [85.0])
def test_power_on_value_ignored(bad):
    sensor, ds, clock = make()
    sensor.poll_once()
    ds.temp = bad
    clock.t += 5
    sensor.poll_once()
    assert sensor.read() == 12.5


def test_crc_error_keeps_previous_value():
    sensor, ds, clock = make()
    sensor.poll_once()
    ds.fail = True
    clock.t += 5
    sensor.poll_once()
    assert sensor.read() == 12.5


def test_poll_forever_survives_unexpected_errors():
    """A sensor problem must never stop the poll loop (and with it the whole server)."""
    import asyncio

    class Exploding(FakeDS):
        calls = 0

        def scan(self):
            Exploding.calls += 1
            if Exploding.calls == 1:
                raise RuntimeError('bus glitch')
            raise KeyboardInterrupt          # ends the test loop

    sensor = TemperatureSensor(Exploding([ROM]), clock=Clock(), poll_s=0)
    sensor._rescan_s = 0
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(sensor.poll_forever())
    assert Exploding.calls == 2
