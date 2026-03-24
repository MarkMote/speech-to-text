#!/usr/bin/env python3
"""Speech-to-text daemon. Hold hotkey to record, release to transcribe and type."""

import logging
import os
import signal
import subprocess
import sys
import threading
import time

from stt.config import load_config
from stt.hotkeys import HotkeyListener
from stt.recorder import Recorder
from stt.transcriber import create_transcriber
from stt.typer import get_active_window, type_text

log = logging.getLogger("stt")

# Resolve config path relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(SCRIPT_DIR, "config.yaml")

# X11 keycodes that need their symbols cleared so GNOME doesn't intercept them.
# evdev KEY_F13 (183) -> X11 keycode 191 (XF86Tools)
# evdev KEY_F19 (189) -> X11 keycode 197 (already empty, but clear anyway)
X11_KEYCODES_TO_CLEAR = [191, 197]


def _clear_x11_keycodes():
    """Clear X11 symbol mappings for our hotkeys so GNOME doesn't intercept them."""
    display = os.environ.get("DISPLAY")
    if not display:
        log.info("No DISPLAY set, skipping xmodmap")
        return

    for attempt in range(5):
        try:
            for keycode in X11_KEYCODES_TO_CLEAR:
                subprocess.run(
                    ["xmodmap", "-e", f"keycode {keycode} = "],
                    capture_output=True, timeout=5,
                )
            log.info("Cleared X11 keycodes: %s", X11_KEYCODES_TO_CLEAR)
            return
        except Exception as e:
            log.warning("xmodmap attempt %d failed: %s", attempt + 1, e)
            time.sleep(2)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG
    log.info("Loading config from %s", config_path)
    config = load_config(config_path)

    # Clear X11 mappings that conflict with our hotkeys
    _clear_x11_keycodes()

    # Load model (stays in memory)
    transcriber = create_transcriber(config.model)
    transcriber.load()

    recorder = Recorder(config.audio)
    model_lock = threading.Lock()

    def on_model_change(model_name: str):
        """Switch to a different Whisper model at runtime."""
        nonlocal transcriber
        with model_lock:
            log.info("Switching model to %s...", model_name)
            if tray:
                tray.show_loading(model_name)
            transcriber.unload()
            config.model.name = model_name
            transcriber = create_transcriber(config.model)
            transcriber.load()
            log.info("Model switched to %s", model_name)
            if tray:
                tray.show_idle()

    # Try tray icon first, fall back to floating indicator, fall back to nothing
    tray = None
    indicator = None

    try:
        from stt.tray import TrayIcon
        tray = TrayIcon(
            on_quit=lambda: shutdown(),
            on_model_change=on_model_change,
            model_name=config.model.name,
        )
        log.info("Tray icon enabled")
    except Exception as e:
        log.warning("Tray icon unavailable: %s", e)
        try:
            from stt.indicator import Indicator
            indicator = Indicator(config.indicator)
            log.info("Floating indicator enabled")
        except Exception as e2:
            log.warning("Indicator also unavailable: %s. Running headless.", e2)

    target_window_id = None
    recording_lock = threading.Lock()

    def on_press():
        nonlocal target_window_id
        with recording_lock:
            target_window_id = get_active_window()
            recorder.start()
            if tray:
                tray.show_recording()
            elif indicator:
                indicator.show_recording()
            log.info("Recording... (window=%s)", target_window_id)

    def on_release():
        nonlocal target_window_id
        with recording_lock:
            audio = recorder.stop()
            wid = target_window_id

        if audio is None:
            log.info("No audio captured")
            if tray:
                tray.show_idle()
            elif indicator:
                indicator.hide()
            return

        duration = len(audio) / config.audio.sample_rate
        if duration < 0.3:
            log.info("Audio too short (%.1fs), ignoring", duration)
            if tray:
                tray.show_idle()
            elif indicator:
                indicator.hide()
            return

        if tray:
            tray.show_transcribing()
        elif indicator:
            indicator.show_transcribing()

        with model_lock:
            text = transcriber.transcribe(audio, config.audio.sample_rate)
        if text:
            type_text(text, wid, config.output.method, config.output.restore_clipboard)
        else:
            log.info("Empty transcription")

        if tray:
            tray.show_idle()
        elif indicator:
            indicator.hide()

    listener = HotkeyListener(config.hotkeys, on_press, on_release)

    def shutdown(*_):
        log.info("Shutting down...")
        listener.stop()
        recorder.cleanup()
        transcriber.unload()
        if tray:
            tray.quit()
        elif indicator:
            indicator.quit()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    listener.start()
    log.info("Speech-to-text daemon running. Press hotkey to dictate.")

    # GTK main loop (needed for tray icon or floating indicator)
    if tray:
        tray.run()
    elif indicator:
        indicator.run()
    else:
        try:
            listener.join()
        except KeyboardInterrupt:
            shutdown()


if __name__ == "__main__":
    main()
