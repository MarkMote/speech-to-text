#!/usr/bin/env python3
"""Press any key to see what evdev events the keyd virtual keyboard emits."""
import evdev
from evdev import ecodes

for path in evdev.list_devices():
    dev = evdev.InputDevice(path)
    if "keyd" in dev.name.lower():
        print(f"Found: {dev.name} at {dev.path}")
        print("Press keys to see events (Ctrl+C to quit)...\n")
        for event in dev.read_loop():
            if event.type == ecodes.EV_KEY:
                name = ecodes.KEY.get(event.code, f"UNKNOWN({event.code})")
                state = {0: "UP", 1: "DOWN", 2: "REPEAT"}.get(event.value, event.value)
                print(f"  code={event.code} name={name} state={state}")
        break
else:
    print("No keyd device found! Available devices:")
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        print(f"  {dev.path}: {dev.name}")
