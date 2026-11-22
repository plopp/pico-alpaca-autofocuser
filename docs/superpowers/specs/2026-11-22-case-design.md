# Focuser case design

## Intent

One printed unit on the astro rig holds the NEMA 17 motor and the carrier PCB (v1.0, ordered
2026-11-22). The motor drives the Askar FMA180 Pro's synchronizer ring with a belt; the unit
screws to the user's bracket with a camera screw. Cables (12 V, DS18B20, USB) leave at the
rear, towards the camera end.

## Goals

- Motor and board in one closed case, printable on the user's FDM printer (OrcaSlicer),
  in PETG or ASA (cold nights, sun during the day).
- Belt tension by sliding the whole unit along the bracket slot, which runs perpendicular to
  the tube; a ridge on the bottom runs in the slot so the unit cannot twist around the screw.
- Rear wall lines up exactly with the board's connectors, taken from the PCB data.
- Driver potentiometer and microstep jumpers reachable without taking the motor out.

## Non-goals

- No other lenses or telescopes; the FMA180 Pro geometry only.
- No lens bracket: the user has one (with a slot for the camera-thread screw).
- No weatherproofing beyond a closed case (no seals, no gaskets).

## Anti-goals

- Anything that lets the belt go slack during a night (the unit creeping round its screw).
- Metal or dense material over the Pico's antenna end.
- Supports inside small holes or slots that are hard to clean out.

## Facts it is built on

**Drive** (checked by the user on the lens): GT2 closed belt, 6 mm wide, 280 mm (140 teeth,
123-3D DME00119); GT2 16-tooth pulley, 5 mm bore, on the motor shaft. The belt fits the
FMA180 Pro's synchronizer ring (Askar's manual calls it MXL; the GT2 belt seats well).
With a ring of about 64 mm, the motor shaft ends up about 77 mm from the tube axis.

**FMA180 Pro** (Askar manual): tube Ø58 mm, 167.5 mm long, 109 mm high with its base;
synchronizer ring behind the front section.

**Motor:** NEMA 17, 42.3 mm square, 4 × M3 holes on a 31 mm square, Ø22 × 2 mm boss,
Ø5 mm shaft. The case fits bodies up to 48 mm long (user: any NEMA 17 up to 48 mm); a
shorter motor just leaves more room behind it for the cable. The motor's own
connector (6-pin JST PH) sits on one side near its rear.

**Board** (`hardware/gen_board.py`, v1.0): 80 × 50 × 1.6 mm, slides in slots along its long
edges (no parts in the 2.5 mm strips). Rear (left) short edge, top to bottom:
- Pico USB: connector face on the board edge; the plug leaves 3 mm of metal exposed (user),
  so a plug-sized hole through a 2 mm wall works.
- J1 DC-005 12 V jack: body front 2 mm past the edge.
- J3 PJ-320D 3.5 mm jack: body front on the edge, Ø5 × 2 mm nose past it.

Both jacks are meant to end flush with the outside of a **2 mm** rear wall.

Tall parts: TMC2209 module on 8.5 mm sockets (with heatsink about 20 mm above the board);
Pico on 8.5 mm sockets (about 13 mm); C1 10.5 mm. Through-hole pins stick out about 2–3 mm
underneath. Motor connector J2 (JST XH, vertical) at the front-right corner.

## Approaches

| | Approach | Trade-off |
|---|---|---|
| **Chosen** | **A. Python script with build123d** (in `.venv`), like the PCB scripts | Hole positions come from the PCB data; pytest checks the critical dimensions; STL + STEP out. Needs `pip install build123d`. |
| | B. OpenSCAD script | Easy to tweak in its GUI, but OpenSCAD must be installed and the positions typed in by hand; no tests. |

| | Layout | Trade-off |
|---|---|---|
| **Chosen** | **1. In line:** motor at the front, board flat behind it, rear wall = board's rear edge | Long, narrow box (about 145 × 56 × 50 mm with room for a 48 mm motor) along the tube; belt at the front where the ring is, cables at the rear. |
| | 2. Stacked: board under the motor | Shorter (about 90 mm) but about 100 mm tall; sticks out more beside the lens. |

The user agreed to A + 1 (2026-11-22).

## Design

**Three printed parts**, joined with M3 screws into M3 heat-set inserts:
1. **Body:** floor, two side walls with the board slots, and the 2 mm rear wall. Open at the
   front and top. The board slides in from the front until its rear edge meets the rear wall
   and the jacks sit in their holes.
2. **Front plate:** carries the motor (4 × M3 through the plate into the motor, boss in a
   Ø22.5 recess), shaft and pulley outside; screws to the front of the body. The motor body
   is inside the case, in front of the board.
3. **Lid:** closes the top, with ventilation slots over the TMC2209 and an opening (or
   removable cap) over the driver's potentiometer.

**Rear wall holes** (positions from the PCB data, heights from datasheets / KiCad 3D models):
- J1: rectangular cutout for the DC-005 body, about 0.3 mm clearance.
- J3: Ø5.4 mm hole for the nose.
- USB: about 9 × 4.5 mm rounded hole at the Pico connector's height (about 11 mm above the
  board), small outside chamfer, and a 1 mm deep recess for a long plug grip.

**Board slots:** 1.8 mm wide, 2 mm deep, with the board's underside about 5 mm above the floor
(clears the through-hole pins). They stop at the rear wall.

**Bottom:**
- 1/4"-20 hex nut (7/16" = 11.1 mm across flats, about 5.6 mm thick) embedded in the floor:
  the print pauses at the top of its pocket, the nut is dropped in and printed over (user:
  no access to the nut is needed). The camera screw comes up through the bracket slot. The
  boss needs about 8 mm of height, which the 5 mm under the board does not have, so it sits
  behind the motor (between motor and board). The STL comes with the pause height stated.
- Ridge running across the case (perpendicular to the tube, along the bracket slot) through
  the nut. Width is a parameter: the user measures the slot. Default 6.0 mm, 2 mm high.

**Inside:** room behind the motor for its cable (motor connector to J2); no part of the case
over the antenna end other than plastic.

**Outputs:** `case/` with the generator script, `case/out/*.stl` (each part, in print
orientation) and `*.step`; pytest checks in `tests/case/`.

## Parameters (top of the script)

Maximum motor body length (48 mm), bracket slot width, wall thickness (2 mm rear wall fixed by the board),
print clearance (default 0.3 mm), M3 insert size, 1/4"-20 nut size.

## Left to the builder

- Exact component heights and outlines for the rear holes: from the DC-005 / PJ-320D
  datasheets and the KiCad 3D models; the Pico USB height from the Pico datasheet.
- Screw count and placement, fillets, print orientation, vent pattern.
- Exact position of the camera nut in the space behind the motor (balance: the motor is
  the heaviest part).
- Potentiometer access: the BTT module's pot is at its VM end, which on the board is the
  end nearest the motor connector (`TMC_PIN1_Y` in `gen_board.py`).

## Still to confirm with the user

- Bracket slot width, to fit the ridge closer than the safe 6.0 mm default. The bracket is
  the 200 mm Arca-Swiss plate from the OpenAstroExplorer clamp kit: two long slots, each with
  a captive 1/4"-20 screw coming up from below, and raised rubber pads (so the case bottom
  stays flat apart from the ridge, and the 2 mm ridge stays above the screw head).
