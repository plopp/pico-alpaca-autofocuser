# Focuser carrier PCB — design

## Intent

Replace the breadboard with a 50 × 80 mm PCB that JLCPCB manufactures **and assembles**.
The user plugs in their own Raspberry Pi Pico 2 W and BigTreeTech TMC2209 v1.3 (sourced
separately). One 12 V barrel-jack supply powers everything, which also fixes the USB-power
brownouts seen during testing. A 3.5 mm jack takes a DS18B20 temperature sensor on a cable.

## Goals

- Board outline exactly **80 × 50 mm** (2-layer, 1.6 mm FR-4).
- Sockets (female 2.54 mm headers) for the Pico 2 W (2 × 1×20) and the TMC2209 (2 × 1×8); every other part soldered by JLCPCB.
- **Barrel jack and the Pico's USB connector on the same 50 mm short edge**, side by side; Pico lies lengthwise with its USB end at that edge.
- 12 V in → motor supply (VM) and a 5 V switching regulator module feeding the Pico's VSYS.
- Drives a standard bipolar NEMA 17 through a 4-pin JST XH connector.
- DS18B20 on a 3.5 mm TRS jack.
- Deliverables JLCPCB accepts: Gerbers + drill (zip), BOM and CPL (pick-and-place) in JLCPCB format, plus the KiCad project, schematic PDF and 3D renders.

## Non-goals

- TMC2209 UART control, sensorless homing/DIAG, limit switches, encoders.
- Firmware changes (DS18B20 `Temperature` support is a separate follow-up).
- Enclosure design.

## Anti-goals

- Pico's USB plug blocked by the barrel jack, the socket height, or the board edge.
- Motor powered before the Pico has booted (EN must be pulled to "off").
- Plugging the sensor in browning out the Pico's 3.3 V.
- A board that fails JLCPCB's DFM checks or can't be assembled from stocked parts.

## Approach (chosen: 1)

1. **JLCPCB assembly + drop-in 3-pin switching regulator module — chosen.** Few parts, no
   delicate switcher layout; scripted design verified with KiCad DRC and 3D renders.
2. JLCPCB assembly + discrete SMD buck regulator — cheaper, but switcher layout is the easiest
   place for a scripted design to go wrong; not worth it at this board size.
3. PCBWay turnkey — any distributor part, but slower and pricier.

## Schematic

**Power**
- J1 barrel jack 5.5 × 2.1 mm, centre positive, 12 V.
- F1 resettable fuse 2 A hold (1812) → D1 SS34 Schottky in series (reverse-polarity protection, ~0.5 V drop) → net **+12V**.
- +12V → TMC2209 **VM**, with C1 100 µF ≥ 35 V electrolytic + C2 100 nF next to the VM pin.
- +12V → U1 5 V switching regulator module (7805 pin-out: IN, GND, OUT) with C3/C4 10 µF 50 V at its input/output per module datasheet → D2 SS14 Schottky → Pico **VSYS** (pin 39). The Pico's own VBUS→VSYS diode lets USB and 12 V coexist.

**Pico 2 W (U2, socket)** — STEP **GP16** (pin 21), DIR **GP20** (pin 26), EN **GP21** (pin 27),
DS18B20 data **GP22** (pin 29), **3V3 OUT** (pin 36), **VSYS** (pin 39), all GND pins to the ground plane.

**TMC2209 (U3, socket; BigTreeTech v1.3 pinout)**
- Power row: VM (+12V), GND, A2, A1, B1, B2, VIO (3V3), GND.
- Logic row: EN, MS1, MS2, RX, TX, CLK, STEP, DIR.
- R1 10 kΩ EN → 3V3 (driver off until the Pico drives EN low). C5 100 nF at VIO.
- MS1, MS2: solder jumpers JP1/JP2 to VIO, **open by default** (1/8 microstep, as the firmware assumes).
- RX, TX, CLK: unconnected.

**Motor (J2, JST XH 4-pin)** — 1 = A1, 2 = A2, 3 = B1, 4 = B2 (coil A on pins 1–2, coil B on 3–4). Silkscreen labels the coils; the user checks their cable's coil pairs.

**DS18B20 (J3, 3.5 mm TRS jack)** — Tip = DQ → GP22 with R2 4.7 kΩ pull-up to 3V3; Ring = 3V3 through R3 100 Ω (limits the short while a plug is inserted); Sleeve = GND. Silkscreen shows T/R/S.

## Layout (80 × 50 mm, origin top-left, x along 80 mm)

- **Left short edge (x = 0, the rear):** Pico USB connector (Pico's USB end flush with the edge, footprint rotated so the board runs along x), then J1 barrel jack and J3 3.5 mm jack below it, both opening outward (user change: the temperature jack comes out of the rear with USB and power). Both jacks reach 2 mm past the edge (user change), flush with the outside of a 2 mm rear wall: J1's body front, and J3's nose (its body front sits on the edge).
- Pico occupies roughly x 0–52, along one long edge; U1 regulator and power parts near J1.
- TMC2209 socket to the right of the Pico; C1 within ~10 mm of VM.
- **Right short edge (x = 80):** J2 motor connector, cable leaving away from power/USB.
- **No mounting holes** (user change): the board slides into slots in the case along its long edges, so no parts within 2.5 mm of either long edge.
- Ground pour on both layers; +12V and motor traces ≥ 1.0 mm; signal traces 0.25 mm; JLCPCB 2-layer rules (≥ 0.127 mm clearance/track, ≥ 0.3 mm drill).
- Silkscreen: board name/version, pin labels for J1/J2/J3, socket outlines labelled "Pico 2 W" / "TMC2209 (EN pin here)", orientation marks so neither module can be plugged in backwards unnoticed.

## Parts (JLCPCB/LCSC)

Verified in stock on LCSC category pages (re-checked at order time by JLCPCB's BOM matcher):

| Ref | Part | LCSC |
|---|---|---|
| J1 | XUNPU DC-005-A200 barrel jack | C720557 |
| J2 | JST B4B-XH-A | C144395 |
| D1 | SS34 (SMA) | C8678 (Basic) |
| D2 | SS14 (SMA) | C2480 (Basic) |
| F1 | ASMD1812-200-30V | C2982282 |
| C2, C5 | 100 nF 50 V X7R 0805 | C49678 (Basic) |
| C3, C4 | 10 µF 50 V X7R 1206 | C89632 |
| R1 | 10 kΩ 0603 | C25804 (Basic) |

**Still to confirm** (not found by automated lookup; the builder confirms on jlcpcb.com/parts, with fallbacks):
- U1 5 V switching module, TO-220 pin-out (Mornsun K7805-500R3/-1000R3 or RECOM R-78E5.0-0.5). Fallback: 5 V/1 A SIP-3 module of any brand with the same pin-out.
- 1×20 and 1×8 female headers 2.54 mm (1×8 candidate C54973824). Fallback for 1×20: two 1×10 sockets end to end.
- C1 100 µF 50 V electrolytic: radial THT, or SMD C72480 (D8 × 10.2) as fallback.
- J3 3.5 mm TRS jack (PJ-320/PJ-3xx class), R2 4.7 kΩ and R3 100 Ω 0603 (Basic parts expected).

## Verification

- KiCad 10 ERC clean, DRC clean against JLCPCB 2-layer rules, board edge exactly 80.00 × 50.00 mm.
- 3D render (top/side) shows: USB plug and barrel jack both reachable from the left edge with the Pico socketed; no parts under the modules taller than the socket clearance.
- Netlist check script: every connection in "Schematic" above exists (STEP/DIR/EN/GP22/VSYS/3V3/VM/coils).
- Gerbers viewed in KiCad's Gerber viewer; BOM/CPL rows match the board's footprints and rotations.

## Left to the builder

Exact coordinates, routing, silkscreen art, footprint variants, and resolving the "still to confirm" parts with the fallbacks above.

## Tooling

KiCad 10.0.7 from the user's AppImage (`~/Downloads/kicad-10.0.7-x86_64.AppImage`), extracted for
`kicad-cli` and the `pcbnew` Python API. Board generated by a Python script kept in `hardware/`
(re-runnable), outputs in `hardware/fab/`.
