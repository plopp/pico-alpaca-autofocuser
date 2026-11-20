# pico-alpaca-autofocuser

An ASCOM Alpaca focuser (IFocuserV4, absolute) for a Raspberry Pi Pico 2 W, written in
MicroPython, for autofocus with NINA. It drives a TMC2209 stepper driver over Wi-Fi.
It passes ASCOM ConformU 4.1 against the desktop simulator (`sim.py`); the run on real
hardware is pending a separate motor supply (see Wiring).

## Hardware

There's a carrier PCB in [`hardware/`](hardware/README.md): 80 × 50 mm, assembled by JLCPCB,
with sockets for the Pico 2 W and the TMC2209, a 12 V barrel jack, a motor connector and a
3.5 mm jack for a DS18B20 temperature sensor. The table below is for breadboard builds.

## Wiring (breadboard)

| TMC2209 (BigTreeTech v1.3) | Connect to |
|---|---|
| STEP | Pico GP16 (pin 21) |
| DIR | Pico GP20 (pin 26) |
| EN | Pico GP21 (pin 27) |
| VIO | Pico 3V3 OUT (pin 36) |
| GND (both) | Pico GND and the motor supply's GND |
| VM | Motor supply, 12 V recommended, with ~100 µF across VM/GND |
| A1/A2, B1/B2 | One motor coil each |
| MS1, MS2 | Unconnected (1/8 microstepping) |

Don't power VM from the Pico's USB 5 V (VBUS): the motor can hang or reset the board.

## Setup

1. Install MicroPython 1.27+ for the Pico 2 W.
2. Create `pico/secret.toml` (never committed):
   ```toml
   [wifi]
   ssid = "your-network-name"
   password = "your-wifi-password"
   ```
3. Adjust `pico/config.toml` if needed (range, speed, direction).
4. `python3 -m venv .venv && .venv/bin/pip install mpremote`, then `tools/deploy.sh`.

At power-up the LED blinks while joining Wi-Fi and stays on when connected. In NINA,
choose the focuser from the Alpaca devices list. Discovery only works when NINA's PC is on
the same subnet as the Pico; otherwise add it manually by IP address, port 5555.

**Position:** the focuser has no encoder. Every power-up it reports the middle of the
range (50000 of 0–100000 by default), so set focus roughly by hand before powering on.

## Development

```bash
python3 -m pytest tests -q   # tests on the PC with simulated hardware
python3 sim.py               # run the server on the PC with a simulated motor
```
