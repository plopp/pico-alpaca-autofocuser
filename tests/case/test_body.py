"""Body: checked with solid intersections and point containment (board frame)."""
import math

import pytest

pytest.importorskip('build123d')
from build123d import Box, Plane, Pos, RegularPolygon, Rot, extrude

from case import params as p
from case.parts import body, board_envelope, box, motor_envelope, to_world

EPS = 1e-3      # mm³: touching faces may leave a sliver of numerical volume


def overlap(a, b):
    return (a & b).volume


@pytest.fixture(scope='module')
def part():
    return body()


def test_body_is_valid(part):
    assert part.is_valid


def test_board_slides_in(part):
    board = box(0, 0, -p.BOARD_T, p.BOARD_L, p.BOARD_W, 0)
    assert overlap(part, board) < EPS
    wider = box(0, -0.25, -p.BOARD_T, p.BOARD_L, p.BOARD_W + 0.25, 0)
    assert overlap(part, wider) > 1.0               # the slots hold it in y


def test_board_slides_in_from_the_front(part):
    """Board, its parts and the pins underneath pass the whole length (motor not fitted yet)."""
    env = board_envelope()
    for d in (0.5, 10, 30, 54, 60):
        assert overlap(part, Pos(d, 0, 0) * env) < EPS, d


def test_parts_clear_board_envelope(part):
    assert overlap(part, board_envelope()) < EPS


@pytest.mark.parametrize('length', [34, 40, 48])
def test_motor_fits(part, length):
    assert overlap(part, motor_envelope(length)) < EPS


def test_rear_holes_open(part):
    for point in [(-1.0, p.USB_Y, p.USB_Z), (-1.0, p.J1_Y, 6.5), (-1.0, p.J3_Y, p.J3_Z)]:
        assert not part.is_inside(point), point
    assert part.is_inside((-1.0, p.USB_Y, p.USB_Z + 8))            # wall between the holes
    assert part.is_inside((-1.0, p.J3_Y, p.J3_Z + 6))


@pytest.mark.parametrize('z', [12.3, 13.3, 14.3])
def test_usb_hole_tolerates_height(part, z):
    """A micro-B plug shell (7 x 2.5) reaches the Pico even if it sits 1 mm off."""
    plug = box(-p.REAR_WALL - 1, p.USB_Y - 3.5, z - 1.25, 0.5, p.USB_Y + 3.5, z + 1.25)
    assert overlap(part, plug) < EPS


def test_screw_hole_is_blind(part):
    assert not part.is_inside((p.NUT_X, p.NUT_Y, p.BOTTOM_Z + 1.3))     # screw comes up
    for z in (p.NUT_TOP_Z + 0.1, (p.NUT_TOP_Z + p.FLOOR_Z) / 2, p.FLOOR_Z - 0.1):
        assert part.is_inside((p.NUT_X, p.NUT_Y, z)), z                # but stops at the nut


def key_bar(width):
    return box(p.NUT_X - width / 2, p.OUTER_Y[0], p.BOTTOM_Z,
               p.NUT_X + width / 2, p.OUTER_Y[1], p.BOTTOM_Z + p.GROOVE_D)


def test_key_fits_groove(part):
    assert overlap(part, key_bar(p.KEY_W + p.CLEAR - 0.01)) < EPS
    assert overlap(part, key_bar(p.KEY_W + p.CLEAR + 0.4)) > 1.0
    assert overlap(body(key_w=6.5), key_bar(6.5 + p.CLEAR - 0.01)) < EPS


def nut(af, rotation=0):
    hexagon = Plane.XY.offset(p.NUT_BOTTOM_Z) * Pos(p.NUT_X, p.NUT_Y) * Rot(0, 0, rotation) \
        * RegularPolygon(af / 2, 6, major_radius=False)
    return extrude(hexagon, amount=p.NUT_T)


def test_nut_pocket(part):
    assert overlap(part, nut(p.NUT_AF)) < EPS
    assert overlap(part, nut(p.NUT_AF + p.CLEAR + 0.4)) > 1.0      # not loose
    assert overlap(part, nut(p.NUT_AF, rotation=30)) > 1.0          # cannot turn
    above = Pos(0, 0, p.NUT_T + 0.05) * nut(p.NUT_AF)
    assert overlap(part, above) > 1.0                               # printed over


def test_antenna_end_plastic_only():
    """Pico antenna (x 43..53): no inserts or bosses near it."""
    for x, _ in p.LID_SCREWS:
        assert not 40 <= x <= 56
    for x0, x1 in p.BOSS_X:
        assert x1 < 40 or x0 > 56


def test_world_frame_is_not_mirrored(part):
    """Seen from behind, the USB is on the left of the 3.5 mm jack: world y = -board y."""
    world = to_world(part)
    bb = world.bounding_box()
    assert math.isclose(bb.min.Y, -(p.OUTER_Y[1] + p.BOSS_OUT), abs_tol=0.01)
    assert not world.is_inside((-1.0, -p.USB_Y, p.USB_Z))
    assert not world.is_inside((-1.0, -p.J3_Y, p.J3_Z))
    assert world.is_inside((-1.0, -p.J3_Y, p.USB_Z))


def test_corner_bosses_where_the_inserts_are(part):
    z = p.LID_UNDER_Z - 1
    for y in (p.OUTER_Y[0] - 1, p.OUTER_Y[1] + 1):
        for x0, x1 in p.BOSS_X:
            assert part.is_inside(((x0 + x1) / 2, y, z)), (x0, y)
        assert not part.is_inside((60.0, y, z))
        assert not part.is_inside((p.BOSS_X[1][0] - 1, y, z))
    assert part.bounding_box().min.X > -p.REAR_WALL - 0.01
