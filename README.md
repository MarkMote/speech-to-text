# Speech-to-Text

Local, private speech-to-text for Linux. Hold a key, speak, release -- text appears at your cursor.

Uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) running on your GPU. No cloud services, no subscription, no data leaves your machine.

## How it works

1. Press and hold **Caps Lock**
2. Speak
3. Release -- transcribed text is typed wherever your cursor is

Works in terminals, text editors, browsers, chat apps -- anywhere you can type.

## Features

- **Fast** -- model stays loaded in GPU memory, transcription takes <1 second
- **Private** -- everything runs locally, nothing sent to the cloud
- **System-wide** -- works in any application via hotkey
- **System tray** -- shows recording/transcribing status
- **Configurable** -- swap Whisper models, change hotkeys, adjust audio settings

## Requirements

- Linux with X11 (GNOME, KDE, etc.)
- NVIDIA GPU with CUDA (for GPU acceleration) or CPU-only mode
- Python 3.10+

## Install

```bash
git clone https://github.com/MarkMote/speech-to-text.git
cd speech-to-text
./install.sh
```

The install script handles everything:
- Installs system packages (keyd, xdotool, xclip)
- Configures Caps Lock as the dictation hotkey (via keyd)
- Adds your user to the `input` group (for hotkey detection)
- Installs Python dependencies
- Downloads the Whisper model
- Sets up auto-start on login

**Reboot after install** if prompted (required for input group changes).

## Uninstall

```bash
./uninstall.sh
```

## Configuration

Edit `config.yaml`:

```yaml
model:
  name: "small.en"        # base.en (fast), small.en (balanced), medium.en (accurate)
  device: "cuda"           # cuda or cpu
  compute_type: "int8_float16"

hotkeys:
  - device_name: "keyd virtual keyboard"
    key_code: "KEY_F13"    # Caps Lock (remapped by keyd)

output:
  method: "type"           # "type" (universal) or "paste" (faster, issues in terminals)
```

### Model sizes

| Model | VRAM | Speed | Accuracy |
|-------|------|-------|----------|
| base.en | ~140MB | Fastest | Good |
| small.en | ~260MB | Fast | Better |
| medium.en | ~800MB | Moderate | Best |

## Manual usage

```bash
# Run directly (instead of auto-start)
python3 stt_daemon.py

# Check logs when running as auto-start app
cat /tmp/stt.log
```

## How it works (technical)

- **keyd** remaps Caps Lock to F13 at the kernel level
- **evdev** detects F13 key press/release (below X11, works in any app)
- **sounddevice** captures mic audio while key is held
- **faster-whisper** transcribes audio on GPU
- **xdotool** types the result at the cursor position
- **AppIndicator** shows status in the system tray
- **xmodmap** clears X11's default F13 mapping so GNOME doesn't intercept it

## License

MIT
