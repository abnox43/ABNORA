#!/usr/bin/env bash
# Install ABNORA system-wide on Linux (Debian/Ubuntu, Arch, Fedora).
#
# Usage:
#   ./packaging/install-linux.sh            # install to ~/.local
#   PREFIX=/usr ./packaging/install-linux.sh   # system-wide (needs sudo)
#
# This builds a virtualenv at $PREFIX/opt/abnora from your *system* PySide6
# and PyMuPDF (so Qt matches your desktop), then drops a launcher + .desktop
# entry + icons into the normal XDG locations.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
VENV_DIR="$PREFIX/opt/abnora"
BIN_DIR="$PREFIX/bin"
APPS_DIR="$PREFIX/share/applications"
ICONS_DIR="$PREFIX/share/icons/hicolor/256x256/apps"

echo "==> Installing ABNORA to $VENV_DIR"
mkdir -p "$VENV_DIR" "$BIN_DIR" "$APPS_DIR" "$ICONS_DIR"

# Prefer the distro Qt/PyMuPDF if present (smaller, better integrated);
# otherwise fall back to PyPI wheels inside the venv.
if python3 -c "import PySide6, pymupdf" 2>/dev/null; then
    echo "==> Using system PySide6 + PyMuPDF"
    python3 -m venv --system-site-packages "$VENV_DIR"
else
    echo "==> System PySide6/PyMuPDF not found; installing from PyPI (larger download)"
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet "$REPO_DIR"

echo "==> Writing launcher $BIN_DIR/abnora"
cat > "$BIN_DIR/abnora" <<LAUNCH
#!/usr/bin/env bash
exec "$VENV_DIR/bin/abnora" "\$@"
LAUNCH
chmod +x "$BIN_DIR/abnora"

echo "==> Installing desktop entry and icon"
cp "$REPO_DIR/packaging/abnora.desktop" "$APPS_DIR/abnora.desktop"
cp "$REPO_DIR/docs/brand/abnora-logo-64.png" "$ICONS_DIR/abnora.png"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo
echo "Done. Launch with:  abnora [file.pdf]"
echo "Or find 'ABNORA' in your application menu."
