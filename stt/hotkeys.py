import logging
import selectors
import threading
from typing import Callable

import evdev
from evdev import ecodes

from stt.config import HotkeyConfig

log = logging.getLogger(__name__)


def _resolve_key_code(name: str) -> int:
    code = ecodes.ecodes.get(name)
    if code is None:
        raise ValueError(f"Unknown key code: {name}")
    return code


def _find_device(name: str) -> evdev.InputDevice | None:
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        if name.lower() in dev.name.lower():
            return dev
    return None


class HotkeyListener(threading.Thread):
    def __init__(
        self,
        hotkeys: list[HotkeyConfig],
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ):
        super().__init__(daemon=True)
        self.hotkeys = hotkeys
        self.on_press = on_press
        self.on_release = on_release
        self._stop_event = threading.Event()

    def run(self) -> None:
        sel = selectors.DefaultSelector()
        # device_path -> (InputDevice, set of key codes)
        devices: dict[str, tuple[evdev.InputDevice, set[int]]] = {}

        for hk in self.hotkeys:
            code = _resolve_key_code(hk.key_code)

            if hk.device_name not in devices:
                dev = _find_device(hk.device_name)
                if dev is None:
                    log.error("Device not found: %s", hk.device_name)
                    continue
                devices[hk.device_name] = (dev, set())
                sel.register(dev, selectors.EVENT_READ)
                log.info("Listening on %s (%s)", dev.name, dev.path)

            devices[hk.device_name][1].add(code)
            log.info("Watching %s (code %d) on %s", hk.key_code, code, hk.device_name)

        if not devices:
            log.error("No hotkey devices found. Exiting listener.")
            return

        # Build fd -> key codes lookup for the event loop
        watched_keys: dict[int, set[int]] = {}
        for dev, codes in devices.values():
            watched_keys[dev.fd] = codes

        while not self._stop_event.is_set():
            events = sel.select(timeout=1.0)
            for key, _ in events:
                dev = key.fileobj
                try:
                    for event in dev.read():
                        if event.type != ecodes.EV_KEY:
                            continue
                        if event.code not in watched_keys[dev.fd]:
                            continue

                        if event.value == 1:  # key down
                            log.info("Hotkey pressed: %s", ecodes.KEY.get(event.code, event.code))
                            self.on_press()
                        elif event.value == 0:  # key up
                            log.info("Hotkey released: %s", ecodes.KEY.get(event.code, event.code))
                            self.on_release()
                        # value == 2 is key repeat, ignore
                except OSError as e:
                    log.warning("Device read error: %s", e)

        sel.close()

    def stop(self) -> None:
        self._stop_event.set()
