"""The printed parts, built in the board frame (see params.py) as assembled.

    body()        floor, side walls with the board slots, rear wall with the jack holes,
                  embedded camera nut, key groove, M3 insert holes; open front and top
    front_plate() carries the motor
    lid()         vents, pot hole, board stop
    key(key_w)    the ridge, glued into the groove

board_envelope() and motor_envelope() are keep-out volumes for the tests and previews.
to_world() mirrors a part into a real (right-handed) frame for printing.
"""
from build123d import (Box, Circle, Part, Plane, Polygon, Pos, RectangleRounded,
                       RegularPolygon, extrude)

from case import params as p


def box(x0, y0, z0, x1, y1, z1) -> Part:
    """Axis-aligned box between two corners."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def rod_x(y, z, d, x0, x1) -> Part:
    """Cylinder along x."""
    return extrude(Plane.YZ.offset(x0) * Pos(y, z) * Circle(d / 2), amount=x1 - x0)


def rod_z(x, y, d, z0, z1) -> Part:
    """Cylinder along z."""
    return extrude(Plane.XY.offset(z0) * Pos(x, y) * Circle(d / 2), amount=z1 - z0)


def to_world(part: Part) -> Part:
    """Board frame (KiCad y, mirror-imaged) -> real frame: y becomes -y."""
    return part.mirror(Plane.XZ)


def board_envelope() -> Part:
    """Board v1.0 with everything on it, including the jacks' overhang and the pins below."""
    parts = [
        box(0, 0, -p.BOARD_T, p.BOARD_L, p.BOARD_W, 0),                 # PCB
        box(0, 2.5, -p.BOARD_T - 3.4, p.BOARD_L, 47.5, -p.BOARD_T),     # through-hole pins
        box(0, 2.9, 0, 53.0, 23.9, 15.0),                               # Pico on sockets
        box(63.0, 3.0, 0, 80.0, 24.0, 22.0),                            # TMC2209 + heatsink
        box(55.5, 29.8, 0, 64.5, 42.2, 11.0),                           # C1
        box(66.0, 24.6, 0, 79.5, 31.4, 16.0),                           # J2 + motor plug
        box(-p.REAR_WALL, p.J1_Y - p.J1_BODY[0] / 2, 0,
            11.5, p.J1_Y + p.J1_BODY[0] / 2, p.J1_BODY[1]),             # J1 DC-005
        box(0, 35.95, 0, 12.1, 45.05, 5.2),                             # J3 PJ-320D body
        rod_x(p.J3_Y, p.J3_Z, 5.0, -p.REAR_WALL, 0),                    # J3 nose
    ]
    return Part() + parts


def motor_envelope(length: float = p.MOTOR_MAX_L) -> Part:
    """NEMA 17 body hanging from the front plate, boss, shaft, connector on top at the rear."""
    rear = p.MOTOR_FACE_X - length
    half = p.MOTOR_SQUARE / 2
    top = p.MOTOR_BOTTOM_Z + p.MOTOR_SQUARE
    parts = [
        box(rear, p.MOTOR_Y - half, p.MOTOR_BOTTOM_Z, p.MOTOR_FACE_X, p.MOTOR_Y + half, top),
        rod_x(p.MOTOR_Y, p.SHAFT_Z, p.MOTOR_BOSS_D, p.MOTOR_FACE_X,
              p.MOTOR_FACE_X + p.MOTOR_BOSS_H),
        rod_x(p.MOTOR_Y, p.SHAFT_Z, 5.0, p.MOTOR_FACE_X, p.MOTOR_FACE_X + 24),
        box(rear, p.MOTOR_Y - 8, top, rear + 10, p.MOTOR_Y + 8, top + p.CONNECTOR_ROOM),
    ]
    return Part() + parts


def _corner_boss(x0, x1, outside_low: bool) -> Part:
    """Bulge outside a side wall at the top, 45° underneath so it prints without support."""
    y_wall, y_out = (p.OUTER_Y[0], p.OUTER_Y[0] - p.BOSS_OUT) if outside_low \
        else (p.OUTER_Y[1], p.OUTER_Y[1] + p.BOSS_OUT)
    profile = Polygon((y_wall, p.BOSS_BOTTOM_Z - p.BOSS_OUT), (y_wall, p.LID_UNDER_Z),
                      (y_out, p.LID_UNDER_Z), (y_out, p.BOSS_BOTTOM_Z))
    return extrude(Plane.YZ.offset(x0) * profile, amount=x1 - x0)


def _rear_holes() -> list[Part]:
    x0, x1 = -p.REAR_WALL - 1, 0.5
    usb_w, usb_h, usb_r = p.USB_HOLE
    rec_w, rec_h, rec_d = p.USB_RECESS
    return [
        extrude(Plane.YZ.offset(x0) * Pos(p.USB_Y, p.USB_Z)
                * RectangleRounded(usb_w, usb_h, usb_r), amount=x1 - x0),
        extrude(Plane.YZ.offset(x0) * Pos(p.USB_Y, p.USB_Z)
                * RectangleRounded(rec_w, rec_h, 2.0), amount=1 + rec_d),
        box(x0, p.J1_CUT_Y[0], p.J1_CUT_Z[0], x1, p.J1_CUT_Y[1], p.J1_CUT_Z[1]),
        rod_x(p.J3_Y, p.J3_Z, p.J3_HOLE_D, x0, x1),
    ]


def _bottom_cuts(key_w: float) -> list[Part]:
    groove_w = key_w + p.CLEAR
    hexagon = Plane.XY.offset(p.NUT_BOTTOM_Z) * Pos(p.NUT_X, p.NUT_Y) \
        * RegularPolygon((p.NUT_AF + p.CLEAR) / 2, 6, major_radius=False)
    return [
        box(p.NUT_X - groove_w / 2, p.OUTER_Y[0] - 1, p.BOTTOM_Z - 1,
            p.NUT_X + groove_w / 2, p.OUTER_Y[1] + 1, p.BOTTOM_Z + p.GROOVE_D),
        extrude(hexagon, amount=p.NUT_T),
        rod_z(p.NUT_X, p.NUT_Y, p.SCREW_HOLE_D, p.BOTTOM_Z - 1, p.NUT_BOTTOM_Z + 0.1),
    ]


def _insert_holes() -> list[Part]:
    holes = [rod_z(x, y, p.INSERT_D, p.LID_UNDER_Z - p.INSERT_DEPTH, p.LID_UNDER_Z + 1)
             for x, y in p.LID_SCREWS]
    holes += [rod_x(y, z, p.INSERT_D, p.MOTOR_FACE_X - p.INSERT_DEPTH, p.MOTOR_FACE_X + 1)
              for y, z in p.PLATE_SCREWS]
    return holes


def body(key_w: float = p.KEY_W) -> Part:
    shell = box(-p.REAR_WALL, p.OUTER_Y[0], p.BOTTOM_Z,
                p.MOTOR_FACE_X, p.OUTER_Y[1], p.LID_UNDER_Z)
    shell += [_corner_boss(x0, x1, low) for x0, x1 in p.BOSS_X for low in (True, False)]
    cuts = [
        box(0, p.INNER_Y[0], p.FLOOR_Z, p.MOTOR_FACE_X + 1, p.INNER_Y[1], p.LID_UNDER_Z + 1),
        box(0, p.SLOT_Y[0], p.SLOT_Z[0], p.MOTOR_FACE_X + 1, p.SLOT_Y[1], p.SLOT_Z[1]),
    ]
    cuts += _rear_holes() + _bottom_cuts(key_w) + _insert_holes()
    return shell - cuts
