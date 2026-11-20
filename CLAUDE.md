# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

An ASCOM Alpaca **Focuser (IFocuserV4, absolute)** written in MicroPython for a Raspberry Pi Pico 2 W driving a BigTreeTech TMC2209 v1.3 and a NEMA 17 stepper, for use with NINA. Design and plan: `docs/superpowers/specs/` and `docs/superpowers/plans/`.

`pico/` is exactly what goes on the board's root filesystem. Everything else (tests, `sim.py`, `tools/`) runs on the PC only.

## Commands

```bash
python3 -m pytest tests -q                       # all tests (CPython, fake hardware)
python3 -m pytest tests/test_stepper.py::test_halt_stops_at_current_position -q   # one test
python3 sim.py [port]                            # app on the PC with a simulated motor (default 5555)
tools/deploy.sh                                  # copy pico/ to the board and reset it
.venv/bin/mpremote repl                          # board console (Ctrl-C stops main.py)

# ConformU 4.1 acceptance checks (against sim.py or the Pico's IP); both must be clean
C=~/git/pic-pico-projects/tools/conformu.linux-x64/conformu
$C alpacaprotocol http://localhost:5555/api/v1/focuser/0
$C conformance   http://localhost:5555/api/v1/focuser/0
```

`mpremote` lives in the git-ignored `.venv` (system Python is PEP 668 managed): `python3 -m venv .venv && .venv/bin/pip install mpremote`.

## Architecture

- `pico/main.py` runs at power-up: loads settings, joins Wi-Fi (blinks the LED, retries every 10 s, watchdog reconnects), builds the `Stepper` with real `machine.Pin`/`machine.Timer`, then `asyncio.run`s the Microdot server and the discovery responder together.
- `pico/stepper.py` – `Stepper` moves one step per **timer tick** toward a target, so HTTP never blocks; `IsMoving`/`Position`/`Halt` work mid-move and a new `move_to` retargets. Pins and timer are injected, which is what lets the same code run under pytest (`tests/conftest.py` `FakePin`/`FakeTimer`, advanced with `tick()`) and in `sim.py` (`ThreadTimer`).
- `pico/alpaca.py` – `create_app(stepper, settings, unique_id, ip_getter)` holds all routes. Members are two dicts (`get_members` return a Value, `put_members` act); `respond()` applies the Alpaca rules shared by all of them. Add a member by adding a dict entry; add it to `_NO_CONNECTION_NEEDED` only if it must work while disconnected.
- `pico/discovery.py` – UDP 32227 responder (`alpacadiscovery1` → `{"AlpacaPort": port}`), polled non-blocking socket.
- `pico/settings.py` – defaults ← `config.toml` ← Wi-Fi from `secret.toml` (git-ignored; placeholder SSID counts as empty).
- `pico/microdot.py`, `pico/toml.py` – vendored, don't edit. `pico/blink.py` – standalone STEP/DIR wiring test.

## Rules that ConformU / NINA depend on

- GET parameter names are case-insensitive; PUT form names are case-sensitive. Malformed requests (bad ClientID/ClientTransactionID, missing or non-parsable parameters) → HTTP 400 with a plain-text body. ASCOM errors → HTTP 200 with `ErrorNumber`/`ErrorMessage` (NotImplemented 0x400, InvalidValue 0x401, NotConnected 0x407, Driver 0x500).
- Board code must stay MicroPython-compatible: no `datetime`, `enum`, `typing`, `threading`, `logging`.
- Position is not persisted: every boot reports `start_position` (middle of range); the user hand-sets focus near the middle before power-up.
- The driver (EN, active low) is disabled at boot, enabled on connect, disabled on disconnect.

## Hardware

STEP GP16, DIR GP20, EN GP21; driver VIO from the Pico's 3V3; MS1/MS2 floating = 1/8 microstep (1600 steps/turn). Motor supply (VM) should come from a separate 12 V supply sharing ground with the Pico — not from USB VBUS (the board hung once while blink.py ran the motor from VBUS; suspected cause).
