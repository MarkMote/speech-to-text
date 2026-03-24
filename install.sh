#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KEYD_CONF="/etc/keyd/default.conf"

echo "=== Speech-to-Text Install ==="
echo ""

# ── 1. System packages ──────────────────────────────────────────────
echo "[1/6] Checking system packages..."

PACKAGES_NEEDED=""
command -v xdotool &>/dev/null || PACKAGES_NEEDED="$PACKAGES_NEEDED xdotool"
command -v xclip &>/dev/null || PACKAGES_NEEDED="$PACKAGES_NEEDED xclip"
command -v xmodmap &>/dev/null || PACKAGES_NEEDED="$PACKAGES_NEEDED x11-xserver-utils"
dpkg -l | grep -q "gir1.2-appindicator3" || PACKAGES_NEEDED="$PACKAGES_NEEDED gir1.2-appindicator3-0.1"

if [ -n "$PACKAGES_NEEDED" ]; then
    echo "  Installing:$PACKAGES_NEEDED"
    sudo apt-get update -qq
    sudo apt-get install -y $PACKAGES_NEEDED
else
    echo "  All system packages present"
fi

# ── 2. keyd ─────────────────────────────────────────────────────────
echo ""
echo "[2/6] Configuring keyd..."

if ! command -v keyd.rvaiya &>/dev/null && ! dpkg -l | grep -q keyd; then
    echo "  keyd not installed. Installing..."
    # keyd PPA or manual install
    sudo apt-get install -y keyd 2>/dev/null || {
        echo "  ERROR: keyd not in apt repos. Install manually:"
        echo "  https://github.com/rvaiya/keyd"
        exit 1
    }
fi

# Backup existing keyd config
if [ -f "$KEYD_CONF" ]; then
    BACKUP="$KEYD_CONF.bak.$(date +%Y%m%d%H%M%S)"
    sudo cp "$KEYD_CONF" "$BACKUP"
    echo "  Backed up existing config to $BACKUP"
fi

# Check if capslock = f13 is already set
if grep -q "capslock = f13" "$KEYD_CONF" 2>/dev/null; then
    echo "  keyd already configured (capslock = f13)"
else
    # If there's an existing capslock mapping, replace it; otherwise add it
    if grep -q "^capslock" "$KEYD_CONF" 2>/dev/null; then
        sudo sed -i 's/^capslock = .*/capslock = f13/' "$KEYD_CONF"
        echo "  Updated existing capslock mapping to f13"
    elif grep -q "^\[main\]" "$KEYD_CONF" 2>/dev/null; then
        sudo sed -i '/^\[main\]/a capslock = f13' "$KEYD_CONF"
        echo "  Added capslock = f13 under [main]"
    else
        # No config exists, create from scratch
        sudo tee "$KEYD_CONF" > /dev/null <<'EOF'
[ids]
*

[main]
capslock = f13
EOF
        echo "  Created new keyd config"
    fi
    sudo systemctl enable keyd
    sudo systemctl restart keyd
    echo "  keyd restarted"
fi

# ── 3. Input group ──────────────────────────────────────────────────
echo ""
echo "[3/6] Checking input group..."

if groups | grep -q input; then
    echo "  Already in input group"
else
    sudo usermod -aG input "$USER"
    echo "  Added $USER to input group (reboot required)"
fi

# ── 4. Python dependencies ──────────────────────────────────────────
echo ""
echo "[4/6] Installing Python dependencies..."
pip install --quiet faster-whisper evdev pyyaml sounddevice soundfile

# ── 5. GNOME autostart ─────────────────────────────────────────────
echo ""
echo "[5/6] Setting up autostart..."

AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/speech-to-text.desktop"
mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Speech-to-Text
Exec=/usr/bin/python3 $SCRIPT_DIR/stt_daemon.py
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Phase=Applications
EOF
echo "  Created $DESKTOP_FILE"

# ── 6. Download model ──────────────────────────────────────────────
echo ""
echo "[6/6] Pre-downloading Whisper model..."
python3 -c "
from faster_whisper import WhisperModel
import yaml, os
config_path = os.path.join('$SCRIPT_DIR', 'config.yaml')
with open(config_path) as f:
    cfg = yaml.safe_load(f)
model_name = cfg.get('model', {}).get('name', 'small.en')
print(f'  Downloading {model_name}...')
WhisperModel(model_name, device='cpu', compute_type='int8')
print(f'  Model {model_name} ready')
" 2>&1 | grep -v "^$"

# ── Done ────────────────────────────────────────────────────────────
echo ""
echo "=== Installation complete ==="
echo ""
echo "To test now:  cd $SCRIPT_DIR && python3 stt_daemon.py"
echo ""

if ! groups | grep -q input; then
    echo "*** REBOOT REQUIRED ***"
    echo "You were added to the 'input' group."
    echo "Reboot for the change to take effect."
    echo "After reboot, Speech-to-Text will auto-start."
else
    echo "You can start it now or it will auto-start on next login."
fi
