# Web control page — short design

**Intent:** Control the focuser from a browser (phone/laptop at the scope) without NINA:
reset the position, move to a target, jog, halt. Requested by the user.

**Goals** — the existing `/setup` page (and `/setup/v1/focuser/0/setup`) becomes a control page:
- Live readout, refreshed ~1 s: position, target, moving, NINA connected, temperature (once the temperature feature exists).
- **Reset position to 50000** (the configured start position): redefines the current position without moving; refused while moving.
- **Target + Move**: integer 0…max_step, clear error when out of range or not a number.
- **Jog**: −1000, −100, −10, +10, +100, +1000 (clamped to 0…max_step), and **Halt**.

**Settings** (requested by the user) — a form for the basic settings:
- Editable: `name`, `max_step`, `start_position`, `steps_per_sec`, `reverse`, `hold_when_idle`.
- **Save** writes them to `config.toml` on the Pico (validated: integers in sane ranges, start_position within 0…max_step).
  `steps_per_sec`, `reverse` and `hold_when_idle` apply immediately (when not moving); the others after **Restart**
  (a button that calls `machine.reset()` after the response is sent).
- Deliberately not editable from the page: Wi-Fi credentials, port, hostname and pins — a wrong value there could make
  the focuser unreachable, and the page has no password. They stay file-only.

**Behaviour**
- Not connected to NINA: a manual move enables the driver for the move and disables it on arrival (keeps the "not energized before a client connects" rule). Connected: normal hold policy.
- NINA connected: controls still work; the page shows a "NINA connected — moves will disturb autofocus" warning.
- Moves retarget like Alpaca `Move` (a new target during a move takes over).

**API** (outside `/api/v1`, so ConformU and NINA are unaffected): `GET /control/status` → JSON;
`POST /control/move` (`position`), `/control/jog` (`steps`), `/control/halt`, `/control/reset`,
`GET/POST /control/settings`, `POST /control/restart` (form-encoded); errors → HTTP 400 with a message.

**Implementation:** `Stepper.set_position(n)` (refused while moving), `Stepper.configure(steps_per_sec, reverse, hold_when_idle)`, `settings.save_settings(path, values)` writing `config.toml`; a small `control.py`
adding the routes to the Microdot app; the page is static HTML + a few lines of JS embedded in
the module (no external assets; must fit the Pico's RAM/flash comfortably).

**Non-goals:** authentication (trusted home network), editing Wi-Fi/port/pins from the page, charts.

**Verification:** pytest through the real server (status JSON, reset refused while moving, jog
clamping, driver enable/disable when not connected, page loads); ConformU on the simulator stays clean.
