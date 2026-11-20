import design
from design import NETS, PARTS, pico_pin


def net_of(ref, pin):
    for name, members in NETS.items():
        if (ref, pin) in members:
            return name
    return None


def test_spec_signal_nets():
    assert net_of(*pico_pin(21)) == 'STEP' and net_of('J6', '7') == 'STEP'
    assert net_of(*pico_pin(26)) == 'DIR' and net_of('J6', '8') == 'DIR'
    assert net_of(*pico_pin(27)) == 'EN' and net_of('J6', '1') == 'EN'
    assert net_of('R1', '1') == 'EN' or net_of('R1', '2') == 'EN'
    assert net_of(*pico_pin(29)) == 'TEMP_DQ' and net_of('J3', 'T') == 'TEMP_DQ'
    assert net_of(*pico_pin(39)) == 'VSYS'
    assert net_of(*pico_pin(36)) == '+3V3' and net_of('J7', '7') == '+3V3'
    assert net_of('J7', '1') == '+12V'


def test_pico_socket_mapping():
    assert pico_pin(1) == ('J4', '1')
    assert pico_pin(20) == ('J4', '20')
    assert pico_pin(40) == ('J5', '1')
    assert pico_pin(21) == ('J5', '20')


def test_pico_gnd_pins():
    for n in (3, 8, 13, 18, 23, 28, 33, 38):
        assert net_of(*pico_pin(n)) == 'GND'


def test_motor_pairs():
    assert net_of('J2', '1') == net_of('J7', '4') == 'MOT_A1'
    assert net_of('J2', '2') == net_of('J7', '3') == 'MOT_A2'
    assert net_of('J2', '3') == net_of('J7', '5') == 'MOT_B1'
    assert net_of('J2', '4') == net_of('J7', '6') == 'MOT_B2'


def test_unconnected_tmc_pins():
    for pin in ('4', '5', '6'):
        assert net_of('J6', pin) is None


def test_power_path():
    assert net_of('J1', '1') == 'VIN_RAW'          # barrel centre (positive)
    assert net_of('J1', '2') == 'GND'
    assert net_of('D1', '2') == 'VIN_FUSED'        # anode
    assert net_of('D1', '1') == '+12V'             # cathode
    assert net_of('U1', '1') == '+12V' and net_of('U1', '3') == '+5V'
    assert net_of('D2', '2') == '+5V' and net_of('D2', '1') == 'VSYS'
    assert net_of('C1', '1') == '+12V' and net_of('C1', '2') == 'GND'
    assert {net_of('R3', '1'), net_of('R3', '2')} == {'+3V3', 'TEMP_VDD'}
    # 4-pole jack, 3-pole plug: the plug's sleeve spans R2 and S, both grounded
    assert net_of('J3', 'R1') == 'TEMP_VDD'
    assert net_of('J3', 'R2') == 'GND' and net_of('J3', 'S') == 'GND'
    assert net_of('J1', '3') == 'GND'                 # DC-005 switch contact


def test_no_pin_in_two_nets():
    seen = {}
    for name, members in NETS.items():
        for member in members:
            assert member not in seen, '{} in {} and {}'.format(member, seen.get(member), name)
            seen[member] = name


def test_every_net_member_is_a_part():
    for members in NETS.values():
        for ref, _ in members:
            assert ref in PARTS


def test_assembled_parts_have_lcsc_or_mpn():
    for part in PARTS.values():
        if part.assembled:
            assert part.lcsc or part.mpn, part.ref          # MPN only = JLC global sourcing
            assert part.lcsc != design.CONFIRM, part.ref


def test_barrel_jack_is_5_5_x_2_1():
    j1 = PARTS['J1']
    assert j1.lcsc == 'C720557' and '5.5x2.1' in j1.value      # XUNPU DC-005-A200: 2.0 mm pin
