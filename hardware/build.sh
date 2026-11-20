#!/usr/bin/env bash
# Rebuild the whole PCB from hardware/design.py: schematic, placement, autorouting, fab files.
# One-time setup: hardware/setup_tools.sh
set -euo pipefail
cd "$(dirname "$0")/.."
KIPY="${KICAD_ROOT:-$HOME/.local/opt/kicad-10.0.7/squashfs-root}/bin/python3.11"
python3 hardware/gen_schematic.py
"$KIPY" hardware/gen_board.py
"$KIPY" hardware/route.py
"$KIPY" hardware/gen_fab.py
echo "Done: hardware/fab/ (check with: python3 -m pytest tests/hardware -q)"
