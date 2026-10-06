"""Export flybody for the browser: decimated meshes, colours, and every pose's
per-part world transform (computed by MuJoCo kinematics)."""
import base64, json, sys
import fast_simplification
import mujoco
import numpy as np
from poses import POSES
from render_sheet_apply import apply

XML, OUT, KEEP = sys.argv[1], sys.argv[2], float(sys.argv[3])
m = mujoco.MjModel.from_xml_path(XML)
d = mujoco.MjData(m)
b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()

meshes = []
for i in range(m.nmesh):
    v = m.mesh_vert[m.mesh_vertadr[i]:m.mesh_vertadr[i] + m.mesh_vertnum[i]].astype(np.float32)
    f = m.mesh_face[m.mesh_faceadr[i]:m.mesh_faceadr[i] + m.mesh_facenum[i]].astype(np.int32)
    # MuJoCo stores a separate vertex per triangle corner; weld shared corners
    # first, otherwise decimation sees disconnected triangles and shreds the mesh.
    v, inverse = np.unique(np.round(v, 7), axis=0, return_inverse=True)
    f = inverse.reshape(-1)[f].astype(np.int32)
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    if f.shape[0] > 400:
        v, f = fast_simplification.simplify(v.astype(np.float32), f, target_reduction=1 - KEEP)
    meshes.append({"name": mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_MESH, i),
                   "positions": b64(v.astype(np.float32)), "indices": b64(f.astype(np.uint32))})

geoms = [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH]
def rgba(g):
    mat = m.geom_matid[g]
    return (m.mat_rgba[mat] if mat >= 0 else m.geom_rgba[g]).round(3).tolist()

root_body = int(m.jnt_bodyid[0])  # body carrying the free joint (thorax)
poses, roots = {}, {}
for name, pose in POSES.items():
    apply(m, d, pose)
    roots[name] = np.round(np.concatenate([d.xpos[root_body], d.xquat[root_body]]), 5).tolist()
    rows = []
    for g in geoms:
        q = np.zeros(4); mujoco.mju_mat2Quat(q, d.geom_xmat[g])
        rows.append(np.round(np.concatenate([d.geom_xpos[g], q]), 5).tolist())
    poses[name] = rows

payload = {"source": "flybody (Vaxenburg et al.), Apache-2.0, via MuJoCo Menagerie; meshes decimated",
           "units": "cm, z up, fly's left = +y", "meshes": meshes,
           "geoms": [{"mesh": int(m.geom_dataid[g]), "rgba": rgba(g)} for g in geoms], "poses": poses, "roots": roots}
open(OUT, "w").write(json.dumps(payload, separators=(",", ":")))
tri = sum(len(base64.b64decode(x["indices"])) // 12 for x in meshes)
print(f"{len(meshes)} meshes, {tri:,} triangles, {len(geoms)} parts, {len(poses)} poses -> {OUT}")
