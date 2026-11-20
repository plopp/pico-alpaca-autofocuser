"""Dump a .kicad_pcb as JSON for the tests (run with KiCad's Python).

    python3.11 hardware/board_report.py hardware/kicad/focuser.kicad_pcb
"""
import json
import sys

import pcbnew

mm = pcbnew.ToMM


def bbox(box):
    return [round(mm(box.GetX()), 3), round(mm(box.GetY()), 3),
            round(mm(box.GetRight()), 3), round(mm(box.GetBottom()), 3)]


def report(path):
    board = pcbnew.LoadBoard(path)
    edge = None
    pico = None
    texts = []
    for item in board.GetDrawings():
        layer = item.GetLayer()
        if layer == pcbnew.Edge_Cuts:
            b = item.GetBoundingBox()
            b.Inflate(-item.GetWidth() // 2)        # outline geometry, not the drawn line
            if edge is None:
                edge = b
            else:
                edge.Merge(b)
        elif layer == pcbnew.User_1 and item.GetClass() == 'PCB_SHAPE' and pico is None:
            pico = bbox(item.GetBoundingBox())
        elif layer == pcbnew.F_SilkS and item.GetClass() == 'PCB_TEXT':
            pos = item.GetPosition()
            texts.append({'text': item.GetText(), 'x': mm(pos.x), 'y': mm(pos.y)})
    footprints = {}
    for fp in board.GetFootprints():
        for field in fp.GetFields():                 # visible footprint fields on silkscreen
            if field.IsVisible() and field.GetLayer() == pcbnew.F_SilkS:
                pos = field.GetPosition()
                texts.append({'text': field.GetText(), 'x': mm(pos.x), 'y': mm(pos.y)})
        court = fp.GetCourtyard(pcbnew.F_CrtYd)
        box = court.BBox() if court.OutlineCount() else fp.GetBoundingBox(False)
        footprints[fp.GetReference()] = {
            'rotation': round(fp.GetOrientationDegrees(), 1),
            'courtyard': bbox(box),
            'pads': {p.GetNumber(): p.GetNetname() for p in fp.Pads() if p.GetNumber()},
            'pad_xy': {p.GetNumber(): [mm(p.GetPosition().x), mm(p.GetPosition().y)]
                       for p in fp.Pads() if p.GetNumber()},
        }
    tracks = [{'net': t.GetNetname(), 'width': mm(t.GetWidth())}
              for t in board.GetTracks() if t.GetClass() == 'PCB_TRACK']
    return {'outline': bbox(edge), 'pico_outline': pico, 'texts': texts,
            'footprints': footprints, 'tracks': tracks}


if __name__ == '__main__':
    print(json.dumps(report(sys.argv[1])))
