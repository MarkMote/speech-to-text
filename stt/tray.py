"""System tray icon for speech-to-text daemon."""

import logging
import threading
from typing import Callable, Optional

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

AVAILABLE_MODELS = [
    ("base.en", "Base (fastest, ~140MB VRAM)"),
    ("small.en", "Small (balanced, ~260MB VRAM)"),
    ("medium.en", "Medium (accurate, ~800MB VRAM)"),
]


class TrayIcon:
    """System tray icon with status indicator and menu."""

    ICON_IDLE = "audio-input-microphone-symbolic"
    ICON_RECORDING = "media-record-symbolic"
    ICON_TRANSCRIBING = "emblem-synchronizing-symbolic"

    def __init__(
        self,
        on_quit: Callable[[], None],
        on_model_change: Optional[Callable[[str], None]] = None,
        model_name: str = "",
    ):
        self._on_quit = on_quit
        self._on_model_change = on_model_change
        self._model_name = model_name
        self._status_item = None
        self._model_items: dict[str, Gtk.RadioMenuItem] = {}
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

        menu.append(Gtk.SeparatorMenuItem())

        # Model submenu
        model_submenu = Gtk.Menu()
        group = None
        for model_id, label in AVAILABLE_MODELS:
            if group is None:
                item = Gtk.RadioMenuItem(label=label)
                group = item
            else:
                item = Gtk.RadioMenuItem(label=label, group=group)

            if model_id == model_name:
                item.set_active(True)

            item.connect("toggled", self._on_model_toggled, model_id)
            self._model_items[model_id] = item
            model_submenu.append(item)

        model_menu_item = Gtk.MenuItem(label="Model")
        model_menu_item.set_submenu(model_submenu)
        menu.append(model_menu_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: self._on_quit())
        menu.append(quit_item)

        menu.show_all()
        self._indicator.set_menu(menu)

    def _on_model_toggled(self, item: Gtk.RadioMenuItem, model_id: str):
        if not item.get_active():
            return
        if model_id == self._model_name:
            return
        log.info("Model switch requested: %s -> %s", self._model_name, model_id)
        self._model_name = model_id
        if self._on_model_change:
            # Run in a thread so GTK doesn't block during model load
            threading.Thread(
                target=self._on_model_change,
                args=(model_id,),
                daemon=True,
            ).start()

    def show_recording(self) -> None:
        if self._indicator:
            GLib.idle_add(self._set_state, self.ICON_RECORDING, "Recording...")

    def show_transcribing(self) -> None:
        if self._indicator:
            GLib.idle_add(self._set_state, self.ICON_TRANSCRIBING, "Transcribing...")

    def show_idle(self) -> None:
        if self._indicator:
            GLib.idle_add(self._set_state, self.ICON_IDLE, "Idle")

    def show_loading(self, model_name: str) -> None:
        if self._indicator:
            GLib.idle_add(self._set_state, self.ICON_TRANSCRIBING, f"Loading {model_name}...")

    def _set_state(self, icon: str, label: str):
        self._indicator.set_icon_full(icon, label)
        if self._status_item:
            self._status_item.set_label(label)
        return False

    def run(self) -> None:
        """Run GTK main loop. Call from the main thread."""
        if not HAS_APPINDICATOR:
            threading.Event().wait()
            return
        Gtk.main()

    def quit(self) -> None:
        GLib.idle_add(Gtk.main_quit)
