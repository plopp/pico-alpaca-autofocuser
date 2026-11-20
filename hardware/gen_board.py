"""Generate the placed (unrouted) board: hardware/kicad/focuser.kicad_pcb + focuser.dsn.

Run with KiCad's Python:  ~/.local/opt/kicad-10.0.7/squashfs-root/bin/python3.11 hardware/gen_board.py
Coordinates in mm, origin top-left, x along the 80 mm side (spec: 2026-11-20-focuser-pcb-design.md).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pcbnew  # noqa: E402

import design  # noqa: E402
import kicad_env  # noqa: E402
from gen_schematic import uid  # noqa: E402

W, H = 80.0, 50.0
SLOT_KEEPOUT = 2.5      # no parts within this of the long edges (board slides into case slots)
PITCH = 2.54

# Pico: socket pin 1 sits 2.72 mm from the USB connector face (Module:RaspberryPi_Pico_Common_THT)
PICO_X = 2.72
PICO_TOP_ROW_Y = 9.0                      # J5: Pico pins 40..21
PICO_BOTTOM_ROW_Y = PICO_TOP_ROW_Y + 17.78  # J4: Pico pins 1..20
PICO_OUTLINE = (0.0, PICO_TOP_ROW_Y - 1.61, PICO_X + 19 * PITCH + 1.13, PICO_BOTTOM_ROW_Y + 1.61)

TMC_LOGIC_X, TMC_POWER_X, TMC_PIN1_Y = 56.0, 68.7, 27.0   # pin 1 at the bottom, pins go up

# ref: (x, y, rotation in degrees)
PLACEMENT = {
    'J5': (PICO_X, PICO_TOP_ROW_Y, 90),
    'J4': (PICO_X, PICO_BOTTOM_ROW_Y, 90),
    'J6': (TMC_LOGIC_X, TMC_PIN1_Y, 180),
    'J7': (TMC_POWER_X, TMC_PIN1_Y, 180),
    'J1': (14.04, 33.5, 0),            # opening faces -x (left edge)
    'J2': (76.0, 24.0, 90),            # motor, right edge, pins going up
    'J3': (73.41, 36.0, 90),           # 3.5 mm jack, opening faces +x (right edge)
    'F1': (21.0, 31.0, 0),
    'D1': (28.0, 31.0, 0),
    'U1': (21.0, 41.0, 0),
    'C3': (33.5, 37.5, 0),
    'C4': (33.5, 41.5, 0),
    'D2': (40.0, 41.5, 0),
    'C1': (62.0, 36.0, 180),           # + pad nearest VM
    'C2': (63.0, 30.2, 0),
    'C5': (64.0, 12.0, 90),
    'R1': (60.0, 26.0, 0),
    'JP1': (46.0, 31.5, 0),
    'JP2': (46.0, 35.0, 0),
    'R2': (58.0, 44.0, 0),
    'R3': (62.0, 44.0, 0),
}

# Descriptive silkscreen replaces these designators (they would overlap the labels)
HIDDEN_REFS = ('J2', 'J4', 'J5', 'J6', 'J7')

SILK = [  # text, x, y, size, rotation
    ('USB', 3.5, (PICO_OUTLINE[1] + PICO_OUTLINE[3]) / 2, 1.2, 90),
    ('Pico 2 W', 27.0, 17.9, 1.5, 0),
    ('TMC2209', 62.35, 18.0, 1.2, 90),
    ('EN', TMC_LOGIC_X, TMC_PIN1_Y + 3.0, 1.0, 0),
    ('VM', TMC_POWER_X + 2.9, TMC_PIN1_Y, 0.8, 0),
    ('12V (+) centre', 8.5, 42.5, 1.0, 0),
    ('A1', 72.4, 24.0, 0.8, 0), ('A2', 72.4, 21.5, 0.8, 0),
    ('B1', 72.4, 19.0, 0.8, 0), ('B2', 72.4, 16.5, 0.8, 0),
    ('MOTOR', 76.0, 11.0, 1.0, 0),
    ('T=DATA R=3V3 S=GND', 71.5, 45.0, 0.8, 0),
    ('MS1/MS2 open = 1/8', 46.0, 37.8, 0.8, 0),
    ('Pico Alpaca Focuser v1.0', 30.0, 48.0, 1.2, 0),
]


def mmv(x, y):
    return pcbnew.VECTOR2I_MM(x, y)


def add_rect(board, layer, x0, y0, x1, y1, width=0.15):
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_RECT)
    shape.SetStart(mmv(x0, y0))
    shape.SetEnd(mmv(x1, y1))
    shape.SetLayer(layer)
    shape.SetWidth(pcbnew.FromMM(width))
    board.Add(shape)


def add_text(board, text, x, y, size, rotation):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(mmv(x, y))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
    t.SetTextThickness(pcbnew.FromMM(max(0.12, size * 0.15)))
    t.SetTextAngleDegrees(rotation)
    board.Add(t)


def add_gnd_zone(board, layer, net):
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(net)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
        outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    zone.SetLocalClearance(pcbnew.FromMM(0.3))
    zone.SetMinThickness(pcbnew.FromMM(0.25))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    board.Add(zone)


def build():
    kicad_env.write_project()
    board = pcbnew.NewBoard(str(kicad_env.PCB))
    board.GetDesignSettings().SetCopperLayerCount(2)

    nets = {}
    for name in design.NETS:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net
    net_of = {member: name for name, members in design.NETS.items() for member in members}

    for ref, part in design.PARTS.items():
        lib, name = part.footprint.split(':')
        fp = pcbnew.FootprintLoad(str(kicad_env.FOOTPRINTS / (lib + '.pretty')), name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(part.value)
        if ref in HIDDEN_REFS:
            fp.Reference().SetVisible(False)
        fp.SetPath(pcbnew.KIID_PATH('/' + uid(ref)))
        fp.SetSheetname('Root')
        fp.SetSheetfile(kicad_env.PROJECT + '.kicad_sch')
        x, y, rot = PLACEMENT[ref]
        fp.SetPosition(mmv(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            net = net_of.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(nets[net])
        board.Add(fp)

    add_rect(board, pcbnew.Edge_Cuts, 0, 0, W, H, width=0.1)
    add_rect(board, pcbnew.User_1, *PICO_OUTLINE)                     # Pico silhouette (tests)
    add_rect(board, pcbnew.F_SilkS, PICO_OUTLINE[0] + 1.11, PICO_OUTLINE[1],
             PICO_OUTLINE[2], PICO_OUTLINE[3])                        # Pico PCB outline
    add_rect(board, pcbnew.F_SilkS, TMC_LOGIC_X - 1.27 - 0.2, TMC_PIN1_Y - 7 * PITCH - 1.27 - 0.2,
             TMC_POWER_X + 1.27 + 0.2, TMC_PIN1_Y + 1.27 + 0.2)       # TMC2209 module outline
    for text in SILK:
        add_text(board, *text)

    add_gnd_zone(board, pcbnew.F_Cu, nets['GND'])
    add_gnd_zone(board, pcbnew.B_Cu, nets['GND'])
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    board.Save(str(kicad_env.PCB))
    pcbnew.ExportSpecctraDSN(board, str(kicad_env.KICAD_DIR / (kicad_env.PROJECT + '.dsn')))
    return kicad_env.PCB


if __name__ == '__main__':
    print(build())
