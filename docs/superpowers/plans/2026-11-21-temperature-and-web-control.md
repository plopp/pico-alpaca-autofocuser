# Temperature + Web Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Report the DS18B20 temperature to NINA, and turn `/setup` into a browser control page with jog, move, reset-position, halt and basic settings.

**Architecture:** A `TemperatureSensor` polls the DS18B20 from an asyncio task and caches the reading. The Alpaca `Temperature` member and `DeviceState` read that cache. A new `control.py` adds `/control/*` JSON routes and an HTML page to the existing Microdot app. Shared state (connected flag, sensor, settings path) moves into a small `FocuserState` object that both `alpaca.py` and `control.py` use. Settings are saved to `config.toml` by `settings.save_settings`.

**Tech Stack:** MicroPython 1.27 (`onewire`, `ds18x20` built in on rp2), Microdot 2.x, pytest on CPython with fakes, ConformU 4.1.

**Spec:** `docs/superpowers/specs/2026-11-20-temperature-design.md` and `docs/superpowers/specs/2026-11-20-web-control-design.md` (both approved).

## Global Constraints

- Board code stays MicroPython-compatible (no `datetime`, `enum`, `typing`, `threading`, `logging`); hardware is injected so tests run on CPython.
- DS18B20 on **GP22**; `config.toml` gains `[temperature] pin = 22`, `poll_s = 5`.
- `Temperature`: no sensor ever found → NotImplemented `0x400`. Sensor lost → last value for up to **60 s**, then Driver error `0x500` until readings resume. The bus is rescanned every **30 s**. `TempCompAvailable` stays false.
- Control API lives outside `/api/v1`. Errors are HTTP 400 with a plain message. ConformU `alpacaprotocol` + `conformance` must stay clean on `sim.py`.
- Editable settings: `name`, `max_step`, `start_position`, `steps_per_sec`, `reverse`, `hold_when_idle`. Wi-Fi, port, hostname and pins are not editable from the page.
- **NINA not connected:** a manual move enables the driver for the move and releases it on arrival. **Connected:** the normal hold policy applies.
- Commits on branch `firmware-control`, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- **Reset position while moving** → refused (HTTP 400); position unchanged. Test: Task 1 `test_set_position_refused_while_moving`.
- **Jog beyond the range** (e.g. +1000 at 99 500) → clamped to max_step, not an error. Test: Task 4 `test_jog_clamps_to_range`.
- **Settings with nonsense values** (`max_step=abc`, `steps_per_sec=0`, `start_position > max_step`) → 400 and nothing written. Test: Task 3 `test_validate_rejects_bad_values`, Task 4 `test_settings_post_rejects_bad_values`.
- **Sensor unplugged mid-session** → last value for 60 s, then 0x500; plugged back in → values resume. Test: Task 2 `test_sensor_lost_then_found`.
- **Manual move with NINA disconnected** leaves the motor energized afterwards → must release. Test: Task 1 `test_move_with_release_disables_on_arrival`.

---

## File Structure

| Path | Responsibility |
|---|---|
| `pico/stepper.py` | + `set_position(n)`, `configure(...)`, `move_to(target, release=False)` |
| `pico/temperature.py` | `TemperatureSensor`: poll loop, cache, staleness, rescan |
| `pico/settings.py` | + `validate_settings(values)`, `save_settings(path, values)` |
| `pico/state.py` | `FocuserState`: connected flag, server transaction id, sensor, settings path, restart hook |
| `pico/alpaca.py` | uses `FocuserState`; `Temperature` and `DeviceState` from the sensor |
| `pico/control.py` | `/control/*` routes + the control page HTML |
| `pico/main.py`, `sim.py` | wire the sensor (real or fake) and control routes |

### Task 1: Stepper additions

**Files:** Modify `pico/stepper.py`, `tests/test_stepper.py`

**Interfaces — produces:**
- `Stepper.set_position(n: int)`: raises `ValueError` if moving or out of `0..max_step`; sets position and target.
- `Stepper.configure(steps_per_sec: int, reverse: bool, hold_when_idle: bool)`: raises `ValueError` while moving.
- `Stepper.move_to(target: int, release: bool = False)`: with `release=True`, enables the driver if needed and disables it on arrival or halt (regardless of `hold_when_idle`).

- [ ] **Step 1: Failing tests:**
  - `test_set_position` (→ position/target 1234, no steps)
  - `test_set_position_refused_while_moving`
  - `test_set_position_out_of_range`
  - `test_configure_changes_speed_and_direction` (next `timer.freq` = new rate; DIR inverted)
  - `test_configure_refused_while_moving`
  - `test_move_with_release_disables_on_arrival` (`hold_when_idle=True`, not enabled → move with `release=True` → EN 0 during the move, EN 1 after)
  - `test_halt_after_release_move_disables`
- [ ] **Step 2:** `python3 -m pytest tests/test_stepper.py -q` → FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit `feat: stepper set_position, configure, release-after-move`.

### Task 2: Temperature sensor

**Files:** Create `pico/temperature.py`, `tests/test_temperature.py`

**Interfaces — produces:**
- `TemperatureSensor(driver, clock=time.time, poll_s=5, stale_s=60, rescan_s=30)`. `driver` has `scan() -> list`, `convert_temp()` and `read_temp(rom) -> float`, as MicroPython's `ds18x20.DS18X20` does.
- `available: bool`: a sensor was ever found.
- `read() -> float`: raises `TemperatureUnavailable` if never found, `TemperatureStale` if no good reading for `stale_s`.
- `async poll_forever()`, and `poll_once()` (sync, for tests: scan if needed, convert, read).
- Exceptions `TemperatureUnavailable`, `TemperatureStale`.

- [ ] **Step 1: Failing tests** with a `FakeDS` (settable roms and temps, can raise `OSError`) and a fake clock:
  - `test_no_sensor_unavailable`
  - `test_reads_value` (12.5)
  - `test_sensor_lost_then_found` (last value until +60 s, then stale; found again → fresh)
  - `test_plugged_in_later` (no rom at start; rom appears; after the rescan interval → available)
  - `test_bad_reading_ignored` (85.0 power-on value, or a CRC `OSError`, keeps the previous value)
- [ ] **Step 2:** FAIL. **Step 3:** Implement. 85.0 °C is the DS18B20 power-on default, so ignore it. **Step 4:** PASS. **Step 5:** Commit `feat: DS18B20 temperature sensor with staleness and rescan`.

### Task 3: Settings validation and saving

**Files:** Modify `pico/settings.py`, `tests/test_settings.py`

**Interfaces — produces:**
- `EDITABLE = ('name', 'max_step', 'start_position', 'steps_per_sec', 'reverse', 'hold_when_idle')`
- `validate_settings(values: dict) -> dict`: returns typed values; raises `ValueError(message)`. Rules:
  - name 1–40 chars
  - max_step 100–1 000 000
  - start_position 0..max_step
  - steps_per_sec 1–5000
  - reverse and hold_when_idle are booleans; `'true'`/`'false'`/`'on'`/missing checkbox → bool
- `save_settings(path: str, values: dict) -> None`: rewrites only the `[device]` keys in `config.toml` and keeps every other line and comment.

- [ ] **Step 1: Failing tests:**
  - `test_validate_accepts_good_values`
  - `test_validate_rejects_bad_values` (parametrized: `abc`, `0`, `start > max`, empty name)
  - `test_save_settings_round_trip` (save, then `load_settings` → new values; `[network]` and the comments are unchanged)
  - `test_save_adds_missing_keys` (the `start_position` key is commented out in the shipped file)
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit `feat: validate and save settings`.

### Task 4: Shared state, Alpaca temperature, control routes and page

**Files:** Create `pico/state.py`, `pico/control.py`, `tests/test_control.py`; modify `pico/alpaca.py`, `tests/conftest.py`, `tests/test_alpaca_focuser.py`

**Interfaces:**
- `FocuserState(settings, sensor=None, settings_path='config.toml', restart=None)` with `connected`, `next_txn()`.
- `create_app(stepper, settings, unique_id, ip_getter=lambda: '', state=None)`: creates a `FocuserState` if none is given, and registers the control routes through `control.add_routes(app, stepper, state, ip_getter)`.
- Routes:

  | Method and path | Behaviour |
  |---|---|
  | `GET /control/status` | `{position, target, moving, connected, temperature (float or null), max_step, settings}` |
  | `POST /control/move` | `position` |
  | `POST /control/jog` | `steps`, may be negative, clamped |
  | `POST /control/halt` | |
  | `POST /control/reset` | sets `start_position`; 400 while moving |
  | `GET /control/settings` | |
  | `POST /control/settings` | validate → save → apply live ones |
  | `POST /control/restart` | calls `state.restart` after the response |

  `GET /setup` and `GET /setup/v1/focuser/0/setup` → the control page.
- Manual moves use `release=not state.connected`.

- [ ] **Step 1: Failing tests:**
  - `test_alpaca_temperature_with_sensor` (12.5; `devicestate` includes `Temperature`)
  - `test_alpaca_temperature_without_sensor` (0x400; `devicestate` without `Temperature`)
  - `test_alpaca_temperature_stale` (0x500)
  - `test_status_json`
  - `test_move_and_jog`
  - `test_jog_clamps_to_range`
  - `test_reset_position`
  - `test_reset_refused_while_moving` (400)
  - `test_manual_move_when_disconnected_releases_driver`
  - `test_settings_post_saves_and_applies` (tmp `config.toml`; speed applied live)
  - `test_settings_post_rejects_bad_values` (400, file unchanged)
  - `test_restart_calls_hook`
  - `test_control_page_loads` (HTML with Jog, Move, Reset, Halt, Settings)
- [ ] **Step 2:** FAIL. **Step 3:** Implement (the page is a compact HTML/JS string, aiming under 8 KB). **Step 4:** whole suite PASS.
- [ ] **Step 5:** Commit `feat: control page, settings editor and Alpaca temperature`.

### Task 5: Wiring, ConformU, deploy

**Files:** Modify `pico/main.py`, `sim.py`, `pico/config.toml`, `README.md`, `CLAUDE.md`

- [ ] **Step 1:**
  - `main.py`: build `TemperatureSensor(ds18x20.DS18X20(onewire.OneWire(Pin(settings['temp_pin']))))` (an import failure → no sensor). Add `sensor.poll_forever()` to the gathered tasks. `FocuserState(..., restart=machine.reset)`.
  - `sim.py`: a fake sensor at 12.5 °C.
  - `settings.py`: load `[temperature] pin/poll_s` as `temp_pin`/`temp_poll_s`.
- [ ] **Step 2:** `python3 sim.py` + both ConformU checks → 0 errors, 0 issues.
- [ ] **Step 3:** Deploy (`tools/deploy.sh`):
  - the Pico boots
  - `curl …/control/status` shows JSON
  - `/setup` loads
  - `curl …/api/v1/focuser/0/temperature` → 0x400 without a sensor, or a value with one
- [ ] **Step 4:** README: the control page, temperature and the NINA trigger. CLAUDE.md: the new modules.
- [ ] **Step 5:** Commit `feat: wire temperature and control page into main and sim`.
