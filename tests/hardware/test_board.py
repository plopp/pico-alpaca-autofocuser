import json
import subprocess
import sys

import pytest

import design

PICO_Y_SPAN = None   # filled from the board: y-range of the Pico sockets' outline


@pytest.fixture(scope='module')
def board(kicad):
    subprocess.run([sys.executable, str(kicad.HARDWARE / 'gen_schematic.py')], check=True)
    kicad.kipython(kicad.HARDWARE / 'gen_board.py')
    out = kicad.kipython(kicad.HARDWARE / 'board_report.py', kicad.PCB)
    return json.loads(out.stdout)


def fp(board, ref):
    return board['footprints'][ref]


def test_outline_80x50(board):
    x0, y0, x1, y1 = board['outline']
    assert abs((x1 - x0) - 80.0) < 0.01
    assert abs((y1 - y0) - 50.0) < 0.01


def test_all_parts_placed_on_board(board):
    x0, y0, x1, y1 = board['outline']
    for ref in design.PARTS:
        assert ref in board['footprints'], ref
        cx0, cy0, cx1, cy1 = fp(board, ref)['courtyard']
        assert cx0 >= x0 - 0.01 and cy0 >= y0 - 0.01, ref
        assert cx1 <= x1 + 0.01 and cy1 <= y1 + 0.01, ref


def test_no_courtyard_overlaps(board):
    refs = sorted(board['footprints'])
    for i, a in enumerate(refs):
        ax0, ay0, ax1, ay1 = fp(board, a)['courtyard']
        for b in refs[i + 1:]:
            bx0, by0, bx1, by1 = fp(board, b)['courtyard']
            overlap = ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1
            assert not overlap, (a, b)


def test_usb_and_jack_access_clear(board):
    x0 = board['outline'][0]
    pico = board['pico_outline']            # x0, y0, x1, y1 of the Pico silhouette
    assert pico[0] - x0 < 1.0               # USB end at the left edge
    assert fp(board, 'J1')['courtyard'][0] - x0 < 1.0      # jack opening at the left edge
    for ref, data in board['footprints'].items():
        if ref in ('J4', 'J5'):
            continue
        cx0, cy0, cx1, cy1 = data['courtyard']
        in_strip = cx0 < x0 + 12 and cy0 < pico[3] and cy1 > pico[1]
        assert not in_strip, ref


def test_right_edge_connectors(board):
    x1 = board['outline'][2]
    for ref in ('J2', 'J3'):
        assert x1 - fp(board, ref)['courtyard'][2] < 3.0, ref


def test_jack_openings_face_out(board):
    assert board['footprints']['J1']['rotation'] % 360 == 0      # opening faces -x
    assert board['footprints']['J3']['rotation'] % 360 == 90     # opening faces +x


def test_barrel_jack_centre_is_positive(board):
    assert fp(board, 'J1')['pads']['1'] == 'VIN_RAW'


def test_board_nets_match_design(board):
    for net, members in design.NETS.items():
        for ref, pin in members:
            assert fp(board, ref)['pads'].get(pin) == net, (ref, pin, net)


def _text_near(board, needle, x, y, dist):
    for t in board['texts']:
        if needle in t['text'] and abs(t['x'] - x) <= dist and abs(t['y'] - y) <= dist:
            return True
    return False


def test_orientation_silkscreen(board):
    pico = board['pico_outline']
    assert _text_near(board, 'USB', pico[0], (pico[1] + pico[3]) / 2, 8)
    j6_pin1 = fp(board, 'J6')['pad_xy']['1']
    assert _text_near(board, 'EN', j6_pin1[0], j6_pin1[1], 8)
    j1 = fp(board, 'J1')['pad_xy']['1']
    assert _text_near(board, '12V', j1[0], j1[1], 10)


SLOT_KEEPOUT = 2.5   # mm along both long edges: the board slides into slots in the case


def test_no_mounting_holes():
    assert not any(ref.startswith('H') for ref in design.PARTS)


def test_slot_edges_clear(board):
    x0, y0, x1, y1 = board['outline']
    for ref, data in board['footprints'].items():
        cx0, cy0, cx1, cy1 = data['courtyard']
        assert cy0 >= y0 + SLOT_KEEPOUT - 0.01, ref
        assert cy1 <= y1 - SLOT_KEEPOUT + 0.01, ref
