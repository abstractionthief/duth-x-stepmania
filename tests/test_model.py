"""The exported escape model and its controls."""

import sys
from pathlib import Path

import numpy as np
import pytest
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model import double_edge_swap, load_model, looming_profile, simulate  # noqa: E402


def test_exported_model_is_consistent():
    m = load_model()
    assert m.provenance["dataset"] == "male-cns:v1.0"
    assert (m.size, m.src_loc.size, m.dn_loc.size) == (766, 311, 26)
    assert m.edge_src.size == m.edge_tgt.size == m.edge_w.size
    assert m.readout_lr.size == m.readout_ud.size == m.dn_loc.size
    assert np.all((m.elevation >= 0) & (m.elevation <= 1))
    assert set(np.unique(m.sign)) <= {-1.0, 1.0}
    WT = m.weights_T()
    assert WT.shape == (766, 766) and WT.nnz == m.edge_src.size


def random_graph(rng, n=60, m=400):
    pairs = set()
    while len(pairs) < m:
        a, b = rng.integers(0, n, 2)
        if a != b:
            pairs.add((int(a), int(b)))
    src, tgt = map(np.array, zip(*sorted(pairs)))
    return src, tgt

def test_double_edge_swap_keeps_exact_degrees_without_duplicates_or_loops():
    rng = np.random.default_rng(0)
    src, tgt = random_graph(rng)
    new = double_edge_swap(src, tgt, rng)
    assert len(set(zip(src.tolist(), new.tolist()))) == src.size      # no duplicate edges
    assert not np.any(src == new)                                    # no self-loops
    assert np.array_equal(np.bincount(new, minlength=60), np.bincount(tgt, minlength=60))  # in-degrees
    assert np.mean(new != tgt) > 0.8                                 # actually rewired

def test_double_edge_swap_can_keep_target_groups():
    rng = np.random.default_rng(1)
    src, tgt = random_graph(rng)
    side = np.where(np.arange(60) < 30, "L", "R")
    new = double_edge_swap(src, tgt, rng, group=side)
    assert np.array_equal(side[new], side[tgt])  # every edge keeps its target's side

def test_simulate_propagates_through_excitatory_chain():
    WT = sp.csr_matrix(np.array([[0, 0], [0.5, 0]]))  # neuron 0 drives neuron 1
    drive = np.ones((200, 1))
    out = simulate(WT, np.array([0]), drive, np.array([1]), tau=10.0)
    assert out[-1, 0] == pytest.approx(0.5, rel=1e-3)  # steady state relu(0.5 * 1)

def test_looming_profile_accelerates_to_one():
    p = looming_profile(200)
    assert p[-1] == pytest.approx(1.0)
    assert np.all(np.diff(p) > 0)
    assert p[100] < 0.1 < p[-10]
