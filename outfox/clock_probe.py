"""Feasibility test for the FlyClock theme: read OutFox's song clock and judgments.

Polls Save/flyclock/clock.txt, fits song time = local time - offset over the
samples so far, and reports how well the two clocks agree. Also prints the
session header and every new judgment. Ctrl+C to stop.

    uv run python outfox/clock_probe.py
"""

import time
from pathlib import Path

import numpy as np

# OutFox maps "Save/" to its preferences folder on macOS; check both likely places.
CANDIDATES = [Path.home() / "Library/Preferences/Project OutFox/flyclock",
              Path.home() / "Library/Application Support/Project OutFox/Save/flyclock"]


def flyclock_dir() -> Path:
    return next((p for p in CANDIDATES if p.exists()), CANDIDATES[0])


POLL_S = 0.002


def read(path: Path) -> str:
    try:
        return path.read_text()
    except (FileNotFoundError, PermissionError):
        return ""


def main() -> None:
    print("watching " + " | ".join(map(str, CANDIDATES)) + " - start a song in OutFox (theme: FlyClock)")
    last_clock, last_session, seen_judgments = "", "", 0
    samples: list[tuple[float, float]] = []   # (local seconds, song seconds)
    last_report = 0.0
    while True:
        now = time.perf_counter()
        FLYCLOCK = flyclock_dir()
        session = read(FLYCLOCK / "session.txt")
        if session and session != last_session:
            last_session, samples, seen_judgments = session, [], 0
            print("\n--- new song ---\n" + session.strip())
        clock = read(FLYCLOCK / "clock.txt")
        if clock and clock != last_clock:
            last_clock = clock
            parts = clock.split()
            if len(parts) >= 1:
                samples.append((now, float(parts[0])))
        lines = read(FLYCLOCK / "judgments.txt").splitlines()
        for line in lines[seen_judgments:]:
            print("  judgment:", line)
        seen_judgments = max(seen_judgments, len(lines))
        if len(samples) >= 20 and now - last_report > 2:
            last_report = now
            local, song = np.array(samples[-200:]).T
            slope, intercept = np.polyfit(local, song, 1)
            residual_ms = 1000 * np.std(song - (slope * local + intercept))
            print(f"  {len(samples)} clock samples: song time ≈ {slope:.4f} × local {intercept:+.3f} s; "
                  f"jitter {residual_ms:.1f} ms; song at {song[-1]:.2f} s")
        time.sleep(POLL_S)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
