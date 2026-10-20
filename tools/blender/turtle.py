"""Builds a red-eared slider turtle procedurally: shell with scutes, striped head and legs, swim rig.

Exports <out_dir>/<variant>.glb and, unless --no-render, preview renders.

Usage (Blender's Python with the bpy module):
    python tools/blender/turtle.py <variant> <out_dir> [--no-render]

Variants: slider, slider_albino
"""
import math
import os
import sys

import numpy as np
import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preview import Previewer  # noqa: E402

VARIANT = sys.argv[1]
OUT = sys.argv[2]
RENDER = "--no-render" not in sys.argv
os.makedirs(f"{OUT}/tex", exist_ok=True)
F32 = np.float32

COLORS = {
    "slider": dict(
        shell=(0.11, 0.14, 0.06), shell_mark=(0.78, 0.72, 0.22), seam=(0.06, 0.07, 0.03),
        plastron=(0.86, 0.78, 0.36), plastron_spot=(0.18, 0.17, 0.08),
        skin=(0.18, 0.25, 0.10), stripe=(0.86, 0.80, 0.28), ear=(0.82, 0.10, 0.05),
        iris=(0.72, 0.70, 0.26), pupil=(0.02, 0.02, 0.02), claw=(0.10, 0.09, 0.07, 1),
    ),
    "slider_albino": dict(
        shell=(0.86, 0.72, 0.30), shell_mark=(1.0, 0.58, 0.16), seam=(0.55, 0.42, 0.16),
        plastron=(0.96, 0.90, 0.62), plastron_spot=None,
        skin=(0.97, 0.90, 0.62), stripe=(1.0, 0.78, 0.20), ear=(1.0, 0.32, 0.12),
        iris=(0.78, 0.16, 0.12), pupil=(0.30, 0.02, 0.02), claw=(0.85, 0.80, 0.62, 1),
    ),
}
C = COLORS[VARIANT]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

A, B, HS = 0.62, 0.50, 0.30   # shell half-length, half-width, dome height; the turtle faces +x
RIM_Z = -0.02


def sstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def to_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


def whole_group(ob, name):
    ob.vertex_groups.new(name=name).add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")


# ================================================================ shell: domed carapace on top, flatter plastron below


def shell_xy(r, phi):
    return A * r * math.cos(phi), B * r * math.sin(phi) * (1 - 0.07 * math.cos(phi))   # a little wider at the back


def top_z(r, phi):
    _, y = shell_xy(r, phi)
    keel = 0.025 * math.exp(-(y / 0.08) ** 2) * (1 - r)
    return HS * max(0.0, 1 - r * r) ** 0.55 + keel + RIM_Z * r ** 8


def bot_z(r):
    return RIM_Z - 0.10 * max(0.0, 1 - r ** 6) ** 0.5


NRr, NP = 40, 96
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")


def shell_uv(co):
    return (co.x / (2 * A) + 0.5, co.y / (2 * B) + 0.5)


top = [[bm.verts.new((*shell_xy(i / NRr, 2 * math.pi * j / NP), top_z(i / NRr, 2 * math.pi * j / NP))) for j in range(NP)] for i in range(1, NRr + 1)]
bot = [[bm.verts.new((*shell_xy(i / NRr, 2 * math.pi * j / NP), bot_z(i / NRr))) for j in range(NP)] for i in range(1, NRr)]
bot.append(top[-1])   # shared rim ring
top_pole = bm.verts.new((0, 0, top_z(0, 0)))
bot_pole = bm.verts.new((0, 0, bot_z(0)))


def add_face(verts, mat):
    f = bm.faces.new(verts)
    f.material_index = mat
    for loop in f.loops:
        loop[uvl].uv = shell_uv(loop.vert.co)


for j in range(NP):
    j2 = (j + 1) % NP
    add_face((top_pole, top[0][j], top[0][j2]), 0)
    add_face((bot_pole, bot[0][j2], bot[0][j]), 1)
    for i in range(NRr - 1):
        add_face((top[i][j], top[i + 1][j], top[i + 1][j2], top[i][j2]), 0)
        add_face((bot[i][j2], bot[i + 1][j2], bot[i + 1][j], bot[i][j]), 1)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
shell = to_obj("Shell", bm)
shell.modifiers.new("sub", "SUBSURF").levels = 1
whole_group(shell, "Root")

# ================================================================ head and neck: a tube from inside the shell to the snout
NECK = Vector((A * 0.80, 0, 0.02))
SNOUT = Vector((A + 0.34, 0, 0.07))
NH, NRH = 48, 32


def head_radius(uh):
    """uh: 0 at the snout tip, 1 at the neck base."""
    if uh < 0.12:   # rounded, pointed snout
        return 0.022 + 0.048 * math.sqrt(max(0.0, 1 - ((0.12 - uh) / 0.12) ** 2))
    # widest at the jaw behind the eyes, narrower neck, thickening into the skin folds at the shell
    return 0.07 + 0.015 * sstep(0.12, 0.28, uh) - 0.017 * sstep(0.30, 0.50, uh) + 0.017 * sstep(0.60, 1.0, uh)


def head_point(uh, th):
    c = SNOUT + (NECK - SNOUT) * uh
    r = head_radius(uh)
    squash = 0.78 * (0.9 + 0.1 * sstep(0.0, 0.3, uh))
    return c + Vector((0, r * math.cos(th), r * squash * math.sin(th)))


bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
rings = [[bm.verts.new(head_point((i + 1) / NH, 2 * math.pi * j / NRH)) for j in range(NRH)] for i in range(NH)]
tip = bm.verts.new(SNOUT + Vector((0.004, 0, -0.004)))
for j in range(NRH):
    j2 = (j + 1) % NRH
    f = bm.faces.new((tip, rings[0][j2], rings[0][j]))
    for loop, uv in zip(f.loops, [(0.0, (j + 0.5) / NRH), (1 / NH, (j + 1) / NRH), (1 / NH, j / NRH)]):
        loop[uvl].uv = uv
    for i in range(NH - 1):
        f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
        for loop, (a, b) in zip(f.loops, [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]):
            loop[uvl].uv = ((a + 1) / NH, b / NRH)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
head = to_obj("Head", bm)
head.modifiers.new("sub", "SUBSURF").levels = 1
whole_group(head, "Head")

EYE_UH, EYE_TH, EYE_R = 0.15, 0.50, 0.021
eyes = []
for side in (1, -1):
    th = EYE_TH if side > 0 else math.pi - EYE_TH
    p = head_point(EYE_UH, th)
    c = SNOUT + (NECK - SNOUT) * EYE_UH
    n = (p - c).normalized()
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=EYE_R, calc_uvs=True)
    rot = Vector((0, 0, 1)).rotation_difference(n).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(p - n * EYE_R * 0.35) @ rot, verts=bm.verts)
    eye = to_obj("Eye", bm)
    whole_group(eye, "Head")
    eyes.append(eye)

# ================================================================ legs, claws, tail


def limb(name, base, direction, length, r0, foot_w, n_claws, claw_len, group):
    """Tapered leg flattening into a paddle-like foot, with claws at the tip. UV u runs along the leg."""
    d = direction.normalized()
    side = d.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(d).normalized()
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    n_r, n_a = 20, 16
    rings = []
    for i in range(n_r):
        t = i / (n_r - 1)
        c = base + d * length * t + Vector((0, 0, -0.04 * t * t))
        foot = sstep(0.55, 0.9, t)
        width = r0 * (1 - 0.35 * t) * (1 - foot) + foot_w * foot
        thick = r0 * (1 - 0.35 * t) * (1 - foot) + r0 * 0.28 * foot
        if t > 0.92:
            k = math.sqrt(max(0.0, 1 - ((t - 0.92) / 0.08) ** 2))
            width, thick = width * (0.3 + 0.7 * k), thick * (0.3 + 0.7 * k)
        rings.append([bm.verts.new(c + width * math.cos(2 * math.pi * k_ / n_a) * side + thick * math.sin(2 * math.pi * k_ / n_a) * up)
                      for k_ in range(n_a)])
    for i in range(n_r - 1):
        for k in range(n_a):
            k2 = (k + 1) % n_a
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            for loop, (a, b) in zip(f.loops, [(i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)]):
                loop[uvl].uv = (a / (n_r - 1), b / n_a)
    cap = bmesh.ops.contextual_create(bm, geom=rings[-1])
    for f in cap["faces"]:
        for loop in f.loops:
            loop[uvl].uv = (1.0, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    leg = to_obj(name, bm)
    leg.modifiers.new("sub", "SUBSURF").levels = 1
    whole_group(leg, group)
    claws = []
    tip_c = base + d * length * 0.97 + Vector((0, 0, -0.04 * 0.94))
    for k in range(n_claws):
        off = (k / (n_claws - 1) - 0.5) * 1.3 * foot_w
        bmc = bmesh.new()
        bmc.loops.layers.uv.new("UVMap")
        bmesh.ops.create_cone(bmc, cap_ends=True, segments=8, radius1=0.012, radius2=0.002, depth=claw_len)
        cdir = (d + Vector((0, 0, -0.35))).normalized()
        rot = Vector((0, 0, 1)).rotation_difference(cdir).to_matrix().to_4x4()
        bmesh.ops.transform(bmc, matrix=Matrix.Translation(tip_c + side * off + cdir * claw_len * 0.5) @ rot, verts=bmc.verts)
        claw = to_obj(f"{name}Claw{k}", bmc)
        whole_group(claw, group)
        claws.append(claw)
    return leg, claws


legs, claws = [], []
for side, tag in ((1, "L"), (-1, "R")):
    leg, cl = limb(f"Front{tag}", Vector((A * 0.55, B * 0.78 * side, -0.04)), Vector((0.55, 0.85 * side, -0.25)),
                   0.34, 0.055, 0.075, 5, 0.04, f"LegF{tag}")
    legs.append(leg)
    claws += cl
    leg, cl = limb(f"Rear{tag}", Vector((-A * 0.62, B * 0.72 * side, -0.05)), Vector((-0.55, 0.85 * side, -0.25)),
                   0.30, 0.06, 0.095, 4, 0.025, f"LegR{tag}")
    legs.append(leg)
    claws += cl
bmt = bmesh.new()
bmt.loops.layers.uv.new("UVMap")
bmesh.ops.create_cone(bmt, cap_ends=True, segments=12, radius1=0.045, radius2=0.004, depth=0.2)
tdir = Vector((-1, 0, -0.25)).normalized()
bmesh.ops.transform(bmt, matrix=Matrix.Translation(Vector((-A * 0.9, 0, -0.03)) + tdir * 0.1) @ Vector((0, 0, 1)).rotation_difference(tdir).to_matrix().to_4x4(), verts=bmt.verts)
tail = to_obj("Tail", bmt)
whole_group(tail, "Tail")

# ================================================================ textures


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


def mix(base, color, amount):
    amount = amount[..., None]
    return base * (1 - amount) + np.asarray(color, F32) * amount


def save(name, rgb, non_color=False):
    h, w, _ = rgb.shape
    img = bpy.data.images.new(name, w, h, alpha=True)
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((h, w, 1), F32)], -1)
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=F32).ravel())
    img.filepath_raw = f"{OUT}/tex/{name}.png"
    img.file_format = "PNG"
    img.save()
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def normal_from(height, strength):
    gy, gx = np.gradient(height)
    n = np.stack([-gx * strength, -gy * strength, np.ones_like(gx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True) * 0.5 + 0.5


def nearest(values, points):
    return np.min(np.abs(values[..., None] - np.asarray(points, F32)), axis=-1)


# carapace: 5 vertebral, 4+4 costal and 24 marginal scutes; grooves, growth rings parallel to the edges, yellow markings
S = 2048
cu_, cv_ = np.meshgrid(np.linspace(0, 1, S, dtype=F32), np.linspace(0, 1, S, dtype=F32))
X, Y = cu_ * 2 - 1, cv_ * 2 - 1           # shell plane: X along the body, Y across
r = np.sqrt(X * X + Y * Y)
ang = np.arctan2(Y, X)
marg_frac = (ang / (2 * np.pi) * 24) % 1.0
border = 0.27 + 0.04 * np.cos(X * np.pi * 3)    # vertebral / costal boundary
vertebral = np.abs(Y) < border
d_ring = np.abs(r - 0.82)
d_marg = np.minimum(marg_frac, 1 - marg_frac) * (2 * np.pi * r / 24)
d_inner = np.minimum(np.abs(np.abs(Y) - border), np.where(vertebral, nearest(X, [-0.5, -0.17, 0.17, 0.5]), nearest(X, [-0.40, 0.0, 0.40])))
d_seam = np.where(r > 0.82, np.minimum(d_ring, d_marg), np.minimum(d_inner, d_ring))
groove = smoothstep(0.012, 0.0, d_seam)
annuli = 0.5 + 0.5 * np.cos(d_seam * 2 * np.pi * 28)
noise = fbm(cu_, cv_, 8, 8, 5, 5)
base = np.asarray(C["shell"], F32) * (0.75 + 0.5 * noise)[..., None]
stripes = smoothstep(0.90, 0.97, 0.5 + 0.5 * np.sin(X * 22 + 7 * fbm(cu_, cv_, 14, 14, 7, 4) + np.abs(Y) * 6)) * ((r < 0.82) & ~vertebral)
marg_bar = smoothstep(0.10, 0.02, np.abs(marg_frac - 0.5)) * (r > 0.86)
blot = smoothstep(0.72, 0.80, fbm(cu_, cv_, 18, 18, 9, 3)) * (r < 0.82)
marks = np.clip(stripes + marg_bar * 0.8 + blot * 0.6, 0, 1) * smoothstep(0.0, 0.03, d_seam)
shell_col = mix(base, C["shell_mark"], marks)
shell_col *= (0.96 + 0.04 * annuli * smoothstep(0.0, 0.12, d_seam))[..., None]
shell_col = mix(shell_col, C["seam"], groove)
shell_h = -groove + 0.02 * annuli + 0.25 * smoothstep(0.0, 0.15, d_seam) + 0.05 * noise
img_shell = save(f"{VARIANT}_carapace", shell_col)
img_shell_n = save(f"{VARIANT}_carapace_normal", normal_from(shell_h, 6), True)

# plastron: yellow scutes split down the middle; dark blotch at each scute centre on the normal variant
p_seam = np.minimum(np.abs(Y), nearest(X, [-0.6, -0.3, 0.05, 0.4, 0.7]))
p_groove = smoothstep(0.012, 0.0, p_seam)
plast = np.asarray(C["plastron"], F32) * (0.85 + 0.3 * noise)[..., None]
if C["plastron_spot"] is not None:
    centres = np.asarray([-0.45, -0.125, 0.225, 0.55], F32)
    d_spot = np.sqrt(nearest(X, centres) ** 2 + (np.abs(Y) - 0.22) ** 2)
    spot = smoothstep(0.12, 0.04, d_spot) * smoothstep(0.45, 0.6, fbm(cu_, cv_, 10, 10, 13, 3) + 0.15)
    plast = mix(plast, C["plastron_spot"], spot)
plast = mix(plast, np.asarray(C["plastron"], F32) * 0.55, p_groove)
img_plast = save(f"{VARIANT}_plastron", plast)
img_plast_n = save(f"{VARIANT}_plastron_normal", normal_from(-p_groove + 0.05 * noise, 6), True)
del cu_, cv_, X, Y, r, ang, d_seam

# skin: wavy yellow stripes along the limbs
SW, SH = 1024, 512
su, sv = np.meshgrid(np.linspace(0, 1, SW, dtype=F32), (np.arange(SH, dtype=F32) + 0.5) / SH)
wob = 0.12 * np.sin(su * 6 + sv * 20) + 0.08 * fbm(su, sv, 8, 4, 21, 3)
stripe = smoothstep(0.10, 0.04, np.abs(((sv * 14 + wob) % 1.0) - 0.5))
skin_noise = fbm(su, sv, 40, 20, 23, 3)
skin_base = np.asarray(C["skin"], F32) * (0.85 + 0.3 * skin_noise)[..., None]
skin_col = mix(skin_base, C["stripe"], stripe)
skin_h = 0.4 * stripe + 0.2 * fbm(su, sv, 160, 80, 25, 2)
img_skin = save(f"{VARIANT}_skin", skin_col)
img_skin_n = save(f"{VARIANT}_skin_normal", normal_from(skin_h, 3), True)

# head: finer stripes, the red "ear" patch behind each eye, mouth line, nostrils
hs = smoothstep(0.08, 0.03, np.abs(((sv * 18 + wob) % 1.0) - 0.5)) * smoothstep(0.02, 0.10, su)   # fade where stripes converge at the snout
head_col = mix(skin_base, C["stripe"], hs)
for v_ear in (0.07, 0.43):
    ear = smoothstep(1.0, 0.8, np.sqrt(((su - 0.31) / 0.10) ** 2 + ((sv - v_ear) / 0.022) ** 2))   # elongated stripe behind the eye
    head_col = mix(head_col, C["ear"], ear)
for v_mouth in (0.955, 0.545):
    mouth = smoothstep(0.008, 0.0, np.abs(sv - v_mouth - 0.02 * su)) * smoothstep(0.25, 0.18, su)
    head_col = mix(head_col, (0.05, 0.05, 0.03), mouth)
for v_n in (0.20, 0.30):
    nostril = smoothstep(0.012, 0.006, np.sqrt(((su - 0.015) * 2) ** 2 + (sv - v_n) ** 2))
    head_col = mix(head_col, (0.03, 0.03, 0.02), nostril)
img_head = save(f"{VARIANT}_head", head_col)

# eye: iris with a dark horizontal bar through the pupil (as on sliders)
EW = 256
eu, ev = np.meshgrid(np.linspace(0, 1, EW, dtype=F32), np.linspace(0, 1, EW, dtype=F32))
pd = np.minimum(ev, 1 - ev)
eye = np.asarray(C["iris"], F32) * (0.8 + 0.3 * fbm(eu, ev, 40, 10, 31, 2))[..., None]
bar = (np.abs(np.sin(2 * np.pi * eu)) < 0.22) & (pd < 0.30)
eye = np.where(((pd < 0.10) | bar)[..., None], np.asarray(C["pupil"], F32), eye)
eye = mix(eye, (0.03, 0.03, 0.03), smoothstep(0.30, 0.34, pd))
img_eye = save(f"{VARIANT}_eye", eye)

# ================================================================ materials


def tex(nt, img):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    return t


def material(name, img, nrm=None, rough=0.5, coat=0.0, sss=0.0, color=None):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    if img is not None:
        nt.links.new(tex(nt, img).outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = color
    if nrm is not None:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tex(nt, nrm).outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.08
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Subsurface Scale"].default_value = 0.02
    return m


M_CARAPACE = material("Carapace", img_shell, img_shell_n, rough=0.55, coat=0.1)
M_PLASTRON = material("Plastron", img_plast, img_plast_n, rough=0.5, coat=0.2)
M_SKIN = material("Skin", img_skin, img_skin_n, rough=0.55, coat=0.2, sss=0.1)
M_HEAD = material("HeadSkin", img_head, None, rough=0.5, coat=0.25, sss=0.1)
M_EYE = material("Eye", img_eye, None, rough=0.1, coat=1.0)
M_CLAW = material("Claw", None, None, rough=0.5, color=C["claw"])
shell.data.materials.append(M_CARAPACE)
shell.data.materials.append(M_PLASTRON)


def apply_all(ob):
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


parts = [(shell, None), (head, M_HEAD), (tail, M_SKIN)] + [(e, M_EYE) for e in eyes] + \
        [(leg, M_SKIN) for leg in legs] + [(c, M_CLAW) for c in claws]
for ob, mat in parts:
    if mat is not None:
        ob.data.materials.append(mat)
    apply_all(ob)
bpy.ops.object.select_all(action="DESELECT")
for ob, _ in parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = shell
bpy.ops.object.join()
turtle = shell
turtle.name = VARIANT
for p in turtle.data.polygons:
    p.use_smooth = True

# ================================================================ rig and swim animation: diagonal leg pairs paddle, head bobs
BONES = {
    "Root": ((0, 0, 0), (0, 0, 0.2), None),
    "Head": (tuple(NECK), tuple(SNOUT), "Root"),
    "LegFL": ((A * 0.55, B * 0.78, -0.04), (A * 0.55 + 0.17, B * 0.78 + 0.27, -0.12), "Root"),
    "LegFR": ((A * 0.55, -B * 0.78, -0.04), (A * 0.55 + 0.17, -B * 0.78 - 0.27, -0.12), "Root"),
    "LegRL": ((-A * 0.62, B * 0.72, -0.05), (-A * 0.62 - 0.15, B * 0.72 + 0.24, -0.12), "Root"),
    "LegRR": ((-A * 0.62, -B * 0.72, -0.05), (-A * 0.62 - 0.15, -B * 0.72 - 0.24, -0.12), "Root"),
    "Tail": ((-A * 0.9, 0, -0.03), (-A * 0.9 - 0.2, 0, -0.08), "Root"),
}
arm = bpy.data.armatures.new("Rig")
rig = bpy.data.objects.new("Rig", arm)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for name, (h, t, parent) in BONES.items():
    b = arm.edit_bones.new(name)
    b.head, b.tail = h, t
    if parent:
        b.parent = arm.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")
turtle.modifiers.new("Armature", "ARMATURE").object = rig
turtle.parent = rig
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions.new("swim")
FR = 36
scene.frame_start, scene.frame_end = 1, FR
for f in range(1, FR + 2):
    w = 2 * math.pi * (f - 1) / FR
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        if pb.name in ("LegFL", "LegRR"):
            pb.rotation_euler = (0.15 * math.sin(w + 1.2), 0, 0.55 * math.sin(w))
        elif pb.name in ("LegFR", "LegRL"):
            pb.rotation_euler = (0.15 * math.sin(w + math.pi + 1.2), 0, 0.55 * math.sin(w + math.pi))
        elif pb.name == "Head":
            pb.rotation_euler = (0.06 * math.sin(2 * w), 0, 0)
        elif pb.name == "Tail":
            pb.rotation_euler = (0, 0, 0.15 * math.sin(w))
        else:
            pb.rotation_euler = (0.02 * math.sin(w), 0, 0)
        pb.keyframe_insert("rotation_euler", frame=f)
bpy.ops.object.select_all(action="DESELECT")
turtle.select_set(True)
rig.select_set(True)
bpy.ops.export_scene.gltf(filepath=f"{OUT}/{VARIANT}.glb", export_animations=True, use_selection=True)
print("EXPORTED", VARIANT, len(turtle.data.vertices), "verts")
if not RENDER:
    sys.exit(0)

# ================================================================ previews
pv = Previewer(OUT, VARIANT)
pv.render("closeup", 9, (1.6, -1.9, 1.25), (0.05, 0, 0.0), 50, (0.55, -0.2, 0.15))
pv.render("head", 9, (1.45, -0.75, 0.35), (0.85, 0, 0.06), 70, (0.83, -0.08, 0.10))
pv.pond()
pv.render("pond", 1, (0.1, -2.4, 2.6), (0.0, 0, -0.1), 40, (0.0, 0.0, 0.0))
print("DONE", VARIANT)
