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
    sox cdparanoia ffmpeg gcc libdbus-1-dev python3.12-dev libcairo2-dev libgirepository1.0-dev autoconf libtool libdbus-glib-1-dev

echo ">>> Installing libdiscid from source..."

LIBDISCID_VERSION="0.6.5"
LIBDISCID_URL="https://ftp.osuosl.org/pub/musicbrainz/libdiscid-${LIBDISCID_VERSION}.tar.gz"
LIBDISCID_DIR="libdiscid-${LIBDISCID_VERSION}"

# Temp directory for build
BUILD_TMP="$(mktemp -d)"
pushd "$BUILD_TMP"

# Download and extract
curl -LO "$LIBDISCID_URL"
tar xf "libdiscid-${LIBDISCID_VERSION}.tar.gz"
cd "$LIBDISCID_DIR"

# Build and install
cmake .
make -j$(nproc)
sudo make install

# Clean up
popd
rm -rf "$BUILD_TMP"
echo ">>> libdiscid $LIBDISCID_VERSION installed successfully."

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

