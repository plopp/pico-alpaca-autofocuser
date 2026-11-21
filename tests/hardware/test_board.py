import design


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


def test_motor_connector_at_right_edge(board):
    x1 = board['outline'][2]
    assert x1 - fp(board, 'J2')['courtyard'][2] < 3.0


def test_rear_edge_has_usb_power_and_temperature(board):
    """USB, 12 V and the DS18B20 jack all come out of the same (rear) short edge."""
    x0 = board['outline'][0]
    for ref in ('J1', 'J3'):
        assert fp(board, ref)['courtyard'][0] - x0 < 1.0, ref


def test_jack_openings_face_out(board):
    assert board['footprints']['J1']['rotation'] % 360 == 0      # opening faces -x
    assert board['footprints']['J3']['rotation'] % 360 == 0      # PJ-320D: opening faces -x


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


def test_no_part_numbers_on_silkscreen(board):
    import re
    for t in board['texts']:
        assert not re.fullmatch(r'C\d{4,}', t['text']), t      # LCSC numbers, not designators
        assert 'CONFIRM' not in t['text'], t


def test_barrel_jack_matches_dc005_datasheet(board):
    """XUNPU DC-005 drawing: blade pins in 3 x 0.8 mm slots, 6.2 mm and 4.7 mm apart."""
    pads = fp(board, 'J1')['pad_xy']
    drills = fp(board, 'J1')['pad_drill']
    (x1, y1), (x2, y2), (x3, y3) = pads['1'], pads['2'], pads['3']
    assert abs(abs(x1 - x2) - 6.2) < 0.01 and abs(y1 - y2) < 0.01
    assert abs(abs(y3 - y1) - 4.7) < 0.01 and abs(abs(x1 - x3) - 2.7) < 0.01
    for pin in ('1', '2', '3'):
        dx, dy = drills[pin]
        assert min(dx, dy) >= 0.8 and max(dx, dy) >= 3.0, (pin, dx, dy)     # slot, not round


def test_tmc2209_socket_handedness_matches_module(board):
    """BTT TMC2209 v1.3 seen from above (user's photo): power row VM..GND on top, logic row
    EN..DIR below, EN and VM at the left end. Rotations keep the sign of
    (DIR - EN) x (VM - EN); a mirror flips it. The module's sign is negative (y down)."""
    en = fp(board, 'J6')['pad_xy']['1']
    dir_ = fp(board, 'J6')['pad_xy']['8']
    vm = fp(board, 'J7')['pad_xy']['1']
    cross = (dir_[0] - en[0]) * (vm[1] - en[1]) - (dir_[1] - en[1]) * (vm[0] - en[0])
    assert abs(abs(cross) - 17.78 * 12.7) < 0.1          # rows 12.7 mm apart, pins aligned
    assert cross < 0, 'TMC2209 sockets are mirrored: the module would plug in reversed'


def _antenna_box(board):
    """Pico 2 W datasheet 2.2.1, figure 7: 14 mm wide x 9 mm deep at the end opposite USB,
    centred between the pin rows."""
    x0, y0, x1, y1 = board['pico_outline']
    mid = (y0 + y1) / 2
    return (x1 - 9.0, mid - 7.0, x1, mid + 7.0)


def test_no_copper_pour_or_vias_under_antenna(board):
    ax0, ay0, ax1, ay1 = _antenna_box(board)
    keepouts = [k for k in board['rule_areas'] if k['no_fill'] and k['no_vias']
                and {'F.Cu', 'B.Cu'} <= set(k['layers'])]
    assert any(k['bbox'][0] <= ax0 and k['bbox'][1] <= ay0 and k['bbox'][2] >= ax1
               and k['bbox'][3] >= ay1 for k in keepouts), 'no keep-out under the antenna'
    for v in board['vias']:
        assert not (ax0 <= v[0] <= ax1 and ay0 <= v[1] <= ay1), v


def test_driver_clear_of_antenna(board):
    pico_end = board['pico_outline'][2]
    tmc_left = min(fp(board, 'J6')['courtyard'][0], fp(board, 'J7')['courtyard'][0])
    assert tmc_left - pico_end >= 10.0
