"""Front plate, lid and key, as assembled (board frame)."""
import math

import pytest

from case import params as p
from case.parts import body, board_envelope, box, front_plate, key, lid, motor_envelope

EPS = 1e-3
MID_PLATE = p.MOTOR_FACE_X + p.PLATE_T / 2


def overlap(a, b):
    return (a & b).volume


@pytest.fixture(scope='module')
def parts():
    return {'body': body(), 'plate': front_plate(), 'lid': lid(), 'key': key()}


def test_parts_are_valid(parts):
    assert all(part.is_valid for part in parts.values())


def test_plate_motor_holes(parts):
    plate = parts['plate']
    half = p.MOTOR_HOLE_PITCH / 2
    for dy in (-half, half):
        for dz in (-half, half):
            assert not plate.is_inside((MID_PLATE, p.MOTOR_Y + dy, p.SHAFT_Z + dz))
    boss_r = (p.MOTOR_BOSS_D + 1.0) / 2
    assert not plate.is_inside((MID_PLATE, p.MOTOR_Y, p.SHAFT_Z + boss_r - 0.1))
    assert plate.is_inside((MID_PLATE, p.MOTOR_Y, p.SHAFT_Z + boss_r + 0.5))


def test_plate_screws_line_up_with_inserts(parts):
    for y, z in p.PLATE_SCREWS:
        assert not parts['plate'].is_inside((MID_PLATE, y, z)), (y, z)
        assert not parts['body'].is_inside((p.MOTOR_FACE_X - 1, y, z)), (y, z)


def test_lid_screws_line_up_with_inserts(parts):
    for x, y in p.LID_SCREWS:
        assert not parts['lid'].is_inside((x, y, p.LID_UNDER_Z + 1)), (x, y)
        assert not parts['body'].is_inside((x, y, p.LID_UNDER_Z - 1)), (x, y)


@pytest.mark.parametrize('length', [34, 48])
def test_plate_and_lid_clear_envelopes(parts, length):
    for name in ('plate', 'lid', 'key'):
        assert overlap(parts[name], board_envelope()) < EPS, name
        assert overlap(parts[name], motor_envelope(length)) < EPS, name
    for a, b in [('plate', 'body'), ('lid', 'body'), ('key', 'body'), ('lid', 'plate')]:
        assert overlap(parts[a], parts[b]) < EPS, (a, b)


def test_board_stop_independent_of_motor(parts):
    """The lid, not the motor, stops the board sliding forward (a 34 mm motor is far away)."""
    moved = box(1.0, 0, -p.BOARD_T, p.BOARD_L + 1.0, p.BOARD_W, 0)
    assert overlap(parts['lid'], moved) > 0.1


def test_pot_hole_and_vents_open(parts):
    above = p.LID_UNDER_Z + 1
    assert not parts['lid'].is_inside((p.POT_X, p.POT_Y, above))
    for x in p.VENT_XS:
        assert not parts['lid'].is_inside((x, sum(p.VENT_Y) / 2, above)), x
    assert parts['lid'].is_inside((40.0, 25.0, above))


def test_key_dimensions(parts):
    bb = parts['key'].bounding_box()
    assert math.isclose(bb.size.X, p.KEY_W, abs_tol=0.01)
    assert math.isclose(bb.size.Y, p.OUTER_Y[1] - p.OUTER_Y[0], abs_tol=0.01)
    assert math.isclose(bb.size.Z, p.KEY_H, abs_tol=0.01)
    assert math.isclose(bb.max.Z, p.BOTTOM_Z + p.GROOVE_D, abs_tol=0.01)   # 1 mm in the groove
    assert not parts['key'].is_inside((p.NUT_X, p.NUT_Y, p.BOTTOM_Z))      # screw passes
    gap = p.SCREW_HOLE_D / 2
    assert not parts['key'].is_inside((p.NUT_X, p.NUT_Y + gap - 0.1, p.BOTTOM_Z))
    assert math.isclose(key(6.5).bounding_box().size.X, 6.5, abs_tol=0.01)
