"""Export what the fly's-eye panel shows, from the exported escape model:
detector positions and, per arrow, many noisy trials of the threat drive and
the DN readout over time, for the real wiring and one rewired control.
Run from the repository root:

    uv run python viewer/tools/export_eye.py viewer/eye.json
"""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from model import simulate  # noqa: E402
from play import COLUMNS, LOOM, Player  # noqa: E402

OUT = sys.argv[1]
TAIL, STEP = 160, 4      # model-ms after collision; export every 4 model-ms
N_SAMPLES = 24           # independent noisy trials per arrow; the viewer picks one per threat
NOISE, P_ACTIVE = 0.05, 0.8  # same input noise and detector participation as play.py
rng = np.random.default_rng(7)
player = Player(rng)
c = player.c
real = player.c.weights_T()
rewired = player.c.rewired(np.random.default_rng(3))
cal = {"real": player.calibrate(real), "rewired": player.calibrate(rewired)}
profile = np.concatenate([player.profile, np.zeros(TAIL)])


def trace(WT, gains, w, seed):
    dn = simulate(WT, c.src_loc, np.outer(profile, w), c.dn_loc, c.tau, noise=NOISE, rng=np.random.default_rng(seed))
    lr, ud = dn @ player.lr, dn @ player.ud
    ev = np.column_stack([np.maximum(lr, 0), np.maximum(-ud, 0), np.maximum(ud, 0), np.maximum(-lr, 0)]) / gains
    return ev[::STEP]


def decision(ev, threshold=0.5):
    crossed = np.flatnonzero(ev.max(1) >= threshold)
    return COLUMNS[int(np.argmax(ev[crossed[0]]))] if crossed.size else "none"


arrows, accuracy = {}, {"real": [], "rewired": []}
for col, name in enumerate(COLUMNS):
    samples = []
    for k in range(N_SAMPLES):
        w = player.templates[col] * (rng.random(c.src_loc.size) < P_ACTIVE) * rng.uniform(0.7, 1.3, c.src_loc.size)
        seed = int(rng.integers(1 << 31))
        ev = {kind: trace(W, cal[kind][0], w, seed) for kind, W in (("real", real), ("rewired", rewired))}
        for kind in ev:
            accuracy[kind].append(decision(ev[kind]) == name)
        samples.append({"weights": np.round(w / w.max(), 3).tolist(),
                        "evidence": {kind: np.round(v, 3).tolist() for kind, v in ev.items()}})
    arrows[name] = samples

payload = {
    "note": f"Model output of model/escape_model.json (rate model, fixed readout): {N_SAMPLES} noisy trials per arrow "
            "(random detector subset, amplitudes and input noise, as in play.py); the viewer plays a random one. "
            "Detector vertical position = estimated elevation rank (0 = top); horizontal placement is illustrative.",
    "columns": COLUMNS, "step_ms": STEP, "collision_index": LOOM // STEP, "threshold": 0.5,
    "profile": np.round(profile[::STEP], 4).tolist(),
    "detectors": {"side": c.side[c.src_loc].tolist(), "type": c.cell_type[c.src_loc].tolist(),
                  "elev": np.round(np.nan_to_num(player.elev, nan=0.5), 3).tolist()},
    "arrows": arrows,
}
open(OUT, "w").write(json.dumps(payload, separators=(",", ":")))
for kind, hits in accuracy.items():
    print(f"{kind:<8} correct decisions: {sum(hits)}/{len(hits)} ({np.mean(hits):.0%})")
