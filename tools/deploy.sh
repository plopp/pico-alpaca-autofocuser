#!/usr/bin/env bash
# Copy the board code in pico/ to the Pico's root and restart it.
# Usage: tools/deploy.sh            (uses .venv/bin/mpremote, or $MPREMOTE)
set -euo pipefail
cd "$(dirname "$0")/.."
MP=${MPREMOTE:-.venv/bin/mpremote}
files=(pico/*.py pico/config.toml)
if [ -f pico/secret.toml ]; then
    files+=(pico/secret.toml)
else
    echo "warning: pico/secret.toml missing - the Pico will start without Wi-Fi" >&2
fi
"$MP" cp "${files[@]}" : + reset
