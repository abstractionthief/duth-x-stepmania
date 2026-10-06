# StepMania experiment: fly viewer

A browser view for duth-x-stepmania: a 3D fruit fly that reacts to
threats, plus a "Fly's-eye view" panel showing the looming threat, the 311
LC4/LPLC2 detectors and the circuit's four readout bars with the press
threshold θ. The fly moves only when a bar crosses θ, and flips over when the
circuit picks the wrong arrow.

```sh
cd viewer && python3 -m http.server 8766
# open http://localhost:8766/viewer.html (three.js loads from a CDN)
```

Arrow keys or the buttons send a threat. **X** plays the miss animation.
The BPM slider scales move durations; the demo stream sends one threat per
beat.

## What is real and what is illustrative

- **Readout bars and decisions** replay output of the escape model
  (`model/escape_model.json`, traces made by `tools/export_eye.py`): the real MaleCNS wiring, plus
  one degree-preserving rewired control kept in `eye.json` but not shown.
- **Detector vertical position** is each detector's estimated dendrite
  elevation. Horizontal placement within an eye is illustrative: the model
  only knows which eye sees the threat and at what elevation.
- **The arrow → movement mapping** (↑ takeoff, ↓ crouch, ←/→ sidestep) is a
  presentation choice, not the fly's measured escape repertoire.
- **Playback:** one threat at a time from precomputed traces; overlapping
  threats are not simulated.

## Fly model

[flybody](https://github.com/TuragaLab/flybody) by Vaxenburg et al.
(Google DeepMind and HHMI Janelia), Apache-2.0 (see `FLYBODY_LICENSE`), taken
from [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie/tree/main/flybody).
`fly.json` holds its meshes, welded and decimated to about 8% (25k
triangles). Each pose is the body's (thorax) transform plus every part's
transform relative to the body, both computed by MuJoCo forward kinematics
from joint angles in `tools/poses.py`.

## Arrow texture

`assets/stepmania5_arrow_1x8.png` is the default dance noteskin arrow from
[StepMania 5](https://github.com/stepmania/stepmania/tree/5_1-new/NoteSkins/dance/default)
(the same look OutFox uses; OutFox's own copy differs slightly and is not
used). StepMania's licence (`Docs/Licenses.txt` in that repository) is a
permissive MIT-style notice for the software and associated files; it does
not name artwork explicitly, so confirm before a commercial use.

## Regenerate

```sh
# flybody meshes (137 MB) - only the flybody folder of MuJoCo Menagerie
git clone --depth 1 --filter=blob:none --sparse https://github.com/google-deepmind/mujoco_menagerie /tmp/menagerie
git -C /tmp/menagerie sparse-checkout set flybody

cd viewer/tools
uv run --with mujoco --with fast-simplification python export_web.py /tmp/menagerie/flybody/fruitfly.xml ../fly.json 0.08
uv run --with mujoco --with pillow python render_sheet.py . /tmp/menagerie/flybody/scene.xml /tmp/poses.png  # pose check

cd ../..   # repository root
uv run python viewer/tools/export_eye.py viewer/eye.json
```
