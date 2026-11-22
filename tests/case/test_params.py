"""Case parameters (pure Python). The geometry tests need build123d, which lives in .venv:
    .venv/bin/python -m pytest tests/case -q
"""
import json
import sys
from pathlib import Path

import pytest

from case import params as p

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'hardware'))


@pytest.fixture(scope='module')
def board():
    """JSON report of the committed board (needs KiCad's Python)."""
    import kicad_env
    if not kicad_env.KICAD_PYTHON.exists():
        pytest.skip('KiCad not installed (run hardware/setup_tools.sh)')
    return json.loads(kicad_env.kipython(kicad_env.HARDWARE / 'board_report.py',
                                         kicad_env.PCB).stdout)


def test_rear_wall_is_2mm():
    assert p.REAR_WALL == 2.0


def test_motor_fits_between_walls():
    inner_y0, inner_y1 = p.INNER_Y
    assert (inner_y0, inner_y1) == (1.8, 48.2)
    assert inner_y1 - inner_y0 >= p.MOTOR_SQUARE + 2 * p.CLEAR
    assert p.MOTOR_FACE_X - p.MOTOR_REAR_X == 48.0


def test_nut_pause_height():
    assert p.PAUSE_HEIGHT == 7.6
    assert abs(p.NUT_TOP_Z - (p.BOTTOM_Z + 7.6)) < 1e-9
    assert p.NUT_TOP_Z < p.FLOOR_Z - 0.7          # printed cover over the nut


def test_floor_clears_board_pins():
    """The board slides in from the front over the whole floor, pins (~3.5 mm) underneath."""
    assert p.FLOOR_Z <= -p.BOARD_T - 3.5


def test_outer_box():
    assert p.OUTER == (-2.0, -2.7, p.BOTTOM_Z, p.PLATE_X1, 52.7, p.LID_TOP_Z)
    assert p.KEY_W == 6.0


def test_positions_match_committed_board(board):
    fp = board['footprints']
    assert board['outline'] == [0.0, 0.0, 80.0, 50.0]
    assert abs(fp['J1']['pad_xy']['1'][1] - p.J1_Y) < 0.05
    assert abs(fp['J1']['courtyard'][0] - (-2.39)) < 0.03        # body front at x = -2
    assert abs(fp['J3']['courtyard'][0] - (-2.5)) < 0.05         # nose end at x = -2
    j3_y = (fp['J3']['courtyard'][1] + fp['J3']['courtyard'][3]) / 2
    assert abs(j3_y - p.J3_Y) < 0.05
    pico = board['pico_outline']
    assert abs((pico[1] + pico[3]) / 2 - p.USB_Y) < 0.05
    assert abs(fp['J2']['pad_xy']['1'][0] - 69.0) < 0.05         # cable gap ahead of J2
