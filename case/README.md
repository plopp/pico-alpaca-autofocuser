# Focuser case

One printed unit for the NEMA 17 motor and the carrier PCB (v1.0). It screws to the
OpenAstroExplorer Arca plate on the Askar FMA180 Pro with the plate's 1/4"-20 camera screw.
The motor's GT2 pulley drives the lens's synchronizer ring with a 280 mm closed belt. Cables
(USB, 12 V, temperature) leave at the rear.

Outside about 141 × 60 × 68 mm (with the 2 mm ridge underneath: 70 mm). It fits NEMA 17
motors from 34 to 48 mm long.

The files are generated. Run `.venv/bin/python -m case.build` (once:
`.venv/bin/pip install build123d==0.13.0 matplotlib pytest`). It writes the STLs, `case.step`
(the assembly) and two previews, `preview-iso.png` and `preview-rear.png`, to `case/out/`.

## Parts

| Printed (`case/out/`) | |
|---|---|
| `body.stl` | Floor, side walls with the board slots, rear wall. **Print pause at 7.6 mm** (nut). |
| `front_plate.stl` | Carries the motor. |
| `lid.stl` | Vents and a screwdriver hole over the driver's potentiometer; two fins hold the board in place (their tips sit in sockets in the floor). |
| `key.stl` | Two short bars, glued into the groove under the case; they run in the plate's slot. |

| Hardware | |
|---|---|
| 1 × 1/4"-20 hex nut (7/16" across flats, 5.6 mm thick) | embedded in the body |
| 8 × M3 heat-set inserts (Ø4.0 hole, ≤ 5 mm long) | 4 for the lid, 4 for the front plate |
| 4 × M3×6 | lid |
| 4 × M3×8 | front plate to body |
| 4 × M3×8 | motor to front plate |
| CA glue | key |

## Printing

PETG or ASA (cold nights, sun during the day), 0.2 mm layers, 4 walls, 30 % infill. No
supports needed. The STLs are already in print orientation:
- **Body**, floor down. **Add a pause at 7.6 mm** (in OrcaSlicer: right-click the layer
  slider at the first layer that starts at or above 7.6 mm → *Add pause*). At the pause,
  drop the nut into the hex pocket. The pocket is 6.0 mm deep, so the nut (5.6 mm) sits
  a little below its top. If it stands proud, don't resume: the nozzle would hit it.
  Resume, and the printer bridges over it.
- **Lid**, top down: the two fins stand upright.
- **Front plate**, outer face down.
- **Key**: two bars, flat.

## Assembly

1. Press the 8 heat-set inserts into the body: 4 vertical at the top corners, 4 in the front face.
2. Glue the key bars into the groove under the case, one either side of the screw hole.
3. Slide the board in from the front, along the slots, until the jacks sit in the rear
   wall and the Pico's USB socket is behind its hole.
4. Screw the motor to the front plate (M3×8), with its cable connector facing up.
   Fit the pulley.
5. Plug the motor cable into J2.
6. Screw the plate to the body (M3×8). The motor hangs inside the case.
7. Screw on the lid (M3×6). Its two fins stop the board sliding forwards.

The driver's current pot is reachable with a small screwdriver through the round hole in
the lid. The microstep jumpers need the lid off.

## On the rig

The 1/4"-20 screw needs to stick up **5.5 to 7 mm** above the surface the case sits on.
Less than that and it grips fewer than 3 threads of the nut. More than 7.6 mm and it pushes
on the plastic above the nut: put a washer or spacer under the case. Slide the unit along the plate's slot to tension the belt, then tighten the
screw. The ridge in the slot stops the unit turning.

## Changing it

All dimensions are in `case/params.py`, in the board's coordinates. `case/parts.py` builds
the parts. `.venv/bin/python -m pytest tests/case -q` checks the fit: the board slides in,
34–48 mm motors fit, the rear holes line up with the committed PCB, the nut is enclosed, and
the inserts line up with the screw holes.

- **Key width:** the default is 6.0 mm, which is safe in a 1/4" slot. Measure the plate's
  slot and regenerate with `.venv/bin/python -m case.build --key-width 6.5` (a little less
  than the slot). The groove follows.
- **USB height:** the hole assumes the Pico sits on 8.5 mm sockets, with the USB centre
  13.3 mm above the board. It is 6 mm tall, so it still fits if the real height is 1 mm
  off. Measure a real board and change `USB_Z` if it is further off.
