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


def write_project():
    """Write focuser.kicad_pro: JLCPCB 2-layer rules and net classes (power nets 1.0 mm)."""
    import json
    import design
    rules = {'min_clearance': 0.127, 'min_track_width': 0.127, 'min_via_diameter': 0.5,
             'min_through_hole_diameter': 0.3, 'min_hole_to_hole': 0.25,
             'min_copper_edge_clearance': 0.3, 'min_via_annular_width': 0.13,
             'min_resolved_spokes': 1,
             'min_text_height': 0.8, 'min_text_thickness': 0.12, 'min_silk_clearance': 0.0,
             'allow_blind_buried_vias': False, 'allow_microvias': False}

    def netclass(name, track, clearance, via, drill, priority):
        return {'name': name, 'track_width': track, 'clearance': clearance,
                'via_diameter': via, 'via_drill': drill, 'microvia_diameter': 0.3,
                'microvia_drill': 0.1, 'diff_pair_width': 0.2, 'diff_pair_gap': 0.25,
                'diff_pair_via_gap': 0.25, 'wire_width': 6, 'bus_width': 12, 'line_style': 0,
                'pcb_color': 'rgba(0, 0, 0, 0.000)', 'schematic_color': 'rgba(0, 0, 0, 0.000)',
                'priority': priority}

    project = {
        'meta': {'filename': PROJECT + '.kicad_pro', 'version': 3},
        'board': {'design_settings': {'rules': rules}},
        'net_settings': {
            'meta': {'version': 4},
            'classes': [netclass('Default', 0.25, 0.2, 0.6, 0.3, 2147483647),
                        netclass('Power', 1.0, 0.25, 0.8, 0.4, 0)],
            'netclass_assignments': None,
            'netclass_patterns': [{'netclass': 'Power', 'pattern': n} for n in design.POWER_NETS],
            'net_colors': None,
        },
    }
    KICAD_DIR.mkdir(parents=True, exist_ok=True)
    (KICAD_DIR / (PROJECT + '.kicad_pro')).write_text(json.dumps(project, indent=2) + '\n')
