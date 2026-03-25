import logging
import os
import subprocess
import time

log = logging.getLogger(__name__)

# WM_CLASS values that need Ctrl+Shift+V instead of Ctrl+V
# Terminals and Electron apps (VS Code, Windsurf, etc.)
CTRL_SHIFT_V_CLASSES = {
    "gnome-terminal", "terminator", "xterm", "urxvt", "alacritty",
    "kitty", "tilix", "konsole", "xfce4-terminal", "mate-terminal",
    "guake", "tilda", "st-256color", "st", "foot", "wezterm",
    "windsurf", "code", "electron",
}


def _detect_display() -> str:
    """Detect the active X11 DISPLAY by checking the user's session."""
    try:
        result = subprocess.run(
            ["w", "-hs"], capture_output=True, text=True, timeout=2,
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith(":"):
                return parts[1]
    except Exception:
        pass
    return ":0"


_cached_env = None


def _get_env():
    """Get environment with DISPLAY guaranteed for X11 tools."""
    global _cached_env
    if _cached_env is not None:
        return _cached_env

    env = os.environ.copy()
    if "DISPLAY" not in env or not env["DISPLAY"]:
        env["DISPLAY"] = _detect_display()
        log.info("Auto-detected DISPLAY=%s", env["DISPLAY"])
    if "XAUTHORITY" not in env:
        env["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
    _cached_env = env
    return _cached_env


def _get_wm_class(window_id: int) -> str:
    """Get the WM_CLASS of a window."""
    try:
        result = subprocess.run(
            ["xprop", "-id", str(window_id), "WM_CLASS"],
            capture_output=True, text=True, timeout=2, env=_get_env(),
        )
        if result.returncode == 0:
            return result.stdout.strip().lower()
    except Exception:
        pass
    return ""


def get_active_window() -> int | None:
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, timeout=2,
            env=_get_env(),
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception as e:
        log.warning("Failed to get active window: %s", e)
    return None


def type_text(text: str, window_id: int | None = None, method: str = "paste",
              restore_clipboard: bool = True) -> None:
    if not text:
        return

    # Always use paste — xdotool type freezes terminals
    _paste_text(text, window_id, restore_clipboard)


def _paste_text(text: str, window_id: int | None, restore: bool) -> None:
    env = _get_env()
    old_clipboard = None
    if restore:
        try:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, timeout=2, env=env,
            )
            if result.returncode == 0:
                old_clipboard = result.stdout
        except Exception:
            pass

    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=text.encode(), timeout=2, env=env,
    )

    if window_id is not None:
        subprocess.run(
            ["xdotool", "windowactivate", "--sync", str(window_id)],
            timeout=2, env=env,
        )

    # Detect if window needs Ctrl+Shift+V (terminals, Electron apps)
    paste_key = "ctrl+v"
    if window_id is not None:
        wm_class = _get_wm_class(window_id)
        if any(cls in wm_class for cls in CTRL_SHIFT_V_CLASSES):
            paste_key = "ctrl+shift+v"
            log.debug("Using Ctrl+Shift+V for %s", wm_class)

    subprocess.run(["xdotool", "key", paste_key], timeout=2, env=env)
    log.info("Pasted %d chars into window %s (%s)", len(text), window_id, paste_key)

    if restore and old_clipboard is not None:
        time.sleep(0.15)
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=old_clipboard, timeout=2, env=env,
        )
