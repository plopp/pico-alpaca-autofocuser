"""JLCPCB fabrication outputs in hardware/fab/ (run after route.py).

    focuser-gerbers.zip   Gerbers + Excellon drill (slots as routed slots)
    focuser-bom-jlc.csv   Comment, Designator, Footprint, LCSC Part #, Manufacturer Part
    focuser-cpl-jlc.csv   Designator, Mid X, Mid Y, Layer, Rotation (mm, origin bottom-left, y up)
    focuser-schematic.pdf, render-top.png, render-iso.png
"""
import csv
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import design  # noqa: E402
import kicad_env  # noqa: E402

LAYERS = 'F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'


def cli(*args):
    env = dict(os.environ, KICAD10_3DMODEL_DIR=str(kicad_env.KICAD_ROOT / 'share/kicad/3dmodels'))
    subprocess.run([str(kicad_env.KICAD_CLI), *map(str, args)], check=True,
                   capture_output=True, text=True, env=env)


def gerbers(out):
    with tempfile.TemporaryDirectory() as tmp:
        cli('pcb', 'export', 'gerbers', '--layers', LAYERS, '-o', tmp + '/', kicad_env.PCB)
        cli('pcb', 'export', 'drill', '--format', 'excellon', '--excellon-units', 'mm',
            '--excellon-oval-format', 'route', '--excellon-separate-th', '-o', tmp + '/',
            kicad_env.PCB)
        with zipfile.ZipFile(out / 'focuser-gerbers.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for f in sorted(Path(tmp).iterdir()):
                z.write(f, f.name)


def bom(out):
    groups = {}
    for p in design.PARTS.values():
        if not p.assembled:
            continue
        key = (p.value, p.footprint.split(':')[1], p.lcsc or '', p.mpn or '')
        groups.setdefault(key, []).append(p.ref)
    with open(out / 'focuser-bom-jlc.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #', 'Manufacturer Part'])
        for (value, footprint, lcsc, mpn), refs in sorted(groups.items(), key=lambda g: g[1][0]):
            w.writerow([value, ','.join(sorted(refs)), footprint, lcsc, mpn])


def cpl(out):
    """Part centres (courtyard centre), not footprint origins: JLC places by centre, and the
    origins of THT parts sit on pin 1 (up to 24 mm off). mm from the bottom-left corner, y up."""
    import pcbnew
    board = pcbnew.LoadBoard(str(kicad_env.PCB))
    origin = board.GetDesignSettings().GetAuxOrigin()
    assembled = {p.ref for p in design.PARTS.values() if p.assembled}
    rows = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in assembled:
            continue
        court = fp.GetCourtyard(pcbnew.F_CrtYd)
        box = court.BBox() if court.OutlineCount() else fp.GetBoundingBox(False)
        centre = box.GetCenter()
        x = pcbnew.ToMM(centre.x - origin.x)
        y = pcbnew.ToMM(origin.y - centre.y)
        side = 'Bottom' if fp.IsFlipped() else 'Top'
        rows.append([ref, '{:.3f}'.format(x), '{:.3f}'.format(y), side,
                     '{:.1f}'.format(fp.GetOrientationDegrees() % 360)])
    with open(out / 'focuser-cpl-jlc.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        w.writerows(sorted(rows))


def docs(out):
    cli('sch', 'export', 'pdf', '-o', out / 'focuser-schematic.pdf', kicad_env.SCH)
    cli('pcb', 'render', '--side', 'top', '--width', '1600', '--height', '1000',
        '-o', out / 'render-top.png', kicad_env.PCB)
    cli('pcb', 'render', '--rotate', '-50,0,25', '--perspective', '--width', '1600',
        '--height', '1000', '-o', out / 'render-iso.png', kicad_env.PCB)


def build(out=None, renders=True):
    out = Path(out) if out else kicad_env.FAB_DIR
    out.mkdir(parents=True, exist_ok=True)
    gerbers(out)
    bom(out)
    cpl(out)
    if renders:
        docs(out)
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    print(build(args[0] if args else None, renders='--no-renders' not in sys.argv))
