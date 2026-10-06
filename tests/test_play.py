"""Chart parsing, timing and scoring rules of the chart player."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from play import beat_to_ms, itg_score, judge, parse_sm, presses_from_evidence  # noqa: E402


SM = """#OFFSET:-0.100;
#BPMS:0.000=120.000,4.000=240.000;
#STOPS:4.000=0.500;
#NOTES:
     dance-single:
     :
     Easy:
     2:
     0:
1000
0000
0010
0000
,
0201
0000
4300
M000
,
0000
0000
0000
3000
;
#NOTES:
     dance-double:
     :
     Hard:
     5:
     0:
10000000
;
"""


def test_parse_sm_reads_timing_and_note_kinds():
    timing, charts = parse_sm(SM)
    assert timing == {"bpms": [(0.0, 120.0), (4.0, 240.0)], "stops": [(4.0, 0.5)], "offset": -0.1}
    assert len(charts) == 1
    difficulty, meter, notes = charts[0]
    assert (difficulty, meter) == ("Easy", 2)
    assert notes == [(0.0, 0, "tap"), (2.0, 2, "tap"), (4.0, 1, "hold"), (4.0, 3, "tap"), (6.0, 0, "roll")]

def test_beat_to_ms_handles_bpm_changes_stops_and_offset():
    timing = {"bpms": [(0.0, 120.0), (4.0, 240.0)], "stops": [(4.0, 0.5)], "offset": -0.1}
    assert beat_to_ms(0, timing) == pytest.approx(100)    # beat 0 sits at -OFFSET
    assert beat_to_ms(2, timing) == pytest.approx(1100)
    assert beat_to_ms(4, timing) == pytest.approx(2100)   # a note on the stop beat precedes the pause
    assert beat_to_ms(6, timing) == pytest.approx(3100)   # 2000 + 500 (240 BPM) + 500 stop + 100

def test_presses_respect_threshold_and_refractory():
    ev = np.zeros((300, 4))
    ev[10:20, 0] = 1.0
    ev[40:50, 0] = 1.0   # within 60 ms of the first press: suppressed
    ev[150:160, 0] = 1.0
    ev[100:110, 2] = 0.4  # never crosses 0.5
    assert presses_from_evidence(ev, refractory=60, lag=5) == [(5, 0), (145, 0)]

def test_judge_windows_misses_and_extra_presses():
    notes = [(1000, 0), (2000, 1), (3000, 2)]
    presses = [(1010, 0), (2100, 1), (2500, 3)]
    counts, extra = judge(notes, presses)
    assert counts["Marvelous"] == 1 and counts["Good"] == 1 and counts["Miss"] == 1
    assert extra == 1
    assert itg_score(counts, 3) == pytest.approx((3 + 0 - 8) / 9)
