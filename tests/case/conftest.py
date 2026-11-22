"""Case tests. Geometry tests need build123d, which lives in .venv:
    .venv/bin/python -m pytest tests/case -q
Under a Python without it only the parameter tests run."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'hardware'))

collect_ignore = [] if importlib.util.find_spec('build123d') else [
    'test_body.py', 'test_lid_plate.py', 'test_build.py']


@pytest.fixture(scope='session')
def board():
    """JSON report of the committed board (needs KiCad's Python)."""
    import kicad_env
    if not kicad_env.KICAD_PYTHON.exists():
        pytest.skip('KiCad not installed (run hardware/setup_tools.sh)')
    return json.loads(kicad_env.kipython(kicad_env.HARDWARE / 'board_report.py',
                                         kicad_env.PCB).stdout)
