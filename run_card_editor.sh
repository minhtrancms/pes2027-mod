#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Select Python environment with pymobiledevice3 and PIL
PYTHON_BIN="/Users/nhatminh/.local/pipx/.cache/26d7aa47311ea6b/bin/python3"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(which python3)"
fi

echo "=========================================================="
echo "   eFootball 2027 - Card Mod Studio Launcher"
echo "=========================================================="
echo "Python binary: $PYTHON_BIN"
echo "Starting Card Mod Studio on http://127.0.0.1:8899 ..."
echo ""

# Open browser after 1 second in background
(sleep 1 && open "http://127.0.0.1:8899") &

# Run server
exec "$PYTHON_BIN" "$DIR/tools/card_editor/server.py"
