#!/bin/bash
set -e

echo "=== Speech-to-Text Uninstall ==="
echo ""

# Kill running daemon
pkill -f "stt_daemon.py" 2>/dev/null && echo "Stopped running daemon" || echo "No daemon running"

# Remove autostart
DESKTOP_FILE="$HOME/.config/autostart/speech-to-text.desktop"
if [ -f "$DESKTOP_FILE" ]; then
    rm "$DESKTOP_FILE"
    echo "Removed autostart entry"
fi

# Restore keyd capslock mapping
KEYD_CONF="/etc/keyd/default.conf"
if grep -q "capslock = f13" "$KEYD_CONF" 2>/dev/null; then
    echo ""
    echo "keyd currently maps Caps Lock to F13 for this app."
    read -p "Restore Caps Lock to default? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo sed -i 's/capslock = f13/# capslock = f13 (removed by stt uninstall)/' "$KEYD_CONF"
        sudo systemctl restart keyd
        echo "keyd config updated, Caps Lock restored"
    else
        echo "keyd config left as-is"
    fi
fi

echo ""
echo "=== Uninstall complete ==="
echo "Note: Python packages (faster-whisper, evdev, etc.) were not removed."
echo "Note: User remains in 'input' group."
