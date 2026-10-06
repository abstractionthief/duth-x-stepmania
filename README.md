# duth-x-stepmania

A fruit fly's looming-escape circuit, taken from the MaleCNS connectome, as
StepMania's second player. Each arrow becomes a threat approaching from one
direction; a fixed readout of the circuit's descending neurons decides which
arrow to press. A 3D fly reacts next to the game, and a "fly's-eye view"
shows the threat, the detectors it excites and the readout.

The science lives in
[Drosophila Under the Hood](https://github.com/abstractionthief/drosophila-under-the-hood)
(`experiments/escape_code`): the dorsoventral wiring gradient, decoding with
controls (degree-preserving rewiring, hemisphere-preserving rewiring, shuffled
detector positions), a sensitivity analysis and a whole-brain test. This
repository consumes its exported model, `model/escape_model.json` (766
neurons, 327 kB). It needs no connectome, R or neuPrint token.

**What this is not:** a fly playing StepMania. The arrow → threat mapping is
hand-made, threats are injected straight into the looming detectors (there is
no vision), and model time is not biological time. What it shows is that the
wiring contains a direction code that a fixed rule can read, and that rewired
copies of the same circuit don't.

## Run

```sh
uv sync
uv run python play.py                        # OutFox's sample chart (default path on macOS)
uv run python play.py some_chart.sm          # any .sm file's dance-single charts
uv run python play.py --bpm-sweep            # 16th-note streams at rising BPM
uv run pytest
cd viewer && python3 -m http.server 8766     # open http://localhost:8766/viewer.html
```

## Results on OutFox's sample chart (`results/`)

| Chart | Notes | Circuit: hits / ITG score / false presses | Rewired circuit (3×): hits / score |
|---|---|---|---|
| Beginner (1) | 5 | 100% / 100% / 0 | 47% / −118% |
| Easy (2) | 9 | 100% / 100% / 0 | 37% / −156% |
| Medium (4) | 17 | 100% / 100% / 0 | 41% / −152% |
| Hard (6), 16 holds | 25 | 84% / 41% / 0 | 35% / −166% |
| Challenge (10) | 61 | 93% / 75% / 0 | 45% / −123% |
| Edit (13) | 152 | 97% / 88% / 0 | 40% / −147% |

Misses in Hard and Challenge are jumps of opposite arrows (← + → or ↑ + ↓),
which cancel in a difference readout. Timing grades are easy by
construction: each threat collides on its note and the offset is
calibrated. Hold and roll heads count as taps; no key is held. Streams stay
clean up to about 250 BPM in model units (60 model-ms between notes, ~6τ).

## Playing against it in OutFox (in progress)

- `outfox/FlyClock/`: an OutFox theme that inherits the default theme and
  writes the song clock and judgments to `Save/flyclock/` (macOS:
  `~/Library/Preferences/Project OutFox/flyclock/`). Link the folder into
  OutFox's user `Themes/` directory and select it in the options.
- `outfox/clock_probe.py`: reads that clock and reports sync jitter.
- `outfox/inject_keys.py`: checks that synthetic key presses reach OutFox
  (`uv run --extra live …`; needs macOS Accessibility permission and OutFox
  focused).

Next: a conductor that schedules the circuit's Player 2 presses on the game
clock and streams events to the viewer.

## Licences

Code: MIT (see `LICENSE`). Connectome data: MaleCNS v1.0, CC-BY 4.0
(Berg et al., *Cell* 2026, doi:10.1016/j.cell.2026.08.015). 3D fly: flybody
(Vaxenburg et al., Google DeepMind & HHMI Janelia), Apache-2.0
(`viewer/FLYBODY_LICENSE`). Arrow texture: StepMania 5 default noteskin, under
StepMania's permissive licence, which does not name artwork explicitly (see
`viewer/README.md`).
