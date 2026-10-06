"""The looming-escape circuit model, loaded from model/escape_model.json.

The file is exported by Drosophila Under the Hood
(experiments/escape_code/export_model.py) from the MaleCNS v1.0 connectome;
this module only runs it. Model: x <- x + (1/tau) * (-x + relu(W^T x + I)),
one step = one model ms (tau not fitted, so times are model units).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy.sparse as sp

MODEL_PATH = Path(__file__).resolve().parent / "model" / "escape_model.json"


@dataclass
class EscapeModel:
    side: np.ndarray            # per neuron
    cell_type: np.ndarray
    sign: np.ndarray
    denom: np.ndarray
    edge_src: np.ndarray
    edge_tgt: np.ndarray
    edge_w: np.ndarray
    src_loc: np.ndarray         # detector indices
    elevation: np.ndarray       # per detector, 0 = most dorsal
    dn_loc: np.ndarray          # looming descending-neuron indices
    readout_lr: np.ndarray      # per DN: +1 left, -1 right
    readout_ud: np.ndarray      # per DN: +1 UP group, -1 DOWN group
    tau: float
    provenance: dict

    @property
    def size(self) -> int:
        return self.side.size

    def weights_T(self, targets: np.ndarray | None = None) -> sp.csr_matrix:
        """Row i = signed, input-normalised influences onto neuron i."""
        tgt = self.edge_tgt if targets is None else targets
        M = sp.csr_matrix((self.edge_w, (self.edge_src, tgt)), shape=(self.size, self.size))
        return (sp.diags(self.sign) @ M @ sp.diags(1.0 / self.denom)).T.tocsr()

    def rewired(self, rng: np.random.Generator, keep_target_side: bool = False) -> sp.csr_matrix:
        """Degree-preserving control: the same neurons and degrees, random wiring."""
        group = self.side if keep_target_side else None
        return self.weights_T(double_edge_swap(self.edge_src, self.edge_tgt, rng, group=group))


def load_model(path: Path = MODEL_PATH) -> EscapeModel:
    d = json.loads(Path(path).read_text())
    if d.get("schema_version") != 1:
        raise ValueError(f"unsupported model schema {d.get('schema_version')!r}")
    elev = np.array([np.nan if e is None else e for e in d["detectors"]["elevation"]], dtype=float)
    return EscapeModel(
        side=np.array(d["neurons"]["side"]), cell_type=np.array(d["neurons"]["type"]),
        sign=np.array(d["neurons"]["sign"], dtype=float), denom=np.array(d["neurons"]["denom"], dtype=float),
        edge_src=np.array(d["edges"]["src"]), edge_tgt=np.array(d["edges"]["tgt"]),
        edge_w=np.array(d["edges"]["synapses"], dtype=float),
        src_loc=np.array(d["detectors"]["index"]), elevation=elev, dn_loc=np.array(d["descending"]["index"]),
        readout_lr=np.array(d["readout"]["left_minus_right"], dtype=float),
        readout_ud=np.array(d["readout"]["up_minus_down"], dtype=float),
        tau=float(d["model"]["tau"]), provenance=d["provenance"],
    )


def double_edge_swap(src: np.ndarray, tgt: np.ndarray, rng: np.random.Generator,
                     swaps_per_edge: int = 10, group: np.ndarray | None = None) -> np.ndarray:
    """Maslov-Sneppen rewiring: swap a->b, c->d into a->d, c->b, rejecting self-loops
    and duplicate edges. Exact in/out-degrees; weights move with their source. With
    `group`, b and d must share a label. Returns new targets in the original edge order."""
    tgt = tgt.copy()
    existing = set(zip(src.tolist(), tgt.tolist()))
    n = src.size
    picks = rng.integers(0, n, size=(swaps_per_edge * n, 2))
    for i, j in picks:
        a, b, c, d = src[i], tgt[i], src[j], tgt[j]
        if i == j or b == d or a == d or c == b:
            continue
        if group is not None and group[b] != group[d]:
            continue
        if (a, d) in existing or (c, b) in existing:
            continue
        existing.difference_update(((a, b), (c, d)))
        existing.update(((a, d), (c, b)))
        tgt[i], tgt[j] = d, b
    return tgt


def looming_profile(length: int, scale: float = 10.0) -> np.ndarray:
    """Angular size 2*atan(r/d) of an object approaching at constant speed,
    normalised to 1 at collision: slow, then explosive growth."""
    k = np.arange(length)
    p = 2 * np.arctan(scale / (length - k))
    return p / p.max()


def simulate(WT: sp.csr_matrix, src_loc: np.ndarray, drive: np.ndarray, dn_loc: np.ndarray,
             tau: float, noise: float = 0.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """drive: (T, n_detectors) input. Returns DN activity (T, n_dn)."""
    x = np.zeros(WT.shape[0])
    out = np.zeros((drive.shape[0], dn_loc.size))
    for t in range(drive.shape[0]):
        I = np.zeros_like(x)
        I[src_loc] = drive[t]
        if noise:
            I[src_loc] += noise * rng.random(src_loc.size)
        x = x + (1.0 / tau) * (-x + np.maximum(0.0, WT @ x + I))
        out[t] = x[dn_loc]
    return out
