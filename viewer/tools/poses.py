"""Key poses for the flybody avatar, as joint-angle overrides on the zero pose.
Root: (x, y, z) in cm and a rotation as (axis, angle). Legs: T1 front, T2 middle, T3 hind."""
import numpy as np

STAND_Z = 0.126  # feet on the floor in the zero pose

LEGS = [f"T{i}_{s}" for i in (1, 2, 3) for s in ("left", "right")]


def legs(**per_joint):
    """per_joint: {'femur': v, 'tibia': v, ...} applied to all six legs."""
    return {f"{j}_{leg}": v for leg in LEGS for j, v in per_joint.items()}


def wings(yaw=0.0, roll=0.0, pitch=0.0):
    return {"wing_yaw_left": yaw, "wing_yaw_right": -yaw, "wing_roll_left": roll, "wing_roll_right": -roll,
            "wing_pitch_left": pitch, "wing_pitch_right": pitch}


POSES = {
    "rest": {"root": ((0, 0, STAND_Z), ((0, 0, 1), 0.0)), "joints": {}},
    # DOWN: crouch / freeze low
    "crouch": {"root": ((0, 0, STAND_Z - 0.045), ((0, 1, 0), 0.12)),
               "joints": {**legs(femur=0.55, tibia=-0.55), "head": 0.25}},
    # UP: Giant Fiber-style takeoff - middle legs extend, wings up and out
    "takeoff": {"root": ((0.05, 0, STAND_Z + 0.22), ((0, 1, 0), -0.35)),
                "joints": {**legs(femur=-0.1, tibia=0.9), **wings(yaw=1.2, roll=1.2, pitch=0.6)}},
    # LEFT / RIGHT: sidestep away from the threat (sign of y decided by the left legs' side)
    "dodge_left": {"root": ((0, 0.18, STAND_Z), ((0, 0, 1), 0.45)),
                   "joints": {"coxa_abduct_T1_left": 0.5, "coxa_abduct_T2_left": 0.25, "coxa_abduct_T3_left": 0.25,
                              **wings(yaw=0.3)}},
    "dodge_right": {"root": ((0, -0.18, STAND_Z), ((0, 0, 1), -0.45)),
                    "joints": {"coxa_abduct_T1_right": 0.5, "coxa_abduct_T2_right": 0.25,
                               "coxa_abduct_T3_right": 0.25, **wings(yaw=0.3)}},
    # MISS: tossed up and rolling (midway), then flipped on its back, legs up (flail frames alternate)
    "tumble": {"root": ((0, 0, STAND_Z + 0.12), ((1, 0, 0), np.pi / 2)),
               "joints": {**legs(femur=0.7, tibia=0.2), **wings(yaw=0.9, roll=0.6)}},
    "flip_a": {"root": ((0, 0, 0.11), ((1, 0, 0), np.pi)),
               "joints": {**legs(femur=1.2, tibia=-0.9), **wings(yaw=0.6)}},
    "flip_b": {"root": ((0, 0, 0.11), ((1, 0, 0), np.pi * 0.92)),
               "joints": {**legs(femur=0.2, tibia=0.6), **wings(yaw=0.2)}},
}
