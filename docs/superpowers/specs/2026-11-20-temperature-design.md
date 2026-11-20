# Focuser temperature reporting — short design

**Intent:** Report the DS18B20 temperature to NINA so NINA's "autofocus after temperature change"
trigger can refocus. Decided by the user: temperature **only**; no firmware temperature compensation.

**Goals**
- Read a DS18B20 on **GP22** (1-Wire; 4.7 kΩ pull-up on the PCB, sensor on the 3.5 mm jack: T = data, R = 3V3, S = GND).
- Alpaca `Temperature` returns the latest reading in °C; `DeviceState` includes `Temperature`.
- `TempCompAvailable` stays false; `TempComp` unchanged (put true → NotImplemented).

**Non-goals:** firmware TempComp, multiple sensors, sensor calibration.

**Anti-goals:** HTTP requests blocking for the 750 ms conversion; a missing or unplugged sensor crashing the server or stopping NINA from connecting.

**Approach** (one sensible way): MicroPython's built-in `onewire` + `ds18x20` modules, polled from an
asyncio task every 5 s (`convert_temp()`, `await asyncio.sleep(0.8)`, `read_temp()`), caching the
last good value. A `TemperatureSensor` class takes the bus/driver objects by injection, so it is
tested on the PC with a fake, like `Stepper`.

**Behaviour without a sensor:** if no sensor is found at startup, `Temperature` returns
NotImplemented (0x400), so NINA treats the focuser as having no thermometer and the temperature
trigger simply never fires. If a sensor that was working stops answering, `Temperature` returns
the last good value for up to 60 s, then DriverError (0x500) until readings resume. The poll task
rescans the bus every 30 s, so plugging a sensor in later works without a reboot.

**Settings:** `[temperature] pin = 22`, `poll_s = 5` in `config.toml`.

**Verification:** pytest with a fake sensor (present, absent, unplugged mid-run, plugged in later);
ConformU on the simulator (which gets a fake sensor reporting 12.5 °C) stays clean; on the Pico,
`curl …/temperature` once the board and sensor exist.

**Order:** after the PCB, or on the breadboard now with a DS18B20 on GP22 plus a 4.7 kΩ pull-up.
