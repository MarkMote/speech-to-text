#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Speech-to-Text Install ==="

# Check input group
if ! groups | grep -q input; then
    echo "Adding $USER to input group (needs re-login)..."
    sudo usermod -aG input "$USER"
    echo "NOTE: Log out and back in for group change to take effect."
fi

# Python deps
echo "Installing Python dependencies..."
pip install faster-whisper evdev pyyaml sounddevice soundfile

# xclip check
if ! command -v xclip &>/dev/null; then
    echo "Installing xclip..."
    sudo apt-get install -y xclip
fi

# xdotool check
if ! command -v xdotool &>/dev/null; then
    echo "Installing xdotool..."
    sudo apt-get install -y xdotool
fi

# keyd capslock remap
echo ""
echo "Updating keyd config (capslock -> move)..."
if grep -q "capslock = move" /etc/keyd/default.conf 2>/dev/null; then
    echo "keyd already configured"
else
    sudo sed -i 's/capslock = .*/capslock = move/' /etc/keyd/default.conf
    sudo systemctl restart keyd
    echo "keyd updated: capslock now sends KEY_F13 (via 'move')"
fi

# Clear X11 mapping for KEY_F13 so GNOME doesn't intercept it
# keycode 191 = X11 mapping for evdev KEY_F13
echo ""
echo "Clearing X11 mapping for keycode 191 (KEY_F13)..."
xmodmap -e "keycode 191 = " 2>/dev/null || true

# Make xmodmap change permanent via autostart
AUTOSTART_DIR="$HOME/.config/autostart"
XMODMAP_DESKTOP="$AUTOSTART_DIR/stt-xmodmap.desktop"
mkdir -p "$AUTOSTART_DIR"
cat > "$XMODMAP_DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=STT xmodmap fix
Exec=bash -c "sleep 2 && xmodmap -e 'keycode 191 = '"
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Phase=Applications
EOF
echo "Created autostart entry for xmodmap fix"

# Also clear F19 mapping (mouse button via Solaar)
# keycode 197 = X11 mapping for evdev KEY_F19
xmodmap -e "keycode 197 = " 2>/dev/null || true

# systemd service
echo ""
echo "Installing systemd user service..."
mkdir -p ~/.config/systemd/user
cp "$SCRIPT_DIR/systemd/speech-to-text.service" ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable speech-to-text.service
echo "Service installed. Start with: systemctl --user start speech-to-text"

echo ""
echo "=== Done ==="
echo "To test manually: cd $SCRIPT_DIR && python3 stt_daemon.py"
