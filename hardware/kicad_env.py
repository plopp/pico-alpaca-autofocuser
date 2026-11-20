"""Where the KiCad 10 install and FreeRouting live, and helpers to run them."""
import os
import subprocess
from pathlib import Path

HARDWARE = Path(__file__).resolve().parent
KICAD_DIR = HARDWARE / 'kicad'
FAB_DIR = HARDWARE / 'fab'
PROJECT = 'focuser'
SCH = KICAD_DIR / (PROJECT + '.kicad_sch')
PCB = KICAD_DIR / (PROJECT + '.kicad_pcb')

KICAD_ROOT = Path(os.environ.get(
    'KICAD_ROOT', Path.home() / '.local/opt/kicad-10.0.7/squashfs-root'))
KICAD_CLI = KICAD_ROOT / 'bin' / 'kicad-cli'
KICAD_PYTHON = KICAD_ROOT / 'bin' / 'python3.11'
SYMBOLS = KICAD_ROOT / 'share/kicad/symbols'
FOOTPRINTS = KICAD_ROOT / 'share/kicad/footprints'
FREEROUTING_JAR = Path(os.environ.get(
    'FREEROUTING_JAR', Path.home() / '.local/opt/freerouting/freerouting-2.1.0.jar'))


def cli(*args, check=True):
    """Run kicad-cli with the given arguments."""
    return subprocess.run([str(KICAD_CLI), *map(str, args)], check=check,
                          capture_output=True, text=True)


def kipython(script, *args, check=True):
    """Run a script with KiCad's bundled Python (which has pcbnew)."""
    return subprocess.run([str(KICAD_PYTHON), str(script), *map(str, args)], check=check,
                          capture_output=True, text=True)
