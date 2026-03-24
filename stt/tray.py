"""System tray icon for speech-to-text daemon."""

import logging
import os
import threading
from typing import Callable

import gi
gi.require_version("Gtk", "3.0")
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3
    HAS_APPINDICATOR = True
except (ValueError, ImportError):
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator3
        HAS_APPINDICATOR = True
    except (ValueError, ImportError):
        HAS_APPINDICATOR = False

from gi.repository import Gtk, GLib

log = logging.getLogger(__name__)


class TrayIcon:
    """System tray icon with status indicator and menu."""

    ICON_IDLE = "audio-input-microphone-symbolic"
    ICON_RECORDING = "media-record-symbolic"
    ICON_TRANSCRIBING = "emblem-synchronizing-symbolic"

    def __init__(self, on_quit: Callable[[], None], model_name: str = ""):
        self._on_quit = on_quit
        self._model_name = model_name
        self._status_item = None
        self._indicator = None

        if not HAS_APPINDICATOR:
            log.warning("AppIndicator3 not available — no tray icon")
            return

        self._indicator = AppIndicator3.Indicator.new(
            "speech-to-text",
            self.ICON_IDLE,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._indicator.set_title("Speech-to-Text")

        menu = Gtk.Menu()

        # Status item (not clickable)
        self._status_item = Gtk.MenuItem(label="Idle")
        self._status_item.set_sensitive(False)
        menu.append(self._status_item)

        # Model info
        if model_name:
            model_item = Gtk.MenuItem(label=f"Model: {model_name}")
            model_item.set_sensitive(False)
            menu.append(model_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: self._on_quit())
        menu.append(quit_item)

        menu.show_all()
        self._indicator.set_menu(menu)

    def show_recording(self) -> None:
        if self._indicator:
            GLib.idle_add(self._set_state, self.ICON_RECORDING, "Recording...")

    def show_transcribing(self) -> None:
        if self._indicator:
            GLib.idle_add(self._set_state, self.ICON_TRANSCRIBING, "Transcribing...")

    def show_idle(self) -> None:
        if self._indicator:
            GLib.idle_add(self._set_state, self.ICON_IDLE, "Idle")

    def _set_state(self, icon: str, label: str):
        self._indicator.set_icon_full(icon, label)
        if self._status_item:
            self._status_item.set_label(label)
        return False

    def run(self) -> None:
        """Run GTK main loop. Call from the main thread."""
        if not HAS_APPINDICATOR:
            # Block forever without GTK
            threading.Event().wait()
            return
        Gtk.main()

    def quit(self) -> None:
        GLib.idle_add(Gtk.main_quit)
