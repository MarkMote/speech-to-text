#!/usr/bin/env python3
"""Watch ALL input devices for key events. Press any key/button to see where it comes from."""
import selectors
import evdev
from evdev import ecodes

sel = selectors.DefaultSelector()
devices = {}

for path in evdev.list_devices():
    dev = evdev.InputDevice(path)
    sel.register(dev, selectors.EVENT_READ)
    devices[dev.fd] = dev
    print(f"  {dev.path}: {dev.name}")

print(f"\nWatching {len(devices)} devices. Press keys/buttons (Ctrl+C to quit)...\n")

while True:
    for key, _ in sel.select(timeout=None):
        dev = key.fileobj
        for event in dev.read():
            if event.type == ecodes.EV_KEY:
                name = ecodes.KEY.get(event.code, ecodes.BTN.get(event.code, f"UNKNOWN({event.code})"))
                state = {0: "UP", 1: "DOWN", 2: "REPEAT"}.get(event.value, str(event.value))
                print(f"  [{dev.name}] code={event.code} name={name} state={state}")
