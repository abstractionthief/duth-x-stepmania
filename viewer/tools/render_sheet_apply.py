import mujoco
import numpy as np


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


