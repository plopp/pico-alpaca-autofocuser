# NINA Alpaca Focuser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A MicroPython ASCOM Alpaca IFocuserV4 (absolute) server on a Pico 2 W driving a TMC2209, that passes ConformU 4.1 and works with NINA.

**Architecture:** Microdot 2.x serves the Alpaca REST API on asyncio; a `machine.Timer` callback emits step pulses toward a target so HTTP stays responsive; a UDP task answers Alpaca discovery. Hardware is injected, so the same code runs on CPython with fakes for pytest and a desktop simulator that ConformU tests against.

**Tech Stack:** MicroPython 1.27 (RP2350), Microdot 2.x (vendored `microdot.py`), CPython 3 + pytest on the PC, mpremote, ConformU 4.1.0.

**Spec:** `docs/superpowers/specs/2026-11-20-nina-alpaca-focuser-design.md`

## Global Constraints

- Board code lives in `pico/` and is copied to the Pico's root unchanged; it may only import MicroPython-available modules (`asyncio`, `json`, `socket`, `time`, `machine`, `network`, `os`) plus `microdot` and `toml`. No `datetime`, `enum`, `typing`, `threading`, `logging`.
- Interface: `InterfaceVersion` = 4, device type `focuser`, device number 0, `Absolute` = true.
- Defaults: `max_step` 100000, `start_position` 50000, `max_increment` 100000, `steps_per_sec` 800, `reverse` false, `hold_when_idle` true, `port` 5555, pins STEP 16 / DIR 20 / EN 21 (EN active low).
- Error numbers: NotImplemented `0x400`, InvalidValue `0x401`, NotConnected `0x407`, InvalidOperation `0x40B`, Driver `0x500`.
- EN is high (driver disabled) at boot; enabled on connect; disabled on disconnect; with `hold_when_idle = false` also disabled after each move.
- Discovery: UDP 32227, request `alpacadiscovery1`, reply `{"AlpacaPort": <port>}`.
- `secret.toml` is never committed (already in `.gitignore`).
- ConformU: `~/git/pic-pico-projects/tools/conformu.linux-x64/conformu`.
- Commits go on branch `nina-focuser`, not `main`, and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- **Move while moving** retargets to the new position instead of erroring. Test: Task 2 `test_move_while_moving_retargets`.
- **Halt mid-move** leaves `Position` where the motor actually stopped and `IsMoving` false. Test: Task 2 `test_halt_stops_at_current_position`.
- **Malformed `Position`** (`"12.5"`, `"abc"`, empty) → HTTP 400; well-formed but out of range (`-1`, `100001`) → InvalidValue `0x401`. Test: Task 4 `test_move_bad_position`.
- **Disconnect during a move** halts the motor and disables the driver. Test: Task 3 `test_disconnect_halts_and_disables`.
- **Missing or placeholder `secret.toml`** → settings load with empty Wi-Fi and the server still starts. Test: Task 1 `test_missing_secret_gives_empty_wifi`.

---

## File Structure

| Path | Responsibility |
|---|---|
| `pico/settings.py` | `load_settings()` merging defaults, `config.toml`, `secret.toml` |
| `pico/stepper.py` | `Stepper`: position/target/moving state, timer-driven stepping, enable/disable |
| `pico/alpaca.py` | `create_app()`: all Alpaca, management and setup routes |
| `pico/discovery.py` | `discovery_reply()` + `run_discovery()` UDP responder |
| `pico/main.py` | Wi-Fi, LED, hostname, start server + discovery |
| `pico/config.toml` | Settings (defaults above) |
| `pico/microdot.py`, `pico/toml.py`, `pico/blink.py` | Moved from repo root, unchanged |
| `sim.py` | Desktop simulator (threaded fake timer) for ConformU |
| `tests/conftest.py` | Puts `pico/` on `sys.path`; `FakePin`, `FakeTimer`, HTTP `client` fixture |
| `tools/deploy.sh` | Copy `pico/` to the board with mpremote |

---

### Task 1: Scaffold, cleanup, settings

**Files:**
- Delete: `app.py compat.py config.py config.toml discovery.py exceptions.py focuser.py focuserdevice.py log.py logging.py management.py setup.py shr.py threading.py main.py`
- Move (git mv / mv): `microdot.py toml.py blink.py` → `pico/`; `secret.toml` → `pico/secret.toml` (untracked, keep the user's contents)
- Create: `pico/settings.py`, `pico/config.toml`, `tests/conftest.py`, `tests/test_settings.py`

**Interfaces:**
- Produces: `load_settings(config_path='config.toml', secret_path='secret.toml') -> dict` with keys
  `port:int, max_step:int, start_position:int, max_increment:int, steps_per_sec:int, reverse:bool, hold_when_idle:bool, step_pin:int, dir_pin:int, en_pin:int, name:str, location:str, wifi_ssid:str, wifi_password:str, hostname:str`.
  `config.toml` sections: `[network] port, hostname`, `[device] name, location, max_step, start_position, max_increment, steps_per_sec, reverse, hold_when_idle`, `[pins] step, dir, en`; `secret.toml`: `[wifi] ssid, password`. Missing files/keys fall back to defaults; `ssid == "your-network-name"` counts as empty.
- Produces (conftest): `FakePin(value=0)` with `.value(v=None)` and `.history:list[int]`; `FakeTimer` with `PERIODIC = 1`, `.init(mode, freq, callback)`, `.deinit()`, `.running:bool`, `.freq`, `.tick(n=1)` calling the callback `n` times while running.

- [ ] **Step 1:** `git checkout -b nina-focuser`, then do the deletes/moves above.
- [ ] **Step 2: Write failing tests** in `tests/test_settings.py`: `test_defaults_when_no_files` (all Global Constraints defaults, `name == "Pico Focuser"`, `hostname == "pico-focuser"`), `test_config_overrides` (tmp `config.toml` with `[device] max_step = 2000` → 2000, others default), `test_missing_secret_gives_empty_wifi`, `test_placeholder_ssid_is_empty`.
- [ ] **Step 3:** Run `python3 -m pytest tests/test_settings.py -v` → FAIL (no module `settings`).
- [ ] **Step 4:** Implement `pico/settings.py` using `toml.load`; write `pico/config.toml` with the defaults.
- [ ] **Step 5:** Run tests → PASS.
- [ ] **Step 6:** Commit `feat: scaffold pico/ layout and settings loader`.

### Task 2: Stepper

**Files:** Create `pico/stepper.py`, `tests/test_stepper.py`

**Interfaces:**
- Produces: `Stepper(step_pin, dir_pin, en_pin, timer, steps_per_sec:int, start_position:int, max_step:int, reverse:bool=False, hold_when_idle:bool=True)`
  - read-only properties `position:int`, `target:int`, `is_moving:bool`, `enabled:bool`
  - `move_to(target:int) -> None` (raises `ValueError` outside `0..max_step`; starts timer with `timer.init(mode=timer.PERIODIC, freq=steps_per_sec, callback=self._tick)` if not running; retargets if running)
  - `halt() -> None` (target = position, `timer.deinit()`)
  - `enable()` (EN → 0), `disable()` (halt, EN → 1)
  - `_tick(t=None)`: if position ≠ target: DIR = 1 for increasing position (inverted when `reverse`), STEP high then low, position ±1; on arrival `timer.deinit()` and, if not `hold_when_idle`, EN → 1.
- Constructor sets EN to 1 (disabled).

- [ ] **Step 1: Write failing tests:** `test_starts_disabled_at_start_position` (EN history `[1]`, position 50000, not moving); `test_move_steps_to_target` (enable, `move_to(50003)`, `tick(10)` → position 50003, 3 STEP rising edges, not moving, timer stopped); `test_direction_and_reverse` (moving down sets DIR 0; with `reverse=True` moving up sets DIR 0); `test_move_out_of_range_raises` (`-1`, `100001`); `test_move_while_moving_retargets` (move_to 50010, tick 3, move_to 49990, tick 100 → 49990); `test_halt_stops_at_current_position` (move_to 50010, tick 4, halt → position 50004, target 50004, not moving, timer stopped); `test_hold_when_idle_false_disables_after_move`.
- [ ] **Step 2:** `python3 -m pytest tests/test_stepper.py -v` → FAIL.
- [ ] **Step 3:** Implement `pico/stepper.py`.
- [ ] **Step 4:** Tests → PASS.
- [ ] **Step 5:** Commit `feat: timer-driven stepper`.

### Task 3: Alpaca app — protocol core and common members

**Files:** Create `pico/alpaca.py`, `tests/test_alpaca_common.py`; extend `tests/conftest.py` with a `client` fixture.

**Interfaces:**
- Consumes: `Stepper` (Task 2), settings dict (Task 1).
- Produces: `create_app(stepper, settings:dict, unique_id:str, ip_getter=lambda: '') -> Microdot`. State (connected flag, server transaction counter) lives in the closure/app.
- `client` fixture: starts `create_app(...)` with a `FakeTimer` stepper on a free localhost port in a background thread (`asyncio.run(app.start_server(...))`), yields an object with `get(path, **params) -> (status:int, body:dict|str)` and `put(path, data:dict) -> (status, body)` (form-urlencoded); shuts down with `app.shutdown()`.
- Response JSON: gets `{"Value", "ClientTransactionID", "ServerTransactionID", "ErrorNumber", "ErrorMessage"}`, methods the same minus `Value`; `Content-Type: application/json`.

- [ ] **Step 1: Write failing tests:** `test_response_envelope` (GET `name` with `ClientTransactionID=7` → 200, Value "Pico Focuser", ClientTransactionID 7, ErrorNumber 0, ServerTransactionID increments across two calls); `test_get_params_case_insensitive` (`clienttransactionid=9` → 9); `test_put_params_case_sensitive` (PUT `connected` with `connected=True` → 400); `test_bad_client_ids` (`ClientID=-1` and `ClientTransactionID=abc` → 400); `test_bad_device_number` (`/api/v1/focuser/1/name` → 400 or 404); `test_identity_members` (interfaceversion 4, supportedactions `[]`, driverversion/description/driverinfo are strings); `test_connect_cycle` (connected false → PUT connect → connected true, connecting false, EN 0 → PUT disconnect → false, EN 1; PUT `connected` `Connected=True`/`False` does the same); `test_not_connected_errors` (GET `position` before connect → ErrorNumber 0x407); `test_action_members_not_implemented` (PUT action/commandblind/commandbool/commandstring with `Action`/`Command`/`Parameters`/`Raw` → 0x400); `test_disconnect_halts_and_disables` (connect, move to 50100, tick 5, disconnect → not moving, EN 1); `test_devicestate` (after connect: Value is a list with Names `IsMoving`, `Position`, `TimeStamp`).
- [ ] **Step 2:** `python3 -m pytest tests/test_alpaca_common.py -v` → FAIL.
- [ ] **Step 3:** Implement `pico/alpaca.py`: route `/api/v1/focuser/<int:devnum>/<member>` for GET and PUT dispatching to member handlers; 404 for unknown member, 400 for devnum ≠ 0; `devicestate` returns list of `{"Name","Value"}` for `IsMoving`, `Position`, `TimeStamp` (ISO UTC built from `time.gmtime()`).
- [ ] **Step 4:** Tests → PASS.
- [ ] **Step 5:** Commit `feat: Alpaca protocol core and common members`.

### Task 4: Focuser members, management, setup

**Files:** Modify `pico/alpaca.py`; create `tests/test_alpaca_focuser.py`

**Interfaces:** Consumes `create_app`, `client` fixture.

- [ ] **Step 1: Write failing tests** (all after connect): `test_static_focuser_values` (absolute true, maxstep 100000, maxincrement 100000, tempcompavailable false, tempcomp false, stepsize 0x400, temperature 0x400); `test_tempcomp_put` (`TempComp=false` → 0, `TempComp=true` → 0x400); `test_move_and_position` (PUT move `Position=50020`, ismoving true, tick 50, ismoving false, position 50020); `test_halt_member`; `test_move_bad_position` (`"12.5"`, `"abc"`, `""` → 400; `-1`, `100001` → 0x401); `test_management` (`/management/apiversions` Value `[1]`; `description` has ServerName/Manufacturer/ManufacturerVersion/Location; `configureddevices` has one entry with DeviceName, DeviceType "Focuser", DeviceNumber 0, UniqueID == the passed id); `test_setup_pages` (`/setup` and `/setup/v1/focuser/0/setup` → 200 text/html containing the position).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement the members in `pico/alpaca.py`.
- [ ] **Step 4:** `python3 -m pytest -v` (whole suite) → PASS.
- [ ] **Step 5:** Commit `feat: focuser members, management and setup endpoints`.

### Task 5: Discovery, main.py, simulator, ConformU on the desktop

**Files:** Create `pico/discovery.py`, `pico/main.py`, `sim.py`, `tests/test_discovery.py`

**Interfaces:**
- Produces: `discovery_reply(data:bytes, alpaca_port:int) -> bytes | None` (reply only when `data` starts with `b"alpacadiscovery1"`); `async run_discovery(alpaca_port:int, udp_port:int=32227)` using a non-blocking UDP socket polled every 100 ms.
- `main.py`: `load_settings()`; Wi-Fi via `network.WLAN(STA_IF)` with `network.hostname(settings['hostname'])`, retry every 10 s until connected (skip with a printed message when ssid empty), `Pin("LED")` on when connected; print the IP; build `Stepper` with real `machine.Pin`/`machine.Timer(-1)`; `unique_id` = hex of `machine.unique_id()` formatted as a GUID-like string; `asyncio.run` gathering `app.start_server(port=...)` and `run_discovery(port)`.
- `sim.py`: same wiring on CPython with `FakePin` and a `ThreadTimer` (a `threading.Thread` calling the callback at `freq` until `deinit`), serving on `0.0.0.0:5555`.

- [ ] **Step 1: Write failing tests:** `test_discovery_reply` (`b"alpacadiscovery1"` → `b'{"AlpacaPort": 5555}'`; `b"hello"` → None).
- [ ] **Step 2:** Run → FAIL; implement `pico/discovery.py`; run → PASS.
- [ ] **Step 3:** Write `pico/main.py` and `sim.py`.
- [ ] **Step 4:** Start `python3 sim.py` in the background; run
  `conformu alpacaprotocol http://localhost:5555/api/v1/focuser/0` and
  `conformu conformance http://localhost:5555/api/v1/focuser/0`.
  Expected: both report 0 errors and 0 issues. Fix and add a regression test for each failure.
- [ ] **Step 5:** Commit `feat: discovery, main entry point and desktop simulator`.

### Task 6: Deploy to the Pico and verify on hardware

**Files:** Create `tools/deploy.sh`; modify `CLAUDE.md`, `ACKNOWLEDGEMENTS`, `README.md`

- [ ] **Step 1:** `pip install --user mpremote`; `tools/deploy.sh` copies every file in `pico/` (including `secret.toml` if present) to `:` and does `mpremote reset`.
- [ ] **Step 2:** Clean the board: remove the old files (`app.py compat.py config.py discovery.py exceptions.py focuser.py focuserdevice.py log.py logging.py management.py setup.py shr.py threading.py requirements.txt alpyca.log`) and `/tools` recursively.
- [ ] **Step 3:** Deploy, then read serial output: expect the printed IP and no traceback.
- [ ] **Step 4:** `curl http://<ip>:5555/management/v1/configureddevices` → one Focuser. Send `alpacadiscovery1` over UDP broadcast → reply with port 5555.
- [ ] **Step 5:** Run both ConformU checks against `http://<ip>:5555/api/v1/focuser/0` → 0 errors, 0 issues.
- [ ] **Step 6:** Update `CLAUDE.md` (new layout, test/sim/deploy/ConformU commands), `README.md` (wiring table, setup), `ACKNOWLEDGEMENTS` (Microdot, MIT; drop AlpycaDevice).
- [ ] **Step 7:** Commit `chore: deploy script and docs`. Hand over for the NINA autofocus test (user).
