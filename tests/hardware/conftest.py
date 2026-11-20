"""PCB tests. Design-data tests always run; tests taking the `kicad` fixture need KiCad."""
import os
import sys

import pytest

HARDWARE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'hardware'))
sys.path.insert(0, HARDWARE)


@pytest.fixture(scope='session')
def kicad():
    import kicad_env
    if not kicad_env.KICAD_CLI.exists():
        pytest.skip('KiCad not installed (run hardware/setup_tools.sh)')
    return kicad_env


@pytest.fixture(scope='session')
def board(kicad):
    """Build the whole board once (schematic -> placement -> routing) and return its JSON report."""
    import json
    import subprocess
    subprocess.run([sys.executable, str(kicad.HARDWARE / 'gen_schematic.py')], check=True)
    kicad.kipython(kicad.HARDWARE / 'gen_board.py')
    kicad.kipython(kicad.HARDWARE / 'route.py')
    return json.loads(kicad.kipython(kicad.HARDWARE / 'board_report.py', kicad.PCB).stdout)
