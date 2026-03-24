import logging
import threading

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import cairo

from stt.config import IndicatorConfig

log = logging.getLogger(__name__)


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


class Indicator:
    def __init__(self, config: IndicatorConfig):
        self.config = config
        self._window = None
        self._color = (1, 0, 0)
        self._visible = False

        if not config.enabled:
            return

        self._window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self._window.set_decorated(False)
        self._window.set_keep_above(True)
        self._window.set_skip_taskbar_hint(True)
        self._window.set_skip_pager_hint(True)
        self._window.set_app_paintable(True)
        self._window.set_default_size(config.size, config.size)

        screen = self._window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self._window.set_visual(visual)

        self._window.connect("draw", self._on_draw)

        # Position
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geom = monitor.get_geometry()

        margin = 10
        if "right" in config.position:
            x = geom.x + geom.width - config.size - margin
        else:
            x = geom.x + margin
        if "bottom" in config.position:
            y = geom.y + geom.height - config.size - margin
        else:
            y = geom.y + margin

        self._window.move(x, y)

        # Click-through
        input_region = cairo.Region(cairo.RectangleInt(0, 0, 0, 0))
        self._window.input_shape_combine_region(input_region)

    def _on_draw(self, widget, cr):
        cr.set_operator(1)  # CAIRO_OPERATOR_SOURCE
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()

        r, g, b = self._color
        size = self.config.size
        cr.set_source_rgba(r, g, b, 0.9)
        cr.arc(size / 2, size / 2, size / 2 - 1, 0, 2 * 3.14159)
        cr.fill()

    def show_recording(self) -> None:
        if not self.config.enabled:
            return
        self._color = _hex_to_rgb(self.config.colors["recording"])
        GLib.idle_add(self._show)

    def show_transcribing(self) -> None:
        if not self.config.enabled:
            return
        self._color = _hex_to_rgb(self.config.colors["transcribing"])
        GLib.idle_add(self._show)

    def hide(self) -> None:
        if not self.config.enabled:
            return
        GLib.idle_add(self._hide)

    def _show(self):
        if self._window:
            self._window.show_all()
            self._window.queue_draw()
        return False

    def _hide(self):
        if self._window:
            self._window.hide()
        return False

    def run(self) -> None:
        if not self.config.enabled:
            # Block forever if no indicator
            threading.Event().wait()
            return
        Gtk.main()

    def quit(self) -> None:
        GLib.idle_add(Gtk.main_quit)
