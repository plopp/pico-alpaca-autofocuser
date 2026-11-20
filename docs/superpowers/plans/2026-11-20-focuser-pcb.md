# Focuser Carrier PCB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A scripted KiCad 10 design of the 80 × 50 mm focuser carrier board, with JLCPCB-ready Gerbers, BOM and CPL.

**Architecture:** One pure-Python data file (`hardware/design.py`) holds every part and net. Generators turn it into a KiCad schematic (system Python) and a placed board (KiCad's bundled Python with `pcbnew`). FreeRouting routes the board headless, and `kicad-cli` runs ERC/DRC and exports fab files. pytest (system Python) checks every output against the spec.

**Tech Stack:** KiCad 10.0.7 (extracted AppImage: `kicad-cli`, `python3.11` + `pcbnew`), FreeRouting 2.x (Java 21), Python 3 + pytest.

**Spec:** `docs/superpowers/specs/2026-11-20-focuser-pcb-design.md`

## Global Constraints

- Board outline exactly 80.00 × 50.00 mm, 2 layers, 1.6 mm; origin top-left, x along the 80 mm side.
- Barrel jack J1 and the Pico's USB end both at the **left short edge (x = 0)**; motor J2 and 3.5 mm jack J3 at the **right short edge (x = 80)**.
- Pico pins: STEP GP16 (pin 21), DIR GP20 (pin 26), EN GP21 (pin 27), DS18B20 GP22 (pin 29), 3V3 OUT (pin 36), VSYS (pin 39); GND pins 3, 8, 13, 18, 23, 28, 33, 38.
- TMC2209 (BTT v1.3) logic row: EN, MS1, MS2, RX, TX, CLK, STEP, DIR; power row: VM, GND, A2, A1, B1, B2, VIO, GND (VM opposite EN). Rows 12.7 mm apart; RX/TX/CLK unconnected.
- JLCPCB 2-layer rules: track/clearance ≥ 0.127 mm, drill ≥ 0.3 mm; +12V, motor and GND power traces ≥ 1.0 mm; signals 0.25 mm.
- Every part except the modules themselves is assembled by JLCPCB (SMD + THT); every BOM line carries an LCSC number.
- Generated outputs are reproducible: `hardware/build.sh` regenerates everything from `design.py`.
- Commits go on branch `pcb`, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- **USB plug blocked** when the Pico is socketed: nothing taller than the socket in a 12 mm-wide strip in front of the Pico's USB end at x = 0. Test: Task 3 `test_usb_and_jack_access_clear`.
- **Barrel jack polarity reversed**: the jack's centre pin must be on `VIN_RAW` (positive). Test: Task 3 `test_barrel_jack_centre_is_positive`.
- **Module plugged in backwards**: silkscreen marks pin 1 / "EN" / "USB" at the right ends. Test: Task 3 `test_orientation_silkscreen`.
- **Motor-current traces too thin** after autorouting. Test: Task 4 `test_power_track_widths`.
- **JLCPCB rejects the CPL** (refs not on the board, coordinates off-board, missing rotations). Test: Task 5 `test_cpl_matches_board`.

---

## File Structure

| Path | Responsibility |
|---|---|
| `hardware/design.py` | PARTS and NETS: the single source of truth (pure Python) |
| `hardware/kicad_env.py` | Locates the KiCad install (`KICAD_ROOT`) and FreeRouting jar; helpers to run `kicad-cli` and KiCad's Python |
| `hardware/setup_tools.sh` | Extracts the AppImage to `~/.local/opt/kicad-10.0.7` and downloads FreeRouting into `~/.local/opt/freerouting/` (idempotent) |
| `hardware/gen_schematic.py` | Writes `hardware/kicad/focuser.kicad_sch` (system Python) |
| `hardware/gen_board.py` | Writes `hardware/kicad/focuser.kicad_pcb` and `focuser.dsn` (KiCad Python) |
| `hardware/route.py` | Runs FreeRouting on the DSN, imports the SES, refills zones (KiCad Python) |
| `hardware/gen_fab.py` | Gerbers/drill zip, JLC BOM/CPL, renders, schematic PDF into `hardware/fab/` |
| `hardware/build.sh` | Runs everything in order |
| `hardware/README.md` | Ordering at JLCPCB, jumpers, connector pinouts |
| `tests/hardware/` | pytest checks (skipped when `KICAD_ROOT` is missing) |

## Part and net decisions (used by Tasks 1–5)

| Ref | Part | Symbol | Footprint | LCSC |
|---|---|---|---|---|
| J1 | DC-005 barrel jack | Connector:Barrel_Jack | Connector_BarrelJack:BarrelJack_Horizontal (check against DC-005-A200 drawing; adjust pads if needed) | C720557 |
| F1 | 2 A PTC 1812 | Device:Polyfuse | Fuse:Fuse_1812_4532Metric | C2982282 |
| D1 | SS34 | Device:D_Schottky | Diode_SMD:D_SMA | C8678 |
| D2 | SS14 | Device:D_Schottky | Diode_SMD:D_SMA | C2480 |
| U1 | R-78E5.0-0.5 class | Converter_DCDC:R-78E5.0-0.5 | Converter_DCDC:Converter_DCDC_RECOM_R-78E-0.5_THT | confirm (Task 5) |
| C1 | 100 µF 50 V | Device:C_Polarized | Capacitor_THT:CP_Radial_D8.0mm_P3.50mm | confirm (Task 5) |
| C2, C5 | 100 nF 0805 | Device:C | Capacitor_SMD:C_0805_2012Metric | C49678 |
| C3, C4 | 10 µF 50 V 1206 | Device:C | Capacitor_SMD:C_1206_3216Metric | C89632 |
| R1 | 10 kΩ 0603 | Device:R | Resistor_SMD:R_0603_1608Metric | C25804 |
| R2 | 4.7 kΩ 0603 | Device:R | Resistor_SMD:R_0603_1608Metric | confirm (Task 5) |
| R3 | 100 Ω 0603 | Device:R | Resistor_SMD:R_0603_1608Metric | confirm (Task 5) |
| JP1, JP2 | solder jumper, open | Jumper:SolderJumper_2_Open | Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm | — (not assembled) |
| J2 | JST B4B-XH-A | Connector:Conn_01x04_Pin | Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical | C144395 |
| J3 | 3.5 mm TRS jack | Connector_Audio:AudioJack3 | Connector_Audio:Jack_3.5mm_CUI_SJ1-3523N_Horizontal (or the confirmed LCSC part's footprint) | confirm (Task 5) |
| J4, J5 | 1×20 female header (Pico) | Connector:Conn_01x20_Socket | Connector_PinSocket_2.54mm:PinSocket_1x20_P2.54mm_Vertical | confirm (Task 5) |
| J6, J7 | 1×8 female header (TMC2209) | Connector:Conn_01x08_Socket | Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical | C54973824 |
| H1–H4 | M3 hole | Mechanical:MountingHole | MountingHole:MountingHole_3.2mm_M3 | — |

Socket pin mapping: **J4 pin n = Pico pin n** (pins 1–20); **J5 pin k = Pico pin 41 − k** (so J5 pin 1 = Pico pin 40, at the USB end). **J6 = TMC logic row**, pin 1 = EN … pin 8 = DIR; **J7 = TMC power row**, pin 1 = VM … pin 8 = GND.

Nets: `VIN_RAW` (J1 centre, F1), `VIN_FUSED` (F1, D1 anode), `+12V` (D1 cathode, U1 VIN, C1+, C2, C3, J7.1 VM), `+5V` (U1 VOUT, C4, D2 anode), `VSYS` (D2 cathode, J5 pin for Pico 39), `+3V3` (Pico 36, J7.7 VIO, C5, R1, R2, R3, JP1, JP2), `GND` (all GND), `STEP`, `DIR`, `EN` (+R1), `MS1` (J6.2, JP1), `MS2` (J6.3, JP2), `TEMP_DQ` (Pico 29, R2, J3 tip), `TEMP_VDD` (R3, J3 ring), `MOT_A1/A2/B1/B2` (J7.4/J7.3/J7.5/J7.6 ↔ J2 pins 1/2/3/4).

---

### Task 1: Tools and design data

**Files:** Create `hardware/setup_tools.sh`, `hardware/kicad_env.py`, `hardware/design.py`, `tests/hardware/conftest.py`, `tests/hardware/test_design.py`

**Interfaces:**
- Produces: `design.PARTS: dict[str, Part]` with `Part(ref, symbol, footprint, value, lcsc: str|None, assembled: bool)`; `design.NETS: dict[str, list[tuple[str, str]]]` (net → `(ref, pin_number)`); `design.pico_pin(n: int) -> tuple[str, str]` (Pico pin → socket `(ref, pin)`).
- Produces: `kicad_env.KICAD_ROOT: Path`, `kicad_env.cli(*args) -> CompletedProcess`, `kicad_env.kipython(script, *args) -> CompletedProcess`, `kicad_env.FREEROUTING_JAR: Path`. `KICAD_ROOT` from env, default `~/.local/opt/kicad-10.0.7/squashfs-root`.
- `tests/hardware/conftest.py`: skip the whole directory if `kicad-cli` isn't found (design-data tests still run).

- [ ] **Step 1:** `git checkout -b pcb`; run `hardware/setup_tools.sh` (extract AppImage once; download the FreeRouting 2.x release jar, version pinned in the script). Expected: `kicad-cli version` → `10.0.7`, `java -jar … -help` prints usage.
- [ ] **Step 2: Failing tests** `test_design.py`: `test_spec_signal_nets` (`pico_pin(21)` in STEP with J6.7; `pico_pin(26)` in DIR with J6.8; `pico_pin(27)` in EN with J6.1 and R1; `pico_pin(29)` in TEMP_DQ; `pico_pin(39)` in VSYS; `pico_pin(36)` in +3V3 with J7.7); `test_pico_gnd_pins` (3, 8, 13, 18, 23, 28, 33, 38 in GND); `test_motor_pairs` (J2.1/J2.2 ↔ J7.4/J7.3, J2.3/J2.4 ↔ J7.5/J7.6); `test_unconnected_tmc_pins` (J6.4, J6.5, J6.6 in no net); `test_no_pin_in_two_nets`; `test_assembled_parts_have_lcsc` (every `assembled` part has `lcsc` or the literal `"CONFIRM"`).
- [ ] **Step 3:** Run `python3 -m pytest tests/hardware/test_design.py -q` → FAIL (no module).
- [ ] **Step 4:** Implement `design.py` from the tables above; `kicad_env.py`.
- [ ] **Step 5:** Tests → PASS. Commit `feat(pcb): design data and KiCad tooling`.

### Task 2: Schematic

**Files:** Create `hardware/gen_schematic.py`, `tests/hardware/test_schematic.py`

**Interfaces:** Consumes `design`, `kicad_env`. Produces `hardware/kicad/focuser.kicad_pro` + `focuser.kicad_sch`.

Approach: KiCad 10 symbol libraries are directories (`<Lib>.kicad_symdir/<Name>.kicad_sym`). Copy each used symbol into `lib_symbols` (renamed `Lib:Name`), place parts on a grid, and attach a **local label named after the net** at every connected pin end (pin positions from the symbol's `pin` `at` fields, rotated with the instance). Put `no_connect` flags on unused pins. Add `PWR_FLAG` symbols on `+12V`, `GND`, `+3V3` and `+5V` so ERC sees driven power nets. Use a fresh UUID per element.

- [ ] **Step 1: Failing tests:** `test_erc_clean` (`kicad-cli sch erc --severity-error` → 0 errors); `test_netlist_matches_design` (`kicad-cli sch export netlist --format kicadsexpr`, parse nets → same `(ref, pin)` sets as `design.NETS`, ignoring auto-named single-pin nets).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(pcb): generated schematic`.

### Task 3: Board placement

**Files:** Create `hardware/gen_board.py`, `tests/hardware/test_board.py`

**Interfaces:** Consumes `design` (nets and footprints; footprints loaded with `pcbnew.FootprintLoad(<lib path>, <name>)`). Produces `hardware/kicad/focuser.kicad_pcb` (placed, unrouted, zones defined) and `focuser.dsn` (`pcbnew.ExportSpecctraDSN`).

Placement rules (coordinates are the builder's, within these constraints):
- Pico sockets J4/J5 horizontal (pins along x), rows 17.78 mm apart, along the top long edge. The USB end is at x = 0, so the Pico outline edge lies at x = 0 (offsets taken from `Module:RaspberryPi_Pico_Common_THT`: its pad 1 relative to its board outline).
- J1 at the left edge beside the Pico, opening outward. U1, F1, D1, D2, C3, C4 near J1.
- J6/J7 (12.7 mm apart) to the right of the Pico; C1 + C2 within 10 mm of J7 pin 1 (VM); C5 at J7 pin 7.
- J2 and J3 at the right edge, opening outward.
- H1–H4 near the corners, clear of everything.
- GND zones on F.Cu and B.Cu covering the board (0.3 mm clearance, thermal reliefs).
- Net classes: `Power` (+12V, VIN_RAW, VIN_FUSED, GND, MOT_*) 1.0 mm track; `Default` 0.25 mm.
- Silkscreen: "Pico 2 W ← USB" by the Pico's USB end, "TMC2209" with "EN" at J6 pin 1, "12V ⊕ centre" by J1, "A1 A2 B1 B2" by J2, "T=DATA R=3V3 S=GND" by J3, "MS1/MS2: open = 1/8" by JP1/JP2, board name + "v1.0".

- [ ] **Step 1: Failing tests:** `test_outline_80x50` (Edge.Cuts bounding box 80.00 × 50.00 ± 0.01); `test_all_parts_placed_on_board` (every design ref present, courtyard inside outline); `test_usb_and_jack_access_clear` (J1's opening and the Pico's USB end within 1 mm of x = 0; no other courtyard within 12 mm of x = 0 in the Pico's y-span); `test_right_edge_connectors` (J2, J3 within 3 mm of x = 80); `test_barrel_jack_centre_is_positive` (J1 centre-pin pad is in net VIN_RAW); `test_board_nets_match_design`; `test_orientation_silkscreen` (silk texts containing "USB", "EN", "12V" exist within 8 mm of the Pico's USB end, J6 pin 1 and J1 respectively); `test_no_courtyard_overlaps`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS. Render `kicad-cli pcb render --side top` to `hardware/fab/preview-top.png` and look at it.
- [ ] **Step 5:** Commit `feat(pcb): board outline and placement`.

### Task 4: Routing and DRC

**Files:** Create `hardware/route.py`; extend `tests/hardware/test_board.py`

**Interfaces:** Consumes the DSN from Task 3 and `kicad_env.FREEROUTING_JAR`. Produces the routed `focuser.kicad_pcb`.

- [ ] **Step 1: Failing tests:** `test_drc_clean` (`kicad-cli pcb drc --schematic-parity --severity-error` → 0 violations, 0 unconnected items); `test_power_track_widths` (every track in nets +12V, VIN_RAW, VIN_FUSED, MOT_* ≥ 1.0 mm).
- [ ] **Step 2:** Run → FAIL (unrouted). **Step 3:** Implement `route.py`: `java -jar freerouting.jar -de focuser.dsn -do focuser.ses -mp 30` (headless), then `pcbnew.ImportSpecctraSES`, zone refill (`pcbnew.ZONE_FILLER`), save. If FreeRouting leaves connections open, adjust placement in Task 3's script and re-run (record a ruling).
- [ ] **Step 4:** Tests → PASS. **Step 5:** Commit `feat(pcb): autorouted board, DRC clean`.

### Task 5: Fabrication outputs and part confirmation

**Files:** Create `hardware/gen_fab.py`, `hardware/build.sh`, `tests/hardware/test_fab.py`; modify `hardware/design.py` (confirmed LCSC numbers)

**Interfaces:** Consumes the routed board and the schematic. Produces in `hardware/fab/`: `focuser-gerbers.zip` (Gerbers + Excellon drill, JLCPCB layer naming), `focuser-bom-jlc.csv` (columns `Comment,Designator,Footprint,LCSC`), `focuser-cpl-jlc.csv` (columns `Designator,Mid X,Mid Y,Layer,Rotation`, mm, top layer), `focuser-schematic.pdf`, `render-top.png`, `render-iso.png`.

- [ ] **Step 1:** Confirm the `"CONFIRM"` parts (U1, C1, R2, R3, J3, J4/J5) on jlcpcb.com/parts or lcsc.com product pages (in stock, footprint matches). Use the spec's fallbacks if needed; record each choice as a ruling. A changed footprint goes back through Tasks 3–4.
- [ ] **Step 2: Failing tests:** `test_gerber_zip_contents` (F_Cu, B_Cu, F_Mask, B_Mask, F_Silkscreen, B_Silkscreen, Edge_Cuts Gerbers plus a drill file); `test_bom_has_lcsc_for_every_assembled_part` (no "CONFIRM", no blanks); `test_cpl_matches_board` (CPL designators == assembled refs; every Mid X/Y inside 0–80 / 0–50 after converting KiCad's y-down coordinates to JLC's convention; rotation present).
- [ ] **Step 3:** Run → FAIL. **Step 4:** Implement `gen_fab.py` and `build.sh`. **Step 5:** Run → PASS; open the renders and confirm the USB/jack edge visually.
- [ ] **Step 6:** Commit `feat(pcb): JLCPCB fabrication outputs`.

### Task 6: Documentation

**Files:** Create `hardware/README.md`; modify `README.md`, `CLAUDE.md`

- [ ] **Step 1:** `hardware/README.md` covers:
  - how to order at JLCPCB: upload the Gerber zip; enable assembly, top side, with through-hole assembly for the sockets and connectors; upload the BOM and CPL; and check the rotations in JLC's preview, especially the diodes and C1 polarity
  - jumper meanings
  - the J2 coil pairs, plus checking the motor cable with a multimeter
  - the J3 TRS pinout
  - plugging in the modules: Pico USB toward the jack edge, TMC2209 EN at the marked pin
  - setting the TMC2209 current with its potentiometer
- [ ] **Step 2:** Root README: replace the breadboard wiring table with a pointer to the board (keep the table for breadboard builds). CLAUDE.md: `hardware/` layout and `hardware/build.sh`, `python3 -m pytest tests/hardware -q`.
- [ ] **Step 3:** `python3 -m pytest -q` (whole repo) → all pass. Commit `docs(pcb): ordering and assembly guide`.
