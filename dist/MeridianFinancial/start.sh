#!/bin/sh
# Meridian Financial — Linux launcher.
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    exec python3 launcher.py
fi

echo
echo "Meridian needs Python 3.11 or newer (python3 was not found)."
echo "Install it with your package manager, then run ./start.sh again."
exit 1
