"""The looming-escape circuit plays a StepMania chart.

Each note becomes a looming threat that 'collides' at the note's time:
    LEFT  = left eye, horizon      RIGHT = right eye, horizon
    UP    = both eyes, dorsal      DOWN  = both eyes, ventral
The arrow -> threat mapping is a hand-made stimulus encoding. The decision
is a FIXED readout of DN activity (no training): left minus right hemisphere
for L/R, UP-group minus DOWN-group (from the exported model) for U/D. An arrow is
pressed when its evidence crosses half its calibrated peak; presses are
judged with StepMania's default timing windows. One step = 1 model ms; tau
is not fitted, so absolute timing and BPM limits are in model units.

    uv run python play.py [chart.sm]     # play every dance-single chart
    uv run python play.py --bpm-sweep    # random 16th streams at rising BPM
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

from model import load_model, looming_profile, simulate

RESULTS_DIR = Path(__file__).resolve().parent / "results"

DEFAULT_CHART = Path("/Applications/OutFox/Docs/SimfileFormats/SDF/test.sm")
COLUMNS = ["LEFT", "DOWN", "UP", "RIGHT"]  # dance-single order
WINDOWS = [("Marvelous", 22.5), ("Perfect", 45), ("Great", 90), ("Good", 135), ("Boo", 180)]
ITG_POINTS = {"Marvelous": 3, "Perfect": 2, "Great": 1, "Good": 0, "Boo": -4, "Miss": -8}
LOOM, LEAD_IN, TAIL = 200, 400, 300
SIGMA, NOISE, P_ACTIVE = 0.15, 0.05, 0.8
REFRACTORY = 60  # ms between presses of the same arrow (a choice, not biology)
N_REWIRED = 3
SEED = 2


# ---------------- charts and scoring (pure) ----------------

NOTE_KINDS = {"1": "tap", "2": "hold", "4": "roll"}


def parse_sm(text: str) -> tuple[dict, list[tuple[str, int, list[tuple[float, int, str]]]]]:
    """Timing ({"bpms", "stops", "offset"}) and every dance-single chart as
    (difficulty, meter, [(beat, column, kind)]). kind is tap, hold or roll
    (by its head); hold/roll ends, mines, lifts and fakes are not notes."""
    text = re.sub(r"//[^\n]*", "", text)

    def pairs(tag):
        m = re.search(rf"#{tag}:([^;]*);", text)
        return [tuple(map(float, p.split("="))) for p in (m.group(1).split(",") if m else []) if "=" in p]

    offset = re.search(r"#OFFSET:([^;]*);", text)
    timing = {"bpms": pairs("BPMS"), "stops": pairs("STOPS"),
              "offset": float(offset.group(1)) if offset and offset.group(1).strip() else 0.0}
    charts = []
    for body in re.findall(r"#NOTES:([^;]*);", text):
        f = [x.strip() for x in body.split(":")]
        if f[0] != "dance-single":
            continue
        notes = []
        for measure_idx, measure in enumerate(f[5].split(",")):
            rows = [r.strip() for r in measure.split() if len(r.strip()) == 4]
            for row_idx, row in enumerate(rows):
                beat = 4 * measure_idx + 4 * row_idx / len(rows)
                notes.extend((beat, col, NOTE_KINDS[ch]) for col, ch in enumerate(row) if ch in NOTE_KINDS)
        charts.append((f[2], int(f[3]), notes))
    return timing, charts


def beat_to_ms(beat: float, timing: dict) -> float:
    """Song time of a beat in ms, as StepMania computes it: BPM segments, plus
    every stop strictly before the beat (a note on a stop's beat comes before
    the pause), minus #OFFSET (time of beat 0 is -OFFSET seconds)."""
    bpms = timing["bpms"]
    t, prev_beat, prev_bpm = 0.0, 0.0, bpms[0][1]
    for b, bpm in bpms[1:]:
        if beat <= b:
            break
        t += (b - prev_beat) * 60000 / prev_bpm
        prev_beat, prev_bpm = b, bpm
    t += (beat - prev_beat) * 60000 / prev_bpm
    t += sum(seconds * 1000 for stop_beat, seconds in timing.get("stops", []) if stop_beat < beat)
    return t - timing.get("offset", 0.0) * 1000


def presses_from_evidence(evidence: np.ndarray, threshold: float = 0.5, refractory: int = REFRACTORY,
                          lag: float = 0.0) -> list[tuple[float, int]]:
    """evidence: (T, 4) per-arrow evidence normalised to its calibrated peak.
    A press is an upward threshold crossing, at most one per refractory window."""
    presses = []
    for col in range(evidence.shape[1]):
        above = evidence[:, col] >= threshold
        last = -10 ** 9
        for t in np.flatnonzero(above[1:] & ~above[:-1]) + 1:
            if t - last >= refractory:
                presses.append((t - lag, col))
                last = t
    return presses


def judge(notes: list[tuple[float, int]], presses: list[tuple[float, int]]) -> tuple[dict, int]:
    """Match each note to the nearest unused press in its column within the Boo window."""
    counts = {name: 0 for name, _ in WINDOWS} | {"Miss": 0}
    used = set()
    for t_note, col in sorted(notes):
        best = None
        for j, (t_press, c) in enumerate(presses):
            if c == col and j not in used and abs(t_press - t_note) <= WINDOWS[-1][1]:
                if best is None or abs(t_press - t_note) < abs(presses[best][0] - t_note):
                    best = j
        if best is None:
            counts["Miss"] += 1
            continue
        used.add(best)
        delta = abs(presses[best][0] - t_note)
        counts[next(name for name, w in WINDOWS if delta <= w)] += 1
    return counts, len(presses) - len(used)


def itg_score(counts: dict, n_notes: int) -> float:
    return sum(ITG_POINTS[k] * v for k, v in counts.items()) / (3 * n_notes)


# ---------------- the circuit as a player ----------------

class Player:
    def __init__(self, rng: np.random.Generator):
        self.c = c = load_model()
        self.elev = c.elevation
        self.lr, self.ud = c.readout_lr, c.readout_ud
        side = c.side[c.src_loc]
        centre = {"UP": 0.1, "DOWN": 0.9}
        self.templates = [np.nan_to_num(np.exp(-((self.elev - centre.get(a, 0.5)) ** 2) / (2 * SIGMA ** 2)))
                          * {"LEFT": side == "L", "RIGHT": side == "R"}.get(a, np.ones(side.size, bool))
                          for a in COLUMNS]
        self.profile = looming_profile(LOOM)
        self.rng = rng

    def evidence(self, WT, notes_ms, total_ms) -> np.ndarray:
        drive = np.zeros((total_ms, self.c.src_loc.size))
        for t_hit, col in notes_ms:
            w = self.templates[col] * (self.rng.random(self.templates[col].size) < P_ACTIVE) \
                * self.rng.uniform(0.7, 1.3, self.templates[col].size)
            t0 = int(t_hit) - LOOM
            lo, hi = max(t0, 0), min(t0 + LOOM, total_ms)
            drive[lo:hi] += np.outer(self.profile[lo - t0:hi - t0], w)
        dn = simulate(WT, self.c.src_loc, drive, self.c.dn_loc, self.c.tau, noise=NOISE, rng=self.rng)
        lr, ud = dn @ self.lr, dn @ self.ud
        return np.column_stack([np.maximum(lr, 0), np.maximum(-ud, 0), np.maximum(ud, 0), np.maximum(-lr, 0)])

    def calibrate(self, WT) -> tuple[np.ndarray, float]:
        """Per-arrow gain and a global timing offset from isolated threats,
        like StepMania's own offset calibration."""
        gains, lags = np.zeros(4), []
        for col in range(4):
            ev = self.evidence(WT, [(LOOM + 50, col)], LOOM + 250)
            gains[col] = ev[:, col].max()
            lags.append(np.argmax(ev[:, col] >= 0.5 * gains[col]) - (LOOM + 50))
        return np.where(gains > 0, gains, np.inf), float(np.mean(lags))

    def play(self, WT, calibration, notes_ms) -> tuple[dict, int]:
        gains, lag = calibration
        total = int(max(t for t, _ in notes_ms)) + TAIL
        return judge(notes_ms, presses_from_evidence(self.evidence(WT, notes_ms, total) / gains, lag=lag))


def play_chart(path: Path) -> list[dict]:
    rng = np.random.default_rng(SEED)
    player = Player(rng)
    real = player.c.weights_T()
    real_cal = player.calibrate(real)
    controls = [(W, player.calibrate(W)) for W in (player.c.rewired(rng) for _ in range(N_REWIRED))]
    timing, charts = parse_sm(path.read_text(encoding="utf-8", errors="replace"))
    print(f"chart {path.name}, BPMs {timing['bpms']}, stops {len(timing['stops'])}, offset {timing['offset']:+.3f}s; "
          f"readout offset {real_cal[1]:+.0f} model-ms. Holds/rolls are scored as taps (no key is held).\n")
    out = []
    for difficulty, meter, notes in charts:
        notes_ms = [(beat_to_ms(b, timing) + LEAD_IN, col) for b, col, _ in notes]
        holds = sum(kind != "tap" for _, _, kind in notes)
        by_time = {}
        for t, col in notes_ms:
            by_time.setdefault(t, set()).add(col)
        cancelling = sum(1 for cols in by_time.values() if {0, 3} <= cols or {1, 2} <= cols)
        counts, extra = player.play(real, real_cal, notes_ms)
        ctrl = [player.play(W, cal, notes_ms) for W, cal in controls]
        row = {"difficulty": difficulty, "meter": meter, "notes": len(notes_ms), "holds_or_rolls": holds,
               "cancelling_jumps": cancelling,
               "real": {"counts": counts, "extra_presses": extra,
                        "hit_rate": 1 - counts["Miss"] / len(notes_ms), "score": itg_score(counts, len(notes_ms))},
               "rewired_mean": {"hit_rate": float(np.mean([1 - c["Miss"] / len(notes_ms) for c, _ in ctrl])),
                                "score": float(np.mean([itg_score(c, len(notes_ms)) for c, _ in ctrl])),
                                "extra_presses": float(np.mean([e for _, e in ctrl]))}}
        out.append(row)
        r, w = row["real"], row["rewired_mean"]
        print(f"{difficulty:<10}({meter:>2}) {len(notes_ms):>3} notes ({holds} holds), {cancelling} cancelling jumps | "
              f"real hit {r['hit_rate']:.0%} score {r['score']:.0%} extra {extra} | "
              f"rewired hit {w['hit_rate']:.0%} score {w['score']:.0%} extra {w['extra_presses']:.0f}")
    return out


def bpm_sweep(n_notes: int = 64, bpms=(100, 150, 200, 250, 300, 400, 500, 600, 800)) -> list[dict]:
    rng = np.random.default_rng(SEED + 5)
    player = Player(rng)
    real = player.c.weights_T()
    cal = player.calibrate(real)
    out = []
    print(f"{n_notes} 16th notes per run; gap = 15000/BPM model-ms\n  BPM   gap | stream hit/score | jacks hit/score")
    for bpm in bpms:
        gap, row = 15000 / bpm, {"bpm": bpm}
        for kind in ("stream", "jacks"):
            cols, prev = [], -1
            while len(cols) < n_notes:
                col = int(rng.choice([x for x in range(4) if x != prev]))
                cols += [col, col] if kind == "jacks" else [col]
                prev = col
            notes = [(LEAD_IN + i * gap, col) for i, col in enumerate(cols[:n_notes])]
            counts, extra = player.play(real, cal, notes)
            row[kind] = {"hit_rate": 1 - counts["Miss"] / n_notes, "score": itg_score(counts, n_notes), "extra_presses": extra}
        out.append(row)
        print(f"  {bpm:>3} {gap:>5.0f} | {row['stream']['hit_rate']:>6.0%} {row['stream']['score']:>6.0%} | "
              f"{row['jacks']['hit_rate']:>6.0%} {row['jacks']['score']:>6.0%}")
    return out


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if "--bpm-sweep" in sys.argv:
        (RESULTS_DIR / "bpm_sweep.json").write_text(json.dumps(bpm_sweep(), indent=2) + "\n")
        return
    chart = Path(next((a for a in sys.argv[1:] if a.endswith((".sm", ".ssc"))), DEFAULT_CHART))
    (RESULTS_DIR / f"play_{chart.stem}.json").write_text(json.dumps(play_chart(chart), indent=2) + "\n")


if __name__ == "__main__":
    main()
