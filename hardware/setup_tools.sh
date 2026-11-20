#!/usr/bin/env bash
# One-time tool setup for the PCB build (no sudo; everything under ~/.local/opt).
#   KiCad 10.0.7 : extracted from the AppImage  -> ~/.local/opt/kicad-10.0.7/squashfs-root
#   FreeRouting  : pinned release jar           -> ~/.local/opt/freerouting/
# Override the AppImage location with KICAD_APPIMAGE=/path/to/kicad.AppImage
set -euo pipefail
OPT="$HOME/.local/opt"
KICAD_DIR="$OPT/kicad-10.0.7"
APPIMAGE="${KICAD_APPIMAGE:-$HOME/Downloads/kicad-10.0.7-x86_64.AppImage}"
FR_VERSION="2.1.0"   # newest release that runs on Java 21 (2.2+ need Java 25)
FR_DIR="$OPT/freerouting"
FR_JAR="$FR_DIR/freerouting-$FR_VERSION.jar"

mkdir -p "$OPT"
if [ ! -x "$KICAD_DIR/squashfs-root/bin/kicad-cli" ]; then
    echo "Extracting $APPIMAGE ..."
    mkdir -p "$KICAD_DIR"
    (cd "$KICAD_DIR" && "$APPIMAGE" --appimage-extract >/dev/null)
fi
if [ ! -f "$FR_JAR" ]; then
    mkdir -p "$FR_DIR"
    curl -fsSL -o "$FR_JAR" \
        "https://github.com/freerouting/freerouting/releases/download/v$FR_VERSION/freerouting-$FR_VERSION.jar"
fi
"$KICAD_DIR/squashfs-root/bin/kicad-cli" version
echo "FreeRouting: $FR_JAR"
