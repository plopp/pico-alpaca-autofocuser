"""The focuser carrier board: every part and every connection.

Single source of truth for the schematic and board generators (pure Python, so it can be
imported by both system Python and KiCad's Python). Spec:
docs/superpowers/specs/2026-11-20-focuser-pcb-design.md
"""
from collections import namedtuple

# lcsc: LCSC/JLCPCB part number. mpn: manufacturer part number for parts JLCPCB has to buy in
# (global sourcing) when there is no LCSC stock.
Part = namedtuple('Part', 'ref symbol footprint value lcsc assembled mpn')
Part.__new__.__defaults__ = ('',)

CONFIRM = 'CONFIRM'   # LCSC number still to be confirmed before ordering

_PARTS = [
    Part('J1', 'Connector:Barrel_Jack_Switch', 'Focuser:BarrelJack_XunPu_DC-005-A200',
         'DC-005 5.5x2.1mm 12V', 'C720557', True),
    Part('F1', 'Device:Polyfuse', 'Fuse:Fuse_1812_4532Metric', '2A hold', 'C2982282', True),
    Part('D1', 'Device:D_Schottky', 'Diode_SMD:D_SMA', 'SS34', 'C8678', True),
    Part('D2', 'Device:D_Schottky', 'Diode_SMD:D_SMA', 'SS14', 'C2480', True),
    Part('U1', 'Converter_DCDC:R-78E5.0-0.5', 'Converter_DCDC:Converter_DCDC_RECOM_R-78E-0.5_THT',
         'R-78E5.0-0.5', 'C18212367', True, 'R-78E5.0-0.5'),   # JLCPCB Extended part
    Part('C1', 'Device:C_Polarized', 'Capacitor_SMD:CP_Elec_8x10.5', '100uF 50V', 'C72480', True),
    Part('C2', 'Device:C', 'Capacitor_SMD:C_0805_2012Metric', '100nF 50V', 'C49678', True),
    Part('C3', 'Device:C', 'Capacitor_SMD:C_1206_3216Metric', '10uF 50V', 'C89632', True),
    Part('C4', 'Device:C', 'Capacitor_SMD:C_1206_3216Metric', '10uF 50V', 'C89632', True),
    Part('C5', 'Device:C', 'Capacitor_SMD:C_0805_2012Metric', '100nF 50V', 'C49678', True),
    Part('R1', 'Device:R', 'Resistor_SMD:R_0603_1608Metric', '10k', 'C25804', True),
    Part('R2', 'Device:R', 'Resistor_SMD:R_0603_1608Metric', '4.7k', 'C23162', True),
    Part('R3', 'Device:R', 'Resistor_SMD:R_0603_1608Metric', '100R', 'C22775', True),
    Part('JP1', 'Jumper:SolderJumper_2_Open', 'Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm',
         'MS1', None, False),
    Part('JP2', 'Jumper:SolderJumper_2_Open', 'Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm',
         'MS2', None, False),
    Part('J2', 'Connector:Conn_01x04_Pin', 'Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical',
         'Motor', 'C144395', True),
    Part('J3', 'Connector_Audio:AudioJack4',
         'Connector_Audio:Jack_3.5mm_KoreanHropartsElec_PJ-320D-4A_Horizontal',
         'PJ-320D DS18B20', 'C95562', True),
    Part('J4', 'Connector:Conn_01x20_Socket', 'Connector_PinSocket_2.54mm:PinSocket_1x20_P2.54mm_Vertical',
         'Pico 1-20', 'C2905423', True),
    Part('J5', 'Connector:Conn_01x20_Socket', 'Connector_PinSocket_2.54mm:PinSocket_1x20_P2.54mm_Vertical',
         'Pico 40-21', 'C2905423', True),
    Part('J6', 'Connector:Conn_01x08_Socket', 'Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical',
         'TMC2209 logic', 'C2905417', True),
    Part('J7', 'Connector:Conn_01x08_Socket', 'Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical',
         'TMC2209 power', 'C2905417', True),
]   # no mounting holes: the board slides into slots in the case

PARTS = {p.ref: p for p in _PARTS}


def pico_pin(n):
    """Pico pin number (1-40) -> (socket ref, socket pin). Both sockets have pin 1 at the USB end."""
    if not 1 <= n <= 40:
        raise ValueError(n)
    return ('J4', str(n)) if n <= 20 else ('J5', str(41 - n))


# TMC2209 (BigTreeTech v1.3) sockets
TMC_LOGIC = {'EN': 1, 'MS1': 2, 'MS2': 3, 'RX': 4, 'TX': 5, 'CLK': 6, 'STEP': 7, 'DIR': 8}   # J6
TMC_POWER = {'VM': 1, 'GND1': 2, 'A2': 3, 'A1': 4, 'B1': 5, 'B2': 6, 'VIO': 7, 'GND2': 8}    # J7


def _j6(name):
    return ('J6', str(TMC_LOGIC[name]))


def _j7(name):
    return ('J7', str(TMC_POWER[name]))


NETS = {
    'VIN_RAW': [('J1', '1'), ('F1', '1')],
    'VIN_FUSED': [('F1', '2'), ('D1', '2')],
    '+12V': [('D1', '1'), ('U1', '1'), ('C1', '1'), ('C2', '1'), ('C3', '1'), _j7('VM')],
    '+5V': [('U1', '3'), ('C4', '1'), ('D2', '2')],
    'VSYS': [('D2', '1'), pico_pin(39)],
    '+3V3': [pico_pin(36), _j7('VIO'), ('C5', '1'), ('R1', '2'), ('R2', '2'), ('R3', '2'),
             ('JP1', '2'), ('JP2', '2')],
    'GND': [('J1', '2'), ('J1', '3'), ('J3', 'R2'), ('U1', '2'), ('C1', '2'), ('C2', '2'), ('C3', '2'), ('C4', '2'),
            ('C5', '2'), _j7('GND1'), _j7('GND2'), ('J3', 'S')]
           + [pico_pin(n) for n in (3, 8, 13, 18, 23, 28, 33, 38)],
    'STEP': [pico_pin(21), _j6('STEP')],
    'DIR': [pico_pin(26), _j6('DIR')],
    'EN': [pico_pin(27), _j6('EN'), ('R1', '1')],
    'MS1': [_j6('MS1'), ('JP1', '1')],
    'MS2': [_j6('MS2'), ('JP2', '1')],
    'TEMP_DQ': [pico_pin(29), ('R2', '1'), ('J3', 'T')],
    'TEMP_VDD': [('R3', '1'), ('J3', 'R1')],
    'MOT_A1': [_j7('A1'), ('J2', '1')],
    'MOT_A2': [_j7('A2'), ('J2', '2')],
    'MOT_B1': [_j7('B1'), ('J2', '3')],
    'MOT_B2': [_j7('B2'), ('J2', '4')],
}

# Nets that carry motor or supply current: 1.0 mm tracks
POWER_NETS = ('VIN_RAW', 'VIN_FUSED', '+12V', 'GND', 'MOT_A1', 'MOT_A2', 'MOT_B1', 'MOT_B2')
