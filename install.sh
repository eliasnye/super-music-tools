#!/usr/bin/env bash
set -euo pipefail

APP_ID="super-music-tools"
PYTHON_VERSION="3.12"
VENV_DIR="$HOME/.local/share/$APP_ID/venv"
APP_DIR="$(dirname "$(readlink -f "$0")")"

echo ">>> Updating APT index & installing native deps..."
sudo apt update
sudo apt install -y \
    python$PYTHON_VERSION \
    python$PYTHON_VERSION-venv \
    sox cdparanoia ffmpeg gcc python-is-python3 libpython3-dev libdbus-1-dev python3-dev libcairo2-dev libgirepository1.0-dev autoconf libtool libdbus-glib-1-dev ffmpeg sox

echo ">>> Creating Python $PYTHON_VERSION virtual-env in: $VENV_DIR"
python$PYTHON_VERSION -m venv "$VENV_DIR"

echo ">>> Activating venv & installing Python requirements..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

echo ">>> Writing launcher script run.sh"
cat > "$APP_DIR/run.sh" <<EOF
#!/usr/bin/env bash
source "$VENV_DIR/bin/activate"
exec python "$APP_DIR/main.py" "\$@"
EOF
chmod +x "$APP_DIR/run.sh"

echo ">>> Writing desktop entry"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_ID.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Super Music Tools
Exec=$APP_DIR/run.sh %u
Icon=$APP_DIR/org.example.super-music-tools.png
Terminal=false
Type=Application
Categories=AudioVideo;Utility;
EOF

echo ">>> Done!"
echo "You’ll now find *Super Music Tools* in your application menu."

