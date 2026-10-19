"""Builds one fish species procedurally: mesh, textures, swim rig and animation.

Exports <out_dir>/<species>.glb and, unless --no-render, preview renders.

Usage (Blender's Python with the bpy module):
    python tools/blender/fish.py <species> <out_dir> [--no-render]

Species: kohaku, tancho, showa, chagoi, ogon, goldfish
"""
import math
import os
import sys

import numpy as np
import bpy
import bmesh
from mathutils import Matrix, Vector

SPECIES_NAME = sys.argv[1]
OUT = sys.argv[2]
RENDER = "--no-render" not in sys.argv
os.makedirs(f"{OUT}/tex", exist_ok=True)
F32 = np.float32

# ================================================================ species
KOI = dict(
    length=1.9, h_top=0.36, h_bot=0.31, w_max=0.25, barbels=True, lips=1.0,
    eye_r=0.042, eye_s=0.115, scales_u=64, tail="koi", tail_len=0.81, dorsal_h=1.0,
    iris=(0.80, 0.82, 0.83), iris_metal=0.45,
)
GOLDFISH = dict(
    length=1.45, h_top=0.40, h_bot=0.35, w_max=0.24, barbels=False, lips=0.45,
    eye_r=0.05, eye_s=0.13, scales_u=40, tail="comet", tail_len=1.15, dorsal_h=1.35,
    iris=(0.86, 0.66, 0.24), iris_metal=0.35,
)
SPECIES = {
    "kohaku": dict(KOI, skin="kohaku"),
    "tancho": dict(KOI, skin="tancho"),
    "showa": dict(KOI, skin="showa"),
    "chagoi": dict(KOI, skin="chagoi"),
    "ogon": dict(KOI, skin="ogon"),
    "goldfish": dict(GOLDFISH, skin="goldfish"),
}
SP = SPECIES[SPECIES_NAME]
SKIN = SP["skin"]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ================================================================ body shape
NOSE_X, LEN = 1.0, SP["length"]
TAIL_X = NOSE_X - LEN


def sstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def gauss(s, m, w):
    return math.exp(-((s - m) / w) ** 2)


def prof(s):
    """(top half-height, belly half-height, half-width) at s (0 nose .. 1 tail base)."""
    if s < 0.35:
        x = s / 0.35
        g = 0.04 + 0.96 * (x * (2 - x)) ** 0.75
        gb, q = g, 0.0
    else:
        q = (s - 0.35) / 0.65
        g = 1 - 0.80 * q ** 1.5
        gb = 1 - 0.80 * q ** 1.25
    ht = SP["h_top"] * g * (1 + 0.05 * gauss(s, 0.33, 0.15))              # shoulder hump
    hb = SP["h_bot"] * gb                                                 # fuller belly
    w = SP["w_max"] * g * (1 - 0.30 * q * q) * (1 + 0.05 * gauss(s, 0.15, 0.05))  # cheek bulge
    if s < 0.22:
        w *= 1 - 0.22 * (1 - s / 0.22) ** 2                               # narrower snout
    return ht, hb, w


def zc(s):
    return 0.015 * math.sin(math.pi * s) - 0.03 * (1 - s) ** 8


def surf(s, th):
    ht, hb, w = prof(s)
    c, sn = math.cos(th), math.sin(th)
    h = hb + (ht - hb) * sstep(-0.5, 0.5, sn)
    return Vector((NOSE_X - LEN * s, w * math.copysign(abs(c) ** 0.9, c), h * sn + zc(s)))


def mouth_offset(s, th):
    """Radial offset that shapes the lips: a groove between a fuller upper and lower lip."""
    mv = abs(((th / (2 * math.pi)) % 1.0) - 0.75)
    win = sstep(0.19, 0.12, mv)
    if win == 0.0 or s > 0.10:
        return 0.0
    cu = 0.012 + 0.022 * (mv / 0.13) ** 2
    groove = -0.013 * math.exp(-((s - cu) / 0.005) ** 2)
    lips = 0.011 * math.exp(-((s - cu + 0.010) / 0.008) ** 2) + 0.009 * math.exp(-((s - cu - 0.011) / 0.008) ** 2)
    return (groove + lips) * win * SP["lips"]


def surf_m(s, th):
    p = surf(s, th)
    d = mouth_offset(s, th)
    if d == 0.0:
        return p
    return p + Vector((0.6, p.y, p.z - zc(s))).normalized() * d


def x_to_s(x):
    return (NOSE_X - x) / LEN


def z_top(x):
    return surf(x_to_s(x), math.pi / 2).z


def z_bot(x):
    return surf(x_to_s(x), 3 * math.pi / 2).z


def to_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


NS_HEAD, NS_BODY, NR = 45, 100, 64
NS = NS_HEAD + NS_BODY
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
S_OF = [0.09 * (k / (NS_HEAD - 1)) ** 1.3 for k in range(NS_HEAD)] + [0.09 + 0.91 * (k + 1) / NS_BODY for k in range(NS_BODY)]
rings = [[bm.verts.new(surf_m(S_OF[i], 2 * math.pi * j / NR)) for j in range(NR)] for i in range(NS)]
nose = bm.verts.new((NOSE_X + 0.004, 0, zc(0)))
tailv = bm.verts.new((TAIL_X - 0.015, 0, zc(1)))
for i in range(NS - 1):
    for j in range(NR):
        j2 = (j + 1) % NR
        f = bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][j2], rings[i][j2]))
        for loop, (a, b) in zip(f.loops, [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]):
            loop[uvl].uv = (S_OF[a], b / NR)
for j in range(NR):
    j2 = (j + 1) % NR
    f = bm.faces.new((nose, rings[0][j], rings[0][j2]))
    for loop, uv in zip(f.loops, [(0.0, (j + 0.5) / NR), (0.0, j / NR), (0.0, (j + 1) / NR)]):
        loop[uvl].uv = uv
    f = bm.faces.new((tailv, rings[-1][j2], rings[-1][j]))
    for loop, uv in zip(f.loops, [(1.0, (j + 0.5) / NR), (1.0, (j + 1) / NR), (1.0, j / NR)]):
        loop[uvl].uv = uv
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
body = to_obj("Body", bm)
body.modifiers.new("sub", "SUBSURF").levels = 1

# ================================================================ fins


def chaikin(pts, it=4):
    pts = [Vector(p) for p in pts]
    for _ in range(it):
        nxt = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            nxt += [p.lerp(q, 0.25), p.lerp(q, 0.75)]
        pts = nxt
    return pts


def fin(name, outline, to3d, group=None, pleat_amp=0.006, pleat_n=16):
    """outline: closed (a, b) list; a along the base, b outward. to3d(a, b, bn) -> Vector (bn = b / max b)."""
    pts = chaikin(outline)
    amin = min(p.x for p in pts)
    amax = max(p.x for p in pts)
    bmax = max(p.y for p in pts)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    face = bm.faces.new([bm.verts.new((p.x, p.y, 0)) for p in pts])
    bmesh.ops.triangulate(bm, faces=[face], quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    for f in bm.faces:
        for loop in f.loops:
            a, b = loop.vert.co.x, loop.vert.co.y
            loop[uvl].uv = (max(b, 0.0) / bmax, (a - amin) / (amax - amin))
    for v in bm.verts:
        a, b = v.co.x, v.co.y
        bn = max(b, 0.0) / bmax
        p0 = to3d(a, b, bn)
        n = (to3d(a + 1e-3, b, bn) - p0).cross(to3d(a, b + 1e-3, bn) - p0).normalized()
        pleat = pleat_amp * bn ** 0.7 * math.sin(2 * math.pi * pleat_n * (a - amin) / (amax - amin))
        v.co = p0 + n * pleat
    ob = to_obj(name, bm)
    if group:
        ob.vertex_groups.new(name=group).add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
    return ob


TAIL_OUTLINES = {
    # (a = height along the tail base, b = distance behind the tail base)
    "koi": [(0.07, 0.0), (0.20, 0.20), (0.40, 0.52), (0.52, 0.78), (0.40, 0.81), (0.18, 0.62), (0.02, 0.48),
            (-0.16, 0.62), (-0.38, 0.81), (-0.50, 0.78), (-0.38, 0.52), (-0.18, 0.20), (-0.07, 0.0)],
    # comet goldfish: long, deeply forked lobes
    "comet": [(0.07, 0.0), (0.18, 0.25), (0.36, 0.70), (0.46, 1.10), (0.36, 1.15), (0.16, 0.80), (0.02, 0.52),
              (-0.14, 0.80), (-0.34, 1.15), (-0.44, 1.10), (-0.34, 0.70), (-0.16, 0.25), (-0.07, 0.0)],
}
DORSAL_X = NOSE_X - LEN * 0.42
DORSAL_LEN = LEN * 0.48
ANAL_X = NOSE_X - LEN * 0.775
dh = SP["dorsal_h"]

fins = [
    fin("Caudal", TAIL_OUTLINES[SP["tail"]],
        lambda a, b, bn: Vector((TAIL_X + 0.04 - b, 0.035 * bn * bn * abs(a) / 0.5 + 0.006 * math.sin(16 * a + 5 * b), a + zc(1)))),
    fin("Dorsal", [(0.0, -0.03), (0.05 * DORSAL_LEN / 0.92, 0.22 * dh), (0.16 * DORSAL_LEN / 0.92, 0.24 * dh),
                   (0.45 * DORSAL_LEN / 0.92, 0.17 * dh), (0.80 * DORSAL_LEN / 0.92, 0.08 * dh), (DORSAL_LEN, 0.0), (DORSAL_LEN, -0.03)],
        lambda a, b, bn: Vector((DORSAL_X - a, 0.007 * math.sin(24 * a) * bn, z_top(DORSAL_X - a) - 0.02 + b))),
    fin("Anal", [(0.0, -0.02), (0.03, 0.12), (0.12, 0.13), (0.22, 0.03), (0.24, -0.02)],
        lambda a, b, bn: Vector((ANAL_X - a, 0.005 * math.sin(30 * a) * bn, z_bot(ANAL_X - a) + 0.02 - b))),
]
for side in (1, -1):
    for name, s, th, out_dir, scale, grp in (("Pectoral", 0.27, -0.65, (-0.60, 0.65, -0.45), 1.0, "PecL" if side > 0 else "PecR"),
                                            ("Pelvic", 0.55, -1.25, (-0.65, 0.45, -0.60), 0.62, None)):
        t = th if side > 0 else math.pi - th
        o = surf(s, t)
        o = o - Vector((0, o.y, o.z - zc(s))).normalized() * 0.02
        A = Vector((-1, 0, 0))
        B = Vector((out_dir[0], out_dir[1] * side, out_dir[2])).normalized()
        N = A.cross(B).normalized()
        if N.z > 0:
            N = -N
        outline = [(0.0, 0.0), (0.08, 0.0), (0.13, 0.10), (0.14, 0.22), (0.08, 0.31), (0.0, 0.32), (-0.05, 0.22), (-0.04, 0.04)]
        outline = [(a * scale, b * scale) for a, b in outline]
        fins.append(fin(f"{name}{side}", outline,
                        lambda a, b, bn, o=o, A=A, B=B, N=N, sc=scale: o + A * a + B * b + N * (0.045 * sc * bn * bn), grp,
                        pleat_amp=0.0018, pleat_n=9))

# ================================================================ barbels, eyes


def oriented(bm, center, direction):
    rot = Vector((0, 0, 1)).rotation_difference(direction).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(center) @ rot, verts=bm.verts)


def set_uv(bm, uv):
    layer = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for loop in f.loops:
            loop[layer].uv = uv


def tube(name, base, direction, length, r0, droop):
    """Soft tapered barbel with a rounded tip, drooping as it extends."""
    bm = bmesh.new()
    rings = []
    d = direction.normalized()
    side = d.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(d).normalized()
    for i in range(13):
        t = i / 12
        c = base + d * length * t + Vector((0, 0, -droop * t * t))
        r = r0 * (1 - 0.5 * t) * (math.sqrt(max(0.0, 1 - ((t - 0.88) / 0.12) ** 2)) if t > 0.88 else 1.0) + 1e-4
        rings.append([bm.verts.new(c + r * (math.cos(2 * math.pi * k / 8) * side + math.sin(2 * math.pi * k / 8) * up)) for k in range(8)])
    for i in range(12):
        for k in range(8):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % 8], rings[i][(k + 1) % 8]))
    bmesh.ops.contextual_create(bm, geom=rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    set_uv(bm, (0.012, 0.80))
    return to_obj(name, bm)


barbels, eyes = [], []
EYE_S, EYE_R = SP["eye_s"], SP["eye_r"]
for side in (1, -1):
    if SP["barbels"]:
        corner = surf_m(0.034, 2 * math.pi * (0.88 if side > 0 else 0.62))
        upper = surf_m(0.014, 2 * math.pi * (0.83 if side > 0 else 0.67))
        barbels.append(tube("BarbelLow", corner, Vector((0.60, 0.32 * side, -0.55)), 0.068, 0.0058, 0.045))
        barbels.append(tube("BarbelUp", upper, Vector((0.8, 0.45 * side, -0.3)), 0.03, 0.0038, 0.016))
    th = 0.42 if side > 0 else math.pi - 0.42
    p = surf(EYE_S, th)
    n = (Vector((0, p.y, p.z - zc(EYE_S))).normalized() + Vector((0.12, 0, 0))).normalized()
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=EYE_R, calc_uvs=True)
    oriented(bm, p - n * EYE_R * 0.405, n)
    eyes.append(to_obj("Eye", bm))

# ================================================================ texture helpers


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def vnoise(u, v, fu, fv, seed):
    lat = np.random.default_rng(seed).random((fv, fu)).astype(F32)
    x, y = u * fu, v * fv
    x0, y0 = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
    fx, fy = x - x0, y - y0
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = lat[y0 % fv, x0 % fu]
    b = lat[y0 % fv, (x0 + 1) % fu]
    c = lat[(y0 + 1) % fv, x0 % fu]
    d = lat[(y0 + 1) % fv, (x0 + 1) % fu]
    return ((a * (1 - sx) + b * sx) * (1 - sy) + (c * (1 - sx) + d * sx) * sy).astype(F32)


def fbm(u, v, fu, fv, seed, octaves=5):
    tot = np.zeros_like(u)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        tot += amp * vnoise(u, v, fu * 2 ** o, fv * 2 ** o, seed + o)
        norm += amp
        amp *= 0.5
    return tot / norm


def save(name, rgba, non_color=False):
    h, w, _ = rgba.shape
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=F32).ravel())
    img.filepath_raw = f"{OUT}/tex/{name}.png"
    img.file_format = "PNG"
    img.save()
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def rgba(rgb, a=None):
    a = np.ones(rgb.shape[:2], F32) if a is None else a
    return np.concatenate([rgb, a[..., None]], -1)


def mix(base, color, amount):
    """Blend an image toward a colour (or another image) by a per-pixel amount."""
    amount = amount[..., None]
    return base * (1 - amount) + np.asarray(color, F32) * amount


# ================================================================ body texture
TW, TH = 4096, 2048
u, v = np.meshgrid(np.linspace(0, 1, TW, dtype=F32), (np.arange(TH, dtype=F32) + 0.5) / TH)
theta = 2 * np.pi * v
lift, side = np.sin(theta), np.abs(np.cos(theta))
dorsal = np.clip(1 - np.abs(v - 0.25) / 0.27, 0, 1)
circ_head = 2 * np.pi * 0.2

# scales: overlapping rounded scales. The scale in front (toward the head) lies on top.
NU, NV, R = SP["scales_u"], 64, 0.90
cu = u * NU
yv = v * NV + 0.30 * cu
c0 = np.floor(cu).astype(np.int32)
rnd = np.random.default_rng(3).random((NV, NU + 3)).astype(F32)


def layer(k):
    cc = c0 + k
    off = 0.5 * (cc % 2)
    r = np.floor(yv + off).astype(np.int32)
    dy = yv - (r + 0.5 - off)
    jx = rnd[r % NV, np.clip(cc, 0, NU + 2)] - 0.5
    dx = cu - (cc + 0.35 + 0.06 * jx)
    return cc, r % NV, dx, dy, np.sqrt(dx * dx + dy * dy)


Lm, L0, Lp = layer(-1), layer(0), layer(1)
in_m = Lm[4] < R
in_0 = (~in_m) & (L0[4] < R)


def pick(i):
    return np.where(in_m, Lm[i], np.where(in_0, L0[i], Lp[i]))


own_c, own_r, dx, dy, dist = (pick(i) for i in range(5))
own_c = np.clip(own_c, 0, NU + 1)
edge_gap = np.where(in_m, 9.0, np.where(in_0, Lm[4] - R, np.minimum(L0[4] - R, Lm[4] - R)))
del Lm, L0, Lp, in_m, in_0
rn = dist / R
jit = rnd[own_r, own_c]
scale_zone = smoothstep(0.20, 0.28, u) * smoothstep(0.985, 0.93, u)
rim = smoothstep(0.82, 0.93, rn) * smoothstep(1.0, 0.95, rn) * scale_zone
pocket = smoothstep(0.10, 0.0, edge_gap) * scale_zone
mott = fbm(u, v, 14, 10, 61, 4)


def pattern(field, threshold, soft_front=True):
    """Pigment mask from a noise field: a smooth outline scalloped along the scale edges,
    crisp at the back edge and faintly blurred at the front edge (as on real koi)."""
    crisp = smoothstep(threshold - 0.004, threshold + 0.004, field + 0.035 * (0.55 - np.clip(rn, 0, 1.2)) * scale_zone)
    if not soft_front:
        return crisp
    dfdu = np.gradient(field, axis=1)
    soft = (dfdu > 0) * (1 - crisp) * smoothstep(threshold - 0.045, threshold, field) * 0.4 * scale_zone
    return np.clip(crisp + soft, 0, 1)


def snow_white():
    w = np.stack([0.94 + 0.02 * (1 - dorsal), 0.925 + 0.03 * (1 - dorsal), 0.885 + 0.05 * (1 - dorsal)], -1).astype(F32)
    blush = smoothstep(0.23, 0.02, u) * smoothstep(0.3, -0.6, lift) * 0.35
    return mix(w, (0.96, 0.76, 0.72), blush)


def hi_red(depth):
    red = np.stack([0.66 + 0.10 * depth, 0.10 - 0.04 * depth, 0.035 - 0.01 * depth], -1).astype(F32)
    red *= ((0.92 + 0.12 * jit) * (0.84 + 0.30 * mott))[..., None]
    red[..., 1] += 0.06 * (mott - 0.4)
    return red


def koi_red_field():
    return fbm(u, v, 5, 6, 11) + 0.42 * dorsal - 0.60 * smoothstep(0.11, 0.0, u) - 0.25 * smoothstep(0.82, 0.97, u)


def paint():
    """Returns (albedo, white_amount, rim_color, rim_strength, scale_relief) for the species' skin."""
    if SKIN in ("kohaku", "tancho", "showa"):
        albedo = snow_white()
        if SKIN == "tancho":
            dist_c = np.sqrt(((u - 0.13) * LEN) ** 2 + ((v - 0.25) * circ_head) ** 2)
            red_amt = smoothstep(0.080, 0.072, dist_c)
            depth = np.full_like(u, 0.6)
        else:
            field = koi_red_field() + (0.06 if SKIN == "showa" else 0.0)
            red_amt = pattern(field, 0.74) * smoothstep(0.05, 0.13, u)
            depth = np.clip((field - 0.74) / 0.15, 0, 1)
        albedo = mix(albedo, hi_red(depth), red_amt)
        white_amt = 1 - red_amt
        if SKIN == "showa":
            # sumi: black wraps around the body (belly too) and reaches onto the face
            sumi_f = fbm(u, v, 4, 5, 81) + 0.10 * np.sin(theta * 2 + u * 9)
            black = pattern(sumi_f, 0.56, soft_front=False) * smoothstep(0.03, 0.10, u)
            black_col = np.array([0.035, 0.035, 0.04], F32) * (0.85 + 0.3 * mott)[..., None]
            albedo = mix(albedo, black_col, black)
            white_amt = white_amt * (1 - black)
        return albedo, white_amt, (0.82, 0.24, 0.08), 0.12 * (1 - white_amt), 0.45
    if SKIN == "chagoi":
        belly = smoothstep(0.1, -0.7, lift)
        base = np.stack([0.42 + 0.06 * mott, 0.27 + 0.04 * mott, 0.13 + 0.02 * mott], -1).astype(F32)
        albedo = mix(base, (0.66, 0.52, 0.33), belly * 0.7)
        albedo *= (0.94 + 0.10 * jit)[..., None]
        return albedo, np.zeros_like(u), (0.16, 0.09, 0.04), 0.55 * np.ones_like(u), 0.55
    if SKIN == "ogon":
        base = np.stack([0.84 + 0.04 * mott, 0.85 + 0.04 * mott, 0.84 + 0.03 * mott], -1).astype(F32)
        albedo = base * (0.95 + 0.08 * jit)[..., None]
        return albedo, np.zeros_like(u), (1.0, 1.0, 0.98), 0.35 * np.ones_like(u), 0.55
    if SKIN == "goldfish":
        belly = smoothstep(0.2, -0.7, lift)
        base = np.stack([0.95 * (0.9 + 0.15 * mott), 0.36 + 0.10 * mott, 0.05 + 0.02 * mott], -1).astype(F32)
        albedo = mix(base, (0.98, 0.66, 0.28), belly * 0.6)
        albedo *= (0.93 + 0.12 * jit)[..., None]
        return albedo, np.zeros_like(u), (1.0, 0.72, 0.30), 0.30 * np.ones_like(u), 0.40
    raise ValueError(f"unknown skin {SKIN}")


albedo, white_amt, rim_col, rim_strength, relief = paint()
# scale shading: light rim on the free edge, shadow pocket where the next scale starts,
# cool blue-grey in the shadows of white skin (pearly look)
albedo *= (1 + 0.03 * rim - 0.02 * pocket + 0.03 * (jit - 0.5) * scale_zone)[..., None]
cool = (pocket * 0.10 + 0.03 * scale_zone) * white_amt
albedo = mix(albedo, (0.70, 0.78, 0.88), cool)
albedo = mix(albedo, rim_col, rim * rim_strength)
if SKIN == "chagoi":
    albedo = mix(albedo, (0.12, 0.07, 0.03), pocket * 0.5)   # dark net between scales

# head: gill plate edge, eye sockets, nostrils, lips
gill_u = 0.20 - 0.035 * (lift + 0.2) ** 2
gill = smoothstep(0.006, 0.0, np.abs(u - gill_u)) * smoothstep(0.35, 0.15, lift) * smoothstep(-0.85, -0.6, lift) * smoothstep(0.4, 0.7, side)
skin_s = fbm(u, v, 400, 200, 71, 2)
height = np.zeros((TH, TW), F32)
er = EYE_R / 0.042
for ve in (0.42 / (2 * np.pi), (np.pi - 0.42) / (2 * np.pi)):
    de = np.sqrt(((u - EYE_S) * LEN) ** 2 + ((v - ve) * circ_head) ** 2)
    socket = smoothstep(0.068 * er, 0.050 * er, de) * smoothstep(0.040 * er, 0.050 * er, de)
    contact = smoothstep(0.047 * er, 0.040 * er, de)
    albedo *= (1 - 0.14 * socket * (0.5 + skin_s) - 0.30 * contact)[..., None]
    height += 0.3 * socket
for vn in (0.30 / (2 * np.pi), (np.pi - 0.30) / (2 * np.pi)):
    dn = np.sqrt(((u - 0.055) * LEN) ** 2 + ((v - vn) * 2 * np.pi * 0.12) ** 2)
    nostril = smoothstep(0.011, 0.005, dn)
    nrim = smoothstep(0.017, 0.013, dn) * smoothstep(0.009, 0.013, dn)
    albedo = mix(albedo, (0.30, 0.22, 0.21), 0.7 * nostril)
    height += 0.3 * nrim - 0.9 * nostril
albedo *= (1 - 0.07 * gill)[..., None]
mv = np.abs(v - 0.75)
lip = smoothstep(0.058, 0.025, u) * smoothstep(0.22, 0.13, mv)
albedo = mix(albedo, (0.95, 0.89, 0.82), lip * (0.8 if SP["barbels"] else 0.4))
crease_u = 0.010 + 0.022 * (mv / 0.13) ** 2
crease = smoothstep(0.0028, 0.0, np.abs(u - crease_u)) * smoothstep(0.14, 0.11, mv)
albedo = mix(albedo, (0.22, 0.09, 0.08), 0.8 * crease)
height -= 0.3 * crease
skin = fbm(u, v, 300, 160, 21, 3)
height += (np.minimum(rn, 1.0) ** 2 - 0.5) * scale_zone * relief - 0.5 * gill + 0.12 * (skin - 0.5) * (1 - scale_zone)
gy, gx = np.gradient(height)
flat = smoothstep(0.015, 0.07, u)
nrm = np.stack([-gx * 9 * flat, -gy * 9 * flat, np.ones_like(gx)], -1)
nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
rough = np.clip(0.22 + 0.12 * rim + 0.2 * pocket + 0.08 * (1 - scale_zone), 0, 1)
tip_col = albedo[:, int(0.02 * TW)].mean(axis=0)
albedo = mix(albedo, tip_col, smoothstep(0.02, 0.004, u))
body_col = save(f"{SPECIES_NAME}_body_albedo", rgba(np.clip(albedo, 0, 1)))
body_nrm = save(f"{SPECIES_NAME}_body_normal", rgba(nrm * 0.5 + 0.5), True)
body_rgh = save(f"{SPECIES_NAME}_body_rough", rgba(np.repeat(rough[..., None], 3, -1)), True)
del u, v, height, nrm

# ================================================================ fin texture: membrane, branching segmented rays, ragged tips
FW = 1024
fu2, fv2 = np.meshgrid(np.linspace(0, 1, FW, dtype=F32), np.linspace(0, 1, FW, dtype=F32))
NRAY = 16


def ray_line(x, width):
    return smoothstep(width, 0.0, np.abs((x % 1.0) - 0.5))


w_ray = 0.11 * (1 - 0.45 * fu2)
warp = 0.18 * np.sin(fv2 * 9.0) + 0.10 * fbm(fv2, fu2, 6, 2, 37, 2)
rays = np.maximum(ray_line(fv2 * NRAY + warp, w_ray), ray_line((fv2 * NRAY + warp) * 2 + 0.5, w_ray) * smoothstep(0.50, 0.62, fu2))
joints = smoothstep(0.10, 0.0, np.abs(((fu2 / 0.055) % 1.0) - 0.5)) * smoothstep(0.15, 0.3, fu2)
rays_seg = rays * (1 - 0.45 * joints)
ragged = fbm(fv2, fu2, 40, 4, 31, 3)
tip = smoothstep(1.0, 0.86 - 0.08 * ragged, fu2)
fin_a = np.clip((0.24 + 0.20 * rays_seg) * (1 - 0.3 * fu2) + 0.25 * smoothstep(0.10, 0.0, fu2), 0, 1) * tip
FIN_COLORS = {   # membrane colour, colour at the fin base
    "kohaku": ((0.90, 0.91, 0.93), (0.95, 0.80, 0.76)),
    "tancho": ((0.92, 0.93, 0.94), (0.95, 0.88, 0.85)),
    "showa": ((0.90, 0.91, 0.93), (0.04, 0.04, 0.045)),
    "chagoi": ((0.55, 0.40, 0.22), (0.40, 0.26, 0.12)),
    "ogon": ((0.90, 0.90, 0.88), (0.85, 0.85, 0.82)),
    "goldfish": ((0.98, 0.50, 0.12), (0.95, 0.36, 0.06)),
}
membrane, base_col = FIN_COLORS[SKIN]
fin_rgb = np.stack([membrane[0] + 0.05 * rays_seg, membrane[1] + 0.04 * rays_seg, membrane[2] + 0.01 * rays_seg], -1).astype(F32)
base_w = smoothstep(0.30 if SKIN == "showa" else 0.15, 0.0, fu2) * (0.85 if SKIN == "showa" else 0.2)
fin_rgb = mix(fin_rgb, base_col, base_w)
if SKIN == "showa":
    fin_a = np.clip(fin_a + 0.5 * base_w, 0, 1)
fy, fx = np.gradient(rays_seg)
fn = np.stack([-fx * 3, -fy * 3, np.ones_like(fx)], -1)
fn /= np.linalg.norm(fn, axis=-1, keepdims=True)
fin_img = save(f"{SPECIES_NAME}_fin", rgba(np.clip(fin_rgb, 0, 1), fin_a))
fin_nrm = save(f"{SPECIES_NAME}_fin_normal", rgba(fn * 0.5 + 0.5), True)

# ================================================================ eye texture: pupil at the poles, metallic iris with flecks, dark rim
EW = 512
eu, ev = np.meshgrid(np.linspace(0, 1, EW, dtype=F32), np.linspace(0, 1, EW, dtype=F32))
pd = np.minimum(ev, 1 - ev)
streak = 0.85 + 0.15 * fbm(eu, ev, 64, 8, 41, 2)
iris = np.asarray(SP["iris"], F32) * (0.80 + 0.20 * streak[..., None])
dark_f = smoothstep(0.60, 0.70, fbm(eu, ev, 90, 26, 51, 3)) * smoothstep(0.14, 0.30, pd)
gold_f = smoothstep(0.64, 0.72, fbm(eu, ev, 70, 30, 57, 2)) * smoothstep(0.11, 0.15, pd)
iris = iris * (1 - 0.65 * dark_f[..., None])
iris = mix(iris, (0.86, 0.66, 0.26), 0.55 * gold_f)
iris = mix(iris, (0.07, 0.07, 0.08), smoothstep(0.33, 0.37, pd))
eye = np.where((pd < 0.12)[..., None], np.array([0.006, 0.006, 0.008], F32), iris)
inner = smoothstep(0.120, 0.130, pd) * smoothstep(0.142, 0.130, pd)
eye = mix(eye, (0.10, 0.10, 0.11), 0.6 * inner)
eye_img = save(f"{SPECIES_NAME}_eye", rgba(np.clip(eye, 0, 1)))

# ================================================================ materials
BODY_METAL = {"ogon": 0.85, "goldfish": 0.35}.get(SKIN, 0.0)


def tex_node(nt, img):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    return t


def mat_body():
    m = bpy.data.materials.new("Body")
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    nt.links.new(tex_node(nt, body_col).outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tex_node(nt, body_rgh).outputs["Color"], b.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.9
    nt.links.new(tex_node(nt, body_nrm).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = BODY_METAL
    b.inputs["Coat Weight"].default_value = 0.55
    b.inputs["Coat Roughness"].default_value = 0.04
    b.inputs["Subsurface Weight"].default_value = 0.15 * (1 - BODY_METAL)
    b.inputs["Subsurface Scale"].default_value = 0.03
    b.inputs["Subsurface Radius"].default_value = (0.6, 0.35, 0.25)
    b.inputs["Thin Film Thickness"].default_value = 320.0
    b.inputs["Thin Film IOR"].default_value = 1.38
    return m


def mat_fin():
    m = bpy.data.materials.new("Fin")
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = tex_node(nt, fin_img)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.6
    nt.links.new(tex_node(nt, fin_nrm).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.25
    b.inputs["Metallic"].default_value = BODY_METAL * 0.4
    m.surface_render_method = "BLENDED"
    m.use_backface_culling = False
    return m


def mat_eye():
    m = bpy.data.materials.new("Eye")
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    nt.links.new(tex_node(nt, eye_img).outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.2
    b.inputs["Metallic"].default_value = SP["iris_metal"]
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.01
    return m


def mat_color(name, col, rough):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    return m


BARBEL_COLORS = {"chagoi": (0.66, 0.50, 0.34, 1), "ogon": (0.88, 0.86, 0.80, 1)}
M_BODY, M_FIN, M_EYE = mat_body(), mat_fin(), mat_eye()
M_BARBEL = mat_color("Barbel", BARBEL_COLORS.get(SKIN, (0.92, 0.85, 0.78, 1)), 0.35)


def apply_all(ob):
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


assign = [(body, M_BODY)] + [(f, M_FIN) for f in fins] + [(e, M_EYE) for e in eyes] + [(b, M_BARBEL) for b in barbels]
for ob, mat in assign:
    ob.data.materials.append(mat)
    apply_all(ob)
bpy.ops.object.select_all(action="DESELECT")
for ob, _ in assign:
    ob.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
fish = body
fish.name = SPECIES_NAME
for p in fish.data.polygons:
    p.use_smooth = True

# ================================================================ rig: spine bones head to tail tip, pectoral flap bones
TAIL_TIP = TAIL_X - SP["tail_len"]
XS = list(np.linspace(NOSE_X + 0.08, TAIL_X, 7)) + [TAIL_X - SP["tail_len"] * 0.45, TAIL_TIP]
arm = bpy.data.armatures.new("Rig")
rig = bpy.data.objects.new("Rig", arm)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
prev, spine = None, []
for i in range(len(XS) - 1):
    b = arm.edit_bones.new(f"Spine{i}")
    b.head = (XS[i], 0, 0)
    b.tail = (XS[i + 1], 0, 0)
    b.roll = 0
    if prev:
        b.parent = prev
        b.use_connect = True
    prev = b
    spine.append(b)
for side, name in ((1, "PecL"), (-1, "PecR")):
    o = surf(0.27, -0.65 if side > 0 else math.pi + 0.65)
    b = arm.edit_bones.new(name)
    b.head = o
    b.tail = o + Vector((-0.6, 0.65 * side, -0.45)).normalized() * 0.25
    b.parent = spine[1]
bpy.ops.object.mode_set(mode="OBJECT")
pec_idx = set()
for g in fish.vertex_groups:
    if g.name.startswith("Pec"):
        for vtx in fish.data.vertices:
            if any(e.group == g.index for e in vtx.groups):
                pec_idx.add(vtx.index)
mids = [(XS[i] + XS[i + 1]) / 2 for i in range(len(XS) - 1)]
kernel = 0.34 * LEN / 1.9
groups = [fish.vertex_groups.new(name=f"Spine{i}") for i in range(len(mids))]
for vtx in fish.data.vertices:
    if vtx.index in pec_idx:
        continue
    ws = [max(0.0, 1 - abs(vtx.co.x - m) / kernel) for m in mids]
    if sum(ws) == 0:
        ws[0 if vtx.co.x > 0 else -1] = 1.0
    tot = sum(ws)
    for g, w in zip(groups, ws):
        if w > 0:
            g.add([vtx.index], w / tot, "REPLACE")
fish.modifiers.new("Armature", "ARMATURE").object = rig
fish.parent = rig
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions.new("swim")
FR = 24
scene.frame_start, scene.frame_end = 1, FR
amps = [0.012, 0.025, 0.045, 0.07, 0.10, 0.14, 0.19, 0.25]
for f in range(1, FR + 2):
    t = (f - 1) / FR
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        if pb.name.startswith("Spine"):
            i = int(pb.name[5:])
            pb.rotation_euler = (0, 0, amps[i] * math.sin(2 * math.pi * t - i * 0.7))
        else:
            pb.rotation_euler = (0.22 * math.sin(4 * math.pi * t + (0 if pb.name == "PecL" else math.pi)), 0, 0)
        pb.keyframe_insert("rotation_euler", frame=f)
bpy.ops.object.select_all(action="DESELECT")
fish.select_set(True)
rig.select_set(True)
bpy.ops.export_scene.gltf(filepath=f"{OUT}/{SPECIES_NAME}.glb", export_animations=True, use_selection=True)
print("EXPORTED", SPECIES_NAME, len(fish.data.vertices), "verts")
if not RENDER:
    sys.exit(0)

# ================================================================ preview renders (camera scales with the fish)
TOTAL = NOSE_X - TAIL_TIP
CX = NOSE_X - TOTAL / 2
K = TOTAL / 2.73
KH = SP["h_top"] / 0.36
EYE_P = surf(EYE_S, 0.42)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1280, 800
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
target = bpy.data.objects.new("Target", None)
scene.collection.objects.link(target)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam
tc = cam.constraints.new("TRACK_TO")
tc.target = target
tc.track_axis = "TRACK_NEGATIVE_Z"
tc.up_axis = "UP_Y"
studio = []


def area(name, loc, energy, size, color=(1, 1, 1)):
    light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    scene.collection.objects.link(light)
    light.data.energy = energy
    light.data.size = size
    light.data.color = color
    light.location = loc
    c = light.constraints.new("TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    studio.append(light)


area("Key", (2.2, -2.6, 3.0), 650, 3.0, (1.0, 0.97, 0.92))
area("Rim", (-2.8, 2.4, 1.6), 450, 2.0, (0.85, 0.92, 1.0))
area("Fill", (0.5, -4.0, 0.0), 90, 4.0)
world = bpy.data.worlds.new("W")
scene.world = world
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.008, 0.022, 0.026, 1)
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 5.6


def render(name, frame, cam_loc, tgt, lens, focus):
    scene.frame_set(frame)
    cam.location = cam_loc
    target.location = tgt
    cam.data.lens = lens
    cam.data.dof.focus_distance = (Vector(cam_loc) - Vector(focus)).length
    scene.render.filepath = f"{OUT}/{SPECIES_NAME}_{name}.png"
    bpy.ops.render.render(write_still=True)


render("closeup", 4, (CX + 1.45 * K, -2.55 * K, 0.57 * K), (CX, 0, -0.02), 50, (EYE_P.x, -0.2 * KH, 0.08))
render("head", 4, (EYE_P.x + 0.92 * KH, -0.95 * KH, 0.28), (EYE_P.x - 0.08, 0, -0.02), 60, (EYE_P.x + 0.04, -EYE_P.y, EYE_P.z))

# pond view at the game camera angle: gravel floor, tinted water, rippled surface
for light in studio:
    light.hide_render = True
bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, -0.9))
floor = bpy.context.active_object
fm = bpy.data.materials.new("Gravel")
nt = fm.node_tree
b = nt.nodes["Principled BSDF"]
edge = nt.nodes.new("ShaderNodeTexVoronoi")
edge.feature = "DISTANCE_TO_EDGE"
edge.inputs["Scale"].default_value = 260
cell = nt.nodes.new("ShaderNodeTexVoronoi")
cell.inputs["Scale"].default_value = 260
round_ = nt.nodes.new("ShaderNodeMapRange")
round_.inputs["From Max"].default_value = 0.45
round_.interpolation_type = "SMOOTHSTEP"
nt.links.new(edge.outputs["Distance"], round_.inputs["Value"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.05, 0.047, 0.04, 1)
ramp.color_ramp.elements[1].color = (0.33, 0.30, 0.24, 1)
nt.links.new(cell.outputs["Color"], ramp.inputs["Fac"])
gmix = nt.nodes.new("ShaderNodeMix")
gmix.data_type = "RGBA"
gmix.inputs["A"].default_value = (0.045, 0.04, 0.03, 1)
nt.links.new(round_.outputs["Result"], gmix.inputs["Factor"])
nt.links.new(ramp.outputs["Color"], gmix.inputs["B"])
nt.links.new(gmix.outputs["Result"], b.inputs["Base Color"])
bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Distance"].default_value = 0.008
nt.links.new(round_.outputs["Result"], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
b.inputs["Roughness"].default_value = 0.6
floor.data.materials.append(fm)
SURF_Z = 0.34
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, (SURF_Z - 0.01 - 0.92) / 2))
water = bpy.context.active_object
water.scale = (14, 14, SURF_Z - 0.01 + 0.92)
wm = bpy.data.materials.new("WaterVolume")
nt = wm.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
vol = nt.nodes.new("ShaderNodeVolumeAbsorption")
vol.inputs["Color"].default_value = (0.42, 0.70, 0.56, 1)
vol.inputs["Density"].default_value = 0.5
nt.links.new(vol.outputs["Volume"], nt.nodes["Material Output"].inputs["Volume"])
water.data.materials.append(wm)
bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, SURF_Z))
surface = bpy.context.active_object
sm = bpy.data.materials.new("WaterSurface")
nt = sm.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
glass = nt.nodes.new("ShaderNodeBsdfGlass")
glass.inputs["IOR"].default_value = 1.333
glass.inputs["Roughness"].default_value = 0.0
wn = nt.nodes.new("ShaderNodeTexNoise")
wn.inputs["Scale"].default_value = 2.5
wn.inputs["Detail"].default_value = 4
wb = nt.nodes.new("ShaderNodeBump")
wb.inputs["Strength"].default_value = 0.12
nt.links.new(wn.outputs["Fac"], wb.inputs["Height"])
nt.links.new(wb.outputs["Normal"], glass.inputs["Normal"])
nt.links.new(glass.outputs["BSDF"], nt.nodes["Material Output"].inputs["Surface"])
surface.data.materials.append(sm)
surface.visible_shadow = False
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(32), math.radians(-12), math.radians(25))
sun.data.energy = 4.0
sun.data.angle = math.radians(2)
bg.inputs["Color"].default_value = (0.55, 0.68, 0.85, 1)
scene.cycles.samples = 96
cam.data.dof.aperture_fstop = 11
render("pond", 1, (CX + 0.27 * K, -2.9 * K, 3.0 * K), (CX + 0.115 * K, 0, -0.1), 40, (CX, 0.0, 0.0))
print("DONE", SPECIES_NAME)
