# pico-alpaca-autofocuser

An ASCOM Alpaca focuser (IFocuserV4, absolute) for a Raspberry Pi Pico 2 W, written in
MicroPython, for autofocus with NINA. It drives a TMC2209 stepper driver over Wi-Fi and
passes ASCOM ConformU 4.1.

## Wiring

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
choose the focuser from the Alpaca devices list (it is found automatically).

**Position:** the focuser has no encoder. Every power-up it reports position 50000
(the middle of 0–100000), so set focus roughly by hand before powering on.

## Development

```bash
python3 -m pytest tests -q   # tests on the PC with simulated hardware
python3 sim.py               # run the server on the PC with a simulated motor
```
