# NINA-compatible Alpaca focuser on Pico 2 W — design

## Intent

Use the breadboard focuser (Pico 2 W + BigTreeTech TMC2209 v1.3 + NEMA 17) from
NINA for autofocus runs. NINA must discover it on the network, connect, read
position and run autofocus without errors. The old AlpycaDevice-based code is
scrapped; this is a fresh, small MicroPython implementation.

## Goals

- ASCOM Alpaca **IFocuserV4**, **absolute** focuser, device number 0.
- Found by NINA via Alpaca discovery (UDP 32227) and usable for autofocus.
- `IsMoving`, `Position` and `Halt` respond while a move is in progress.
- Starts by itself at power-up (Wi-Fi from `secret.toml`).
- **Passes ASCOM ConformU 4.1** (user requirement): both `alpacaprotocol` and
  `conformance` checks against the focuser, with no errors or issues.

## Non-goals

- Position persistence, homing, limit switches or encoders.
- Temperature sensing / temperature compensation.
- TMC2209 UART configuration (driver stays in standalone mode, MS1/MS2 floating = 1/8 microstep).
- Acceleration ramps, multiple devices, authentication, HTTPS.

## Anti-goals

- HTTP server freezing while the motor steps (breaks NINA polling and Halt).
- Motor energized before a client connects.
- Logs or state files slowly filling the ~2 MB flash.

## Decisions (from the user)

- **Position model:** on every boot, `Position` = middle of the range. The user
  hand-sets focus near the middle before powering up. No persistence.
- **Approach 1** (below): Microdot + hardware timer for step pulses.
- Ground between driver and Pico is connected (user confirmed).

## Approaches considered

1. **Microdot + `machine.Timer` step generation — chosen.** Microdot 2.x
   (already on the board) serves HTTP on asyncio; a periodic hardware timer
   callback emits one step per tick toward the target. Simple, small, non-blocking.
2. **Microdot + PIO step generation.** Exact pulse timing with zero CPU, but
   step counting and clean halts need more code. Only worth it for fast moves
   with acceleration ramps, which a focuser doesn't need.
3. **Hand-written HTTP server.** Fewer files, but re-implements request parsing
   Microdot already does well.

## Defaults (my calls, all in `config.toml`)

| Setting | Default | Notes |
|---|---|---|
| `max_step` | 100000 | ≈ 31 motor turns each way at 1/8 µstep (1600 steps/rev) |
| `start_position` | 50000 | middle of range |
| `max_increment` | 100000 | = `max_step` |
| `steps_per_sec` | 800 | timer frequency |
| `reverse` | false | inverts DIR |
| `hold_when_idle` | true | driver stays enabled while connected; TMC2209 reduces standstill current itself |
| `port` | 5555 | Alpaca HTTP port |
| pins | STEP 16, DIR 20, EN 21 | EN active low |

Driver enable policy: EN is **high (disabled) at boot**, enabled on Connect,
disabled on Disconnect. With `hold_when_idle = false` it is also disabled after
each move completes.

## Architecture

Everything that goes on the Pico lives in `pico/` and is copied to the board root.

| File | Responsibility |
|---|---|
| `main.py` | Join Wi-Fi (retry until connected, on-board LED on when connected, hostname `pico-focuser`), print IP, then `asyncio.run()` the HTTP server and discovery responder together. |
| `settings.py` | Load `config.toml` + `secret.toml` with the small TOML parser (`toml.py`, kept from the old code). Missing `secret.toml` → clear message, no crash. |
| `stepper.py` | `Stepper` class: `position`, `target`, `is_moving`, `move_to(n)`, `halt()`, `enable()/disable()`. A `machine.Timer` at `steps_per_sec` calls a callback that, if `position != target`, sets DIR, pulses STEP and updates `position`; when it arrives it stops the timer. `halt()` sets `target = position` and stops the timer. Hardware access goes through injected pin/timer objects so it can be tested on the desktop with fakes. |
| `alpaca.py` | Microdot app with all routes: Alpaca common members, focuser members, management API, and setup pages. Contains request parsing and response building. |
| `discovery.py` | Non-blocking UDP socket on 32227 polled from an asyncio task; replies `{"AlpacaPort": 5555}` to `alpacadiscovery1`. |
| `microdot.py`, `toml.py` | Vendored libraries (unchanged). |
| `config.toml`, `secret.toml` | Settings / Wi-Fi credentials (`secret.toml` is git-ignored). |

`blink.py` stays as a standalone wiring test. All the old AlpycaDevice files
(`app.py`, `compat.py`, `config.py`, `exceptions.py`, `focuser.py`,
`focuserdevice.py`, `log.py`, `logging.py`, `management.py`, `setup.py`,
`shr.py`, `threading.py`) are deleted from the repo and from the Pico, along
with the stray `/tools/conformu.linux-x64` folder on the Pico's flash.

## Alpaca behaviour (rules the builder must follow)

- Routes: `/api/v1/focuser/{devnum}/{member}`. Device number other than 0, or unknown member → HTTP 400 / 404.
- Every response is JSON (`Content-Type: application/json`) with `Value` (for gets),
  `ClientTransactionID` (echoed, 0 if missing), `ServerTransactionID` (increments),
  `ErrorNumber`, `ErrorMessage`. Alpaca errors use HTTP 200 + `ErrorNumber`.
- Parameter names: case-**insensitive** in GET query strings, case-**sensitive** in PUT form bodies.
  Non-numeric or negative `ClientID` / `ClientTransactionID` → HTTP 400. Missing required PUT parameter → HTTP 400.
- Error numbers: NotImplemented `0x400`, InvalidValue `0x401`, NotConnected `0x407`, InvalidOperation `0x40B`, Driver `0x500`.
- Common members: `connected` (get/put), `connect`, `disconnect`, `connecting` (always false; connect is instant),
  `description`, `driverinfo`, `driverversion`, `interfaceversion` = 4, `name`, `supportedactions` = `[]`,
  `devicestate` (`IsMoving`, `Position`, `TimeStamp`), `action` / `commandblind` / `commandbool` / `commandstring` → NotImplemented.
- Focuser members: `absolute` = true; `ismoving`; `maxincrement`; `maxstep`; `position`;
  `stepsize` → NotImplemented; `tempcompavailable` = false; `tempcomp` get = false, put false accepted,
  put true → NotImplemented; `temperature` → NotImplemented; `halt`;
  `move` (`Position` int, outside `0..max_step` → InvalidValue; a move while moving retargets).
- Members other than the identity ones (name, description, driver*, interfaceversion, supportedactions,
  connected/connecting) return NotConnected when not connected.
- Management: `/management/apiversions` = `[1]`, `/management/v1/description`
  (server name, manufacturer, version, location), `/management/v1/configureddevices`
  with a stable `UniqueID` derived from `machine.unique_id()`.
- Setup: `/setup` and `/setup/v1/focuser/0/setup` return a simple HTML status page (position, moving, IP).

## Testing

ConformU 4.1.0 (Linux, command line) is at
`~/git/pic-pico-projects/tools/conformu.linux-x64/conformu`. Its two checks are the acceptance test:

```
conformu alpacaprotocol http://HOST:5555/api/v1/focuser/0
conformu conformance   http://HOST:5555/api/v1/focuser/0
```

1. **Desktop unit tests (pytest):** Microdot runs on CPython, so `alpaca.py` and `stepper.py` are
   tested on the computer with a fake `machine` module (fake Pin/Timer). Covers response format,
   parameter rules, error numbers, move/halt/retarget logic and range limits.
2. **Desktop simulator + ConformU:** a small `sim.py` (desktop only, not copied to the Pico) starts the
   same app on CPython with simulated hardware whose timer really ticks in a thread. ConformU runs
   against `localhost` until both checks are clean, before anything is flashed.
3. **On the Pico:** deploy with `mpremote`, power-cycle, confirm it starts from `main.py`, re-run both
   ConformU checks against the Pico's IP, then connect from NINA and run a short autofocus.

## Left to the builder

File-internal structure, test layout, exact HTML of the setup page, the deploy command wrapper.
