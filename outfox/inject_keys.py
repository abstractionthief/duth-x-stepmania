"""Feasibility test: does OutFox react to synthetic macOS key events?

Sends a few arrow presses to whatever window is focused, after a countdown.
Put OutFox on a menu screen (e.g. the song wheel), run this, click into the
OutFox window during the countdown, and watch whether the cursor moves.

    uv run --extra live python outfox/inject_keys.py [--numpad]

--numpad uses keypad 4/2/8/6, StepMania's default Player 2 arrows.
macOS only. The terminal app running this needs Accessibility permission
(System Settings > Privacy & Security > Accessibility), or events are dropped.
"""

import sys
import time

import Quartz

ARROWS = {"left": 123, "right": 124, "down": 125, "up": 126}           # macOS virtual key codes
NUMPAD = {"left": 86, "right": 88, "down": 84, "up": 91}               # keypad 4, 6, 2, 8
SEQUENCE = ["down", "down", "down", "up", "up", "up", "right", "left"]
HOLD_S, GAP_S, COUNTDOWN_S = 0.05, 0.4, 5


def accessibility_trusted() -> bool:
    try:
        from ApplicationServices import AXIsProcessTrusted
        return bool(AXIsProcessTrusted())
    except ImportError:
        return True  # can't check without pyobjc ApplicationServices; the test itself will tell


def press(keycode: int) -> None:
    for down in (True, False):
        event = Quartz.CGEventCreateKeyboardEvent(None, keycode, down)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        time.sleep(HOLD_S if down else 0)


def main() -> None:
    keys = NUMPAD if "--numpad" in sys.argv else ARROWS
    if not accessibility_trusted():
        print("This terminal lacks Accessibility permission; macOS will drop the events.\n"
              "Grant it in System Settings > Privacy & Security > Accessibility, then rerun.")
        return
    print(f"Sending {len(SEQUENCE)} presses ({'keypad' if keys is NUMPAD else 'arrow keys'}) "
          f"in {COUNTDOWN_S} s - focus the OutFox window now.")
    for s in range(COUNTDOWN_S, 0, -1):
        print(f"  {s}...", flush=True)
        time.sleep(1)
    for name in SEQUENCE:
        print(f"  {name}", flush=True)
        press(keys[name])
        time.sleep(GAP_S)
    print("Done. Did the OutFox menu cursor move?")


if __name__ == "__main__":
    main()
