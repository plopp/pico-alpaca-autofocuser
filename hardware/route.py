"""Autoroute the placed board with FreeRouting (headless), then import the result.

Run with KiCad's Python after gen_board.py:
    ~/.local/opt/kicad-10.0.7/squashfs-root/bin/python3.11 hardware/route.py
FreeRouting's anonymous usage analytics are disabled.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pcbnew  # noqa: E402

import kicad_env  # noqa: E402

MAX_PASSES = 30


def route():
    board = pcbnew.LoadBoard(str(kicad_env.PCB))
    dsn = kicad_env.KICAD_DIR / (kicad_env.PROJECT + '.dsn')
    ses = kicad_env.KICAD_DIR / (kicad_env.PROJECT + '.ses')
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError('DSN export failed')
    # Route with clearances 10 um wider than the DRC rules: FreeRouting rounds coordinates
    text = dsn.read_text()
    text = re.sub(r'\(clearance (\d+)', lambda m: '(clearance {}'.format(int(m.group(1)) + 10), text)
    dsn.write_text(text)
    env = dict(os.environ, FREEROUTING__USAGE_AND_DIAGNOSTIC_DATA__DISABLE_ANALYTICS='true')
    result = subprocess.run(
        ['java', '-Djava.awt.headless=true', '-jar', str(kicad_env.FREEROUTING_JAR),
         '-de', str(dsn), '-do', str(ses), '-mp', str(MAX_PASSES), '-da', '--gui.enabled=false'],
        env=env, capture_output=True, text=True, timeout=600)
    if result.returncode != 0 or not ses.exists():
        raise RuntimeError('FreeRouting failed:\n' + result.stdout[-2000:] + result.stderr[-2000:])
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise RuntimeError('SES import failed')
    # The SES import can shrink via copper below the drill + ring; restore a 0.2 mm ring
    for via in board.GetTracks():
        if via.GetClass() == 'PCB_VIA':
            wanted = via.GetDrill() + pcbnew.FromMM(0.4)
            if via.GetWidth(pcbnew.F_Cu) < wanted:
                via.SetFrontWidth(wanted)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(str(kicad_env.PCB))
    ses.unlink()
    return kicad_env.PCB


if __name__ == '__main__':
    print(route())
