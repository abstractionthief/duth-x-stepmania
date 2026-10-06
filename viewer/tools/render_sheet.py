"""Render every pose in poses.py with MuJoCo into one contact sheet."""
import sys

import mujoco
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, sys.argv[1])
from poses import POSES  # noqa: E402

XML = sys.argv[2]
OUT = sys.argv[3]


def apply(m, d, pose):
    d.qpos[:] = 0
    (x, y, z), (axis, angle) = pose["root"]
    d.qpos[0:3] = (x, y, z)
    q = np.zeros(4)
    mujoco.mju_axisAngle2Quat(q, np.array(axis, float), angle)
    d.qpos[3:7] = q
    for name, value in pose["joints"].items():
        j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, name)
        if j < 0:
            raise KeyError(name)
        lo, hi = m.jnt_range[j]
        d.qpos[m.jnt_qposadr[j]] = np.clip(value, lo, hi)
    mujoco.mj_kinematics(m, d)


def main():
    m = mujoco.MjModel.from_xml_path(XML)
    d = mujoco.MjData(m)
    r = mujoco.Renderer(m, 300, 400)
    tiles = []
    for name, pose in POSES.items():
        apply(m, d, pose)
        cam = mujoco.MjvCamera()
        cam.lookat[:] = [0, 0, 0.15]
        cam.distance, cam.azimuth, cam.elevation = 1.1, 150, -18
        r.update_scene(d, cam)
        img = Image.fromarray(r.render())
        ImageDraw.Draw(img).text((8, 8), name, fill=(255, 255, 255))
        tiles.append(img)
    cols = 4
    sheet = Image.new("RGB", (400 * cols, 300 * ((len(tiles) + cols - 1) // cols)))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 400, (i // cols) * 300))
    sheet.save(OUT)
    left = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "tibia_T1_left")
    apply(m, d, POSES["rest"])
    print("left tibia y:", round(float(d.xpos[left][1]), 3), "(positive => fly's left is +y)")


main()
