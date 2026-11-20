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
    assembled = {p.ref for p in design.PARTS.values() if p.assembled}
    with tempfile.TemporaryDirectory() as tmp:
        pos = Path(tmp) / 'pos.csv'
        cli('pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
            '--use-drill-file-origin', '-o', pos, kicad_env.PCB)
        with open(pos, newline='') as f:
            rows = list(csv.DictReader(f))
    with open(out / 'focuser-cpl-jlc.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in rows:
            if r['Ref'] in assembled:
                w.writerow([r['Ref'], r['PosX'], r['PosY'],
                            'Top' if r['Side'] == 'top' else 'Bottom', r['Rot']])


def docs(out):
    cli('sch', 'export', 'pdf', '-o', out / 'focuser-schematic.pdf', kicad_env.SCH)
    cli('pcb', 'render', '--side', 'top', '--width', '1600', '--height', '1000',
        '-o', out / 'render-top.png', kicad_env.PCB)
    cli('pcb', 'render', '--rotate', '-50,0,25', '--perspective', '--width', '1600',
        '--height', '1000', '-o', out / 'render-iso.png', kicad_env.PCB)


def build():
    out = kicad_env.FAB_DIR
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob('preview-*.png'):          # superseded by render-*.png
        old.unlink()
    gerbers(out)
    bom(out)
    cpl(out)
    docs(out)
    return out


if __name__ == '__main__':
    print(build())
