#!/bin/bash
# Meridian Financial — macOS launcher. Double-click to start.
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    exec python3 launcher.py
fi

echo
echo "Meridian needs Python 3.11 or newer, and none was found on this Mac."
echo
echo "  1. Download it from https://www.python.org/downloads/"
echo "  2. Run the installer"
echo "  3. Double-click 'Start Meridian.command' again"
echo
read -r -p "Press Enter to close this window."
