"""Procedural 3D food & prop models.  1 Blender unit = 10 cm."""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector, Matrix, noise as mnoise

from . import materials as M
from . import fx


# --------------------------------------------------------------- helpers ---
def new_obj(name, data, coll=None):
    o = bpy.data.objects.new(name, data)
    if coll is not None:
        coll.objects.link(o)
    return o


def _revolve(bm, prof, seg=64, rfn=None):
    """Revolve (r, z) profile around Z.  rfn(theta, z) -> radial scale lets a
    profile be lobed (garlic cloves) or squashed."""
    rings = []
    for r, z in prof:
        if r < 1e-6:
            rings.append([bm.verts.new((0.0, 0.0, z))])
        else:
            ring = []
            for i in range(seg):
                th = 2 * math.pi * i / seg
                k = rfn(th, z) if rfn else 1.0
                ring.append(bm.verts.new((r * k * math.cos(th), r * k * math.sin(th), z)))
            rings.append(ring)
    faces = []
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        for i in range(seg):
            j = (i + 1) % seg
            if len(a) == 1:
                vs = (a[0], b[j], b[i])
            elif len(b) == 1:
                vs = (a[i], a[j], b[0])
            else:
                vs = (a[i], a[j], b[j], b[i])
            f = bm.faces.new(vs)
            f.smooth = True
            faces.append(f)
    return faces


def revolve_mesh(name, prof, seg=64, matfn=None, closed=True, rfn=None):
    bm = bmesh.new()
    faces = _revolve(bm, prof, seg, rfn)
    if matfn:
        for f in faces:
            f.material_index = matfn(f.calc_center_median())
    if closed:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def _mats(me, mats):
    for m in mats:
        me.materials.append(m)


def _hide_proto(o):
    for a in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission",
              "visible_volume_scatter", "visible_shadow"):
        setattr(o, a, False)
    o.location = (0, 0, -200)


_mesh_cache = {}


def _once(key, fn):
    if key not in _mesh_cache:
        _mesh_cache[key] = fn()
    return _mesh_cache[key]


def _disc(name, radius, z, rings=24, seg=96, zfn=None):
    prof = []
    for k in range(rings + 1):
        r = radius * k / rings
        prof.append((r, z if zfn is None else zfn(r)))
    me = revolve_mesh(name, prof, seg, closed=False)
    for p in me.polygons:
        p.use_smooth = True
    return me


def _box(bm, center, size, rot=None):
    m = Matrix.Translation(center)
    if rot is not None:
        m = m @ rot.to_4x4()
    m = m @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
    return bmesh.ops.create_cube(bm, size=1.0, matrix=m)


# ---------------------------------------------------------------- props ----
def cutting_board(name, coll, sx=1.9, sy=1.35, h=0.08):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = (v.co.x * sx, v.co.y * sy, (v.co.z - 0.5) * h)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    _mats(me, [M.wood()])
    o = new_obj(name, me, coll)
    b = o.modifiers.new("Bevel", "BEVEL")
    b.width = 0.03
    b.segments = 4
    return o


def floor(name, coll, size=60, z=0.0, mat=None, catcher=True):
    """Seamless studio floor: a Cycles shadow catcher shows the backdrop with
    contact shadows (no visible horizon line)."""
    me = bpy.data.meshes.new(name)
    s = size / 2
    me.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
    _mats(me, [mat or M.slate()])
    o = new_obj(name, me, coll)
    o.is_shadow_catcher = catcher
    return o


DISH_LIQ_Z = 0.16


def dish(name, coll):
    prof = [(0, 0), (0.55, 0), (0.62, 0.01), (0.72, 0.05), (0.80, 0.13), (0.85, 0.22), (0.86, 0.245),
            (0.845, 0.256), (0.82, 0.246), (0.78, 0.17), (0.70, 0.09), (0.60, 0.05), (0.5, 0.04), (0, 0.04)]
    me = _once("dish", lambda: revolve_mesh("dish", prof, 72))
    if not me.materials:
        _mats(me, [M.stoneware()])
    return new_obj(name, me, coll)


# Stock pot for the pasta water
POT_FLOOR = 0.06
POT_WATER_Z = 0.50
POT_R_IN = 0.89


def pot(name, coll):
    prof = [(0, 0), (0.85, 0), (0.92, 0.03), (0.95, 0.1), (0.95, 0.58), (0.945, 0.615), (0.925, 0.632),
            (0.905, 0.625), (0.89, 0.6), (0.89, 0.1), (0.85, 0.06), (0, 0.06)]
    me = revolve_mesh(name, prof, 96)
    _mats(me, [M.brushed_steel()])
    o = new_obj(name, me, coll)
    # two side handles
    bm = bmesh.new()
    for sgn in (-1, 1):
        _box(bm, Vector((sgn * 1.02, 0, 0.5)), (0.16, 0.34, 0.05))
    hm = bpy.data.meshes.new(name + "_handles")
    bm.to_mesh(hm)
    bm.free()
    _mats(hm, [M.brushed_steel()])
    h = new_obj(name + "_handles", hm, coll)
    h.parent = o
    bv = h.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.02
    bv.segments = 3
    return o


# Skillet: floor top at PAN_FLOOR, inner wall flares outwards
PAN_FLOOR = 0.04
_PAN_IN = [(0.97, 0.04), (1.03, 0.07), (1.10, 0.17), (1.175, 0.27)]


def pan_inner_r(z):
    """Inner wall radius of the skillet at height z."""
    pts = _PAN_IN
    if z <= pts[0][1]:
        return pts[0][0]
    for (r0, z0), (r1, z1) in zip(pts[:-1], pts[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return pts[-1][0]


def skillet(name, coll):
    prof = [(0, 0), (0.95, 0), (1.02, 0.015), (1.06, 0.05), (1.14, 0.18), (1.20, 0.26), (1.215, 0.275),
            (1.205, 0.285), (1.175, 0.27), (1.10, 0.17), (1.03, 0.07), (0.97, 0.04), (0, 0.04)]
    me = revolve_mesh(name, prof, 128)
    _mats(me, [M.cast_iron()])
    o = new_obj(name, me, coll)
    bm = bmesh.new()
    rot = Matrix.Rotation(-0.16, 3, "Y")
    _box(bm, Vector((1.95, 0, 0.30)), (1.6, 0.16, 0.07), rot)
    _box(bm, Vector((1.22, 0, 0.235)), (0.16, 0.22, 0.09))
    hm = bpy.data.meshes.new(name + "_handle")
    bm.to_mesh(hm)
    bm.free()
    _mats(hm, [M.cast_iron()])
    h = new_obj(name + "_handle", hm, coll)
    h.parent = o
    bv = h.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.025
    bv.segments = 3
    return o


# Pasta plate: shallow well + wide rim
PLATE_TOP = 0.07


def plate(name, coll):
    prof = [(0, 0), (0.5, 0), (0.56, 0.012), (0.60, 0.035), (0.72, 0.07), (0.85, 0.12), (1.10, 0.165),
            (1.30, 0.19), (1.33, 0.20), (1.32, 0.215), (1.28, 0.212), (1.05, 0.19), (0.82, 0.155),
            (0.72, 0.11), (0.6, 0.08), (0.3, 0.07), (0, 0.07)]
    me = _once("plate", lambda: revolve_mesh("plate", prof, 128))
    if not me.materials:
        _mats(me, [M.ceramic()])
    return new_obj(name, me, coll)


def shaker(name, coll):
    prof = [(0, 0), (0.10, 0), (0.12, 0.012), (0.125, 0.04), (0.125, 0.30), (0.12, 0.33), (0.112, 0.342),
            (0.119, 0.346), (0.119, 0.42), (0.112, 0.434), (0.08, 0.44), (0.0, 0.441)]
    me = _once("shaker", lambda: revolve_mesh("shaker", prof, 48, lambda c: 1 if c.z > 0.343 else 0))
    if not me.materials:
        _mats(me, [M.plastic((0.72, 0.10, 0.05), 0.35), M.shaker_cap()])
    return new_obj(name, me, coll)


def oil_bottle(name, coll):
    prof = [(0, 0), (0.15, 0), (0.17, 0.02), (0.175, 0.06), (0.175, 0.52), (0.16, 0.6), (0.10, 0.68),
            (0.055, 0.74), (0.05, 0.86), (0.058, 0.87), (0.058, 0.95), (0.0, 0.955)]
    me = revolve_mesh(name, prof, 48, lambda c: 1 if c.z > 0.862 else 0)
    _mats(me, [M.glass(), M.plastic((0.08, 0.10, 0.06), 0.4)])
    o = new_obj(name, me, coll)
    ip = [(0, 0.02), (0.158, 0.02), (0.16, 0.05), (0.16, 0.50), (0.0, 0.50)]
    im = revolve_mesh(name + "_oil", ip, 48)
    _mats(im, [M.olive_oil()])
    oi = new_obj(name + "_oil", im, coll)
    oi.parent = o
    return o


def stream(name, coll, pts, radius, mat, taper=(1.0, 0.7)):
    """Pouring liquid: a bevelled poly curve; animate data.bevel_factor_start/end."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    cu.bevel_factor_mapping_start = "SPLINE"
    cu.bevel_factor_mapping_end = "SPLINE"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        t = i / max(len(pts) - 1, 1)
        sp.points[i].co = (*p, 1.0)
        sp.points[i].radius = taper[0] + (taper[1] - taper[0]) * t
    cu.materials.append(mat)
    return new_obj(name, cu, coll)


# --------------------------------------------------------------- chicken ---
CHICKEN_BOTTOM = 0.072


def chicken_mesh():
    """Whole raw breast fillet (ingredient line-up)."""
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=48, radius=1.0)
        for v in bm.verts:
            x, y, z = v.co
            th = math.atan2(y, x)
            rho = math.sqrt(x * x + y * y)
            R = 1 + 0.06 * math.sin(2 * th + 0.7) + 0.045 * math.sin(3 * th + 2.1) + 0.03 * math.sin(5 * th + 0.4)
            X = 0.62 * rho * R * math.cos(th)
            Y = 0.50 * rho * R * math.sin(th)
            lump = 1 + 0.16 * mnoise.noise(Vector((X * 2.3, Y * 2.3, 0.5)))
            h = 0.085 if z > 0 else 0.068
            Z = math.copysign(abs(z) ** 0.45, z) * h * lump
            v.co = (X, Y, Z + CHICKEN_BOTTOM)
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new("chicken")
        bm.to_mesh(me)
        bm.free()
        return me
    return _once("chicken", mk)


def chicken(name, coll, mat):
    o = new_obj(name, chicken_mesh().copy(), coll)
    o.data.materials.append(mat)
    s = o.modifiers.new("Subsurf", "SUBSURF")
    s.levels = s.render_levels = 1
    return o


CUBE = 0.21          # chicken cube edge length (2.1 cm)


def chicken_cube_mesh(seed):
    """Irregular rounded cube of chicken breast."""
    def mk():
        rng = random.Random(seed)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=5, use_grid_fill=True)
        r = 0.2
        sx, sy, sz = rng.uniform(0.85, 1.2), rng.uniform(0.85, 1.15), rng.uniform(0.75, 1.0)
        off = Vector((rng.uniform(0, 9), rng.uniform(0, 9), rng.uniform(0, 9)))
        for v in bm.verts:
            c = Vector(v.co)
            inner = Vector([max(-(0.5 - r), min(0.5 - r, x)) for x in c])
            d = c - inner
            c = inner + (d.normalized() * r if d.length > 1e-6 else d)
            c += c.normalized() * 0.05 * mnoise.noise(c * 3.0 + off)
            v.co = (c.x * sx * CUBE, c.y * sy * CUBE, c.z * sz * CUBE)
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new(f"chicken_cube{seed}")
        bm.to_mesh(me)
        bm.free()
        me["hz"] = 0.5 * sz * CUBE * 1.03      # half-height: rest height above a surface
        return me
    return _once(("cube", seed), mk)


def chicken_cube(name, coll, mat, seed):
    """Origin at the cube's centre; data["hz"] is its half-height."""
    o = new_obj(name, chicken_cube_mesh(seed % 6), coll)
    if not o.data.materials:
        o.data.materials.append(mat)
    o.material_slots[0].link = "OBJECT"
    o.material_slots[0].material = mat
    s = o.modifiers.new("Subsurf", "SUBSURF")
    s.levels = s.render_levels = 1
    return o


# --------------------------------------------------------------- produce ---
def garlic_bulb(name, coll):
    prof = [(0, 0.0), (0.12, 0.004), (0.22, 0.03), (0.28, 0.09), (0.30, 0.17), (0.28, 0.26), (0.22, 0.34),
            (0.14, 0.41), (0.07, 0.47), (0.035, 0.52), (0.025, 0.58), (0.0, 0.60)]

    def lobes(th, z):
        k = 1 + 0.09 * abs(math.cos(4 * th + 0.3)) - 0.045
        return 1 + (k - 1) * min(1.0, z / 0.12) * max(0.0, 1 - (z - 0.3) / 0.25)
    me = _once("garlic", lambda: revolve_mesh("garlic", prof, 64, rfn=lobes))
    if not me.materials:
        _mats(me, [M.garlic_skin()])
    return new_obj(name, me, coll)


def onion(name, coll):
    prof = [(0, 0.0), (0.06, 0.005), (0.18, 0.04), (0.30, 0.12), (0.36, 0.24), (0.355, 0.34), (0.30, 0.45),
            (0.20, 0.54), (0.09, 0.61), (0.035, 0.66), (0.02, 0.72), (0.0, 0.73)]
    me = _once("onion", lambda: revolve_mesh("onion", prof, 64,
                                            rfn=lambda th, z: 1 + 0.015 * math.sin(7 * th) * min(1, z * 5)))
    if not me.materials:
        _mats(me, [M.onion_skin()])
    return new_obj(name, me, coll)


def basil_leaf_mesh(L=0.5, seed=0):
    def mk():
        rng = random.Random(seed)
        NU, NV = 28, 12
        bm = bmesh.new()
        verts, rad, vx = [], [], []
        bend = rng.uniform(0.6, 1.2)
        for i in range(NU + 1):
            u = i / NU
            w = 0.36 * L * math.sin(math.pi * min(1.0, u ** 0.75)) ** 0.9
            row = []
            for j in range(NV + 1):
                v = -1 + 2 * j / NV
                x = u * L
                y = v * w
                z = 0.12 * L * abs(v) ** 1.5 * (w / (0.36 * L) + 0.2) - 0.12 * L * bend * u * u
                z += 0.01 * mnoise.noise(Vector((x * 9, y * 9, seed)))
                row.append(bm.verts.new((x, y, z)))
                rad.append(abs(v))
                vx.append(v)
            verts.append(row)
        for i in range(NU):
            for j in range(NV):
                f = bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
                f.smooth = True
        me = bpy.data.meshes.new(f"basil{seed}")
        bm.to_mesh(me)
        bm.free()
        for nm, arr in (("rad", rad), ("vx", vx)):
            a = me.attributes.new(nm, "FLOAT", "POINT")
            a.data.foreach_set("value", np.array(arr, dtype=np.float32))
        _mats(me, [M.basil()])
        return me
    return _once(("basil", L, seed), mk)


def basil_leaf(name, coll, L=0.5, seed=0):
    o = new_obj(name, basil_leaf_mesh(L, seed), coll)
    s = o.modifiers.new("Solidify", "SOLIDIFY")
    s.thickness = 0.004
    s.offset = 0
    return o


def basil_sprig(name, coll, n=4, L=0.5):
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    for i in range(n):
        lf = basil_leaf(f"{name}_leaf{i}", coll, L * (1.0 - 0.12 * (i // 2)), seed=i)
        lf.parent = root
        a = i * 2.4
        lf.rotation_euler = (0.25 * (-1) ** i, -0.35, a)
        lf.location = (0.02 * math.cos(a), 0.02 * math.sin(a), 0.03 * (i // 2))
    return root


def parmesan_wedge(name, coll):
    def mk():
        bm = bmesh.new()
        L, Wd, Ht = 0.72, 0.52, 0.34
        pts = [(0.0, 0.0), (L, -Wd / 2), (L, Wd / 2)]
        bot = [bm.verts.new((x, y, 0.0)) for x, y in pts]
        top = [bm.verts.new((x, y, Ht)) for x, y in pts]
        bm.faces.new(bot[::-1])
        bm.faces.new(top)
        for i in range(3):
            j = (i + 1) % 3
            f = bm.faces.new((bot[i], bot[j], top[j], top[i]))
            if i == 1:
                f.material_index = 1          # rind on the back
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=8, use_grid_fill=True)
        for v in bm.verts:
            c = Vector(v.co)
            if c.x < L - 0.01:
                c.z += 0.012 * mnoise.noise(c * 14.0) * (1 if 0.005 < c.z < Ht - 0.005 else 0)
                c.y += 0.01 * mnoise.noise(c * 11.0 + Vector((3, 1, 2)))
            v.co = c
        me = bpy.data.meshes.new("parmesan")
        bm.to_mesh(me)
        bm.free()
        _mats(me, [M.parmesan(), M.parmesan(True)])
        return me
    o = new_obj(name, _once("parmesan", mk), coll)
    bv = o.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.012
    bv.segments = 2
    return o


def carrot(name, coll):
    """Whole carrot along +Z (tip at z=0) with a stubby green top."""
    def mk():
        prof = [(0.0, 0.0)]
        for k in range(1, 41):
            z = k / 40
            prof.append((0.012 + 0.098 * z ** 0.65, z))
        prof += [(0.10, 1.0), (0.05, 1.01), (0.0, 1.012)]
        bm = bmesh.new()
        _revolve(bm, prof, 40, rfn=lambda th, z: 1 + 0.035 * math.sin(55 * z + 2 * math.sin(3 * th)))
        _box(bm, Vector((0, 0, 1.05)), (0.035, 0.035, 0.09))
        for f in bm.faces:
            f.material_index = 1 if f.calc_center_median().z > 1.005 else 0
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("carrot")
        bm.to_mesh(me)
        bm.free()
        _mats(me, [M.carrot_skin(), M.basil()])
        return me
    return new_obj(name, _once("carrot", mk), coll)


def celery(name, coll, L=1.1):
    """Celery stalk: a ribbed crescent section swept along a gentle curve."""
    def mk():
        bm = bmesh.new()
        NR, NM = 44, 28
        rings, ribs = [], []
        for i in range(NR + 1):
            u = i / NR
            x = u * L
            y = 0.05 * math.sin(math.pi * u)
            taper = 0.75 + 0.25 * math.sin(math.pi * min(1.0, u * 1.15)) + 0.15 * u
            ring = []
            for j in range(NM):
                t = j / NM
                if t < 0.6:      # outer ribbed arc (underside)
                    th = math.pi * (1.1 + 0.8 * (t / 0.6))
                    r = 0.085 * (1 + 0.06 * math.cos(14 * th))
                    rib = 0.5 + 0.5 * math.cos(14 * th)
                    cy, cz = r * math.cos(th), r * math.sin(th) + 0.02
                else:            # inner groove (top)
                    th = math.pi * (1.9 - 0.8 * ((t - 0.6) / 0.4))
                    r = 0.055
                    rib = 0.0
                    cy, cz = r * math.cos(th), r * math.sin(th) + 0.05
                ring.append(bm.verts.new((x, y + cy * taper, cz * taper)))
                ribs.append(rib)
            rings.append(ring)
        for a, b in zip(rings[:-1], rings[1:]):
            for j in range(NM):
                k = (j + 1) % NM
                f = bm.faces.new((a[j], b[j], b[k], a[k]))
                f.smooth = True
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("celery")
        bm.to_mesh(me)
        bm.free()
        a = me.attributes.new("rib", "FLOAT", "POINT")
        a.data.foreach_set("value", np.array(ribs, dtype=np.float32))
        _mats(me, [M.celery_skin()])
        return me
    return new_obj(name, _once(("celery", L), mk), coll)


def wine_bottle(name, coll):
    prof = [(0, 0), (0.14, 0), (0.15, 0.015), (0.152, 0.05), (0.152, 0.62), (0.14, 0.68), (0.09, 0.74),
            (0.05, 0.79), (0.045, 0.84), (0.045, 1.0), (0.05, 1.005), (0.0, 1.01)]
    me = _once("wine_bottle", lambda: revolve_mesh("wine_bottle", prof, 48, lambda c: 1 if c.z > 0.86 else 0))
    if not me.materials:
        _mats(me, [M.bottle_glass(), M.plastic((0.45, 0.05, 0.05), 0.3)])
    o = new_obj(name, me, coll)
    lp = [(0.1555, 0.18), (0.1555, 0.46)]
    lm = _once("wine_label", lambda: revolve_mesh("wine_label", lp, 48, closed=False))
    if not lm.materials:
        _mats(lm, [M.label_paper()])
    lb = new_obj(name + "_label", lm, coll)
    lb.parent = o
    return o


def spoon(name, coll):
    """Wooden spoon, origin at the centre of its bowl, handle along +Z."""
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0,
                                  matrix=Matrix.Diagonal((0.12, 0.085, 0.025, 1.0)))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.022, radius2=0.03, depth=1.6,
                              matrix=Matrix.Translation((0, 0, 0.88)) @ Matrix.Rotation(0.0, 4, "X"))
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new("spoon")
        bm.to_mesh(me)
        bm.free()
        _mats(me, [M.wood()])
        return me
    return new_obj(name, _once("spoon", mk), coll)


# --------------------------------------------------------------- liquids ---
def sauce_surface(name, coll, radius, z=0.0, rings=34, seg=128, amp=0.012, mat=None):
    """Chunky tomato-sauce surface (origin at its mean height)."""
    me = _disc(name, radius, 0.0, rings, seg)
    for v in me.vertices:
        c = v.co
        r = math.hypot(c.x, c.y) / radius
        edge = min(1.0, (1 - r) * 8)
        v.co.z = amp * edge * (mnoise.noise(Vector((c.x * 7, c.y * 7, 0.3))) +
                               0.5 * mnoise.noise(Vector((c.x * 19, c.y * 19, 1.7))))
    _mats(me, [mat or M.tomato_sauce()])
    o = new_obj(name, me, coll)
    o.location.z = z
    fx.add_ripple(o, amp=0.002, scale=6.0, speed=0.02)
    return o


def sauce_cap(name, coll, radius, height, base_fn, mat=None):
    """Sauce spooned over the nest: a dome that drapes over base_fn(r)."""
    def zfn(r):
        k = max(0.0, 1 - (r / radius) ** 2) ** 0.6
        return base_fn(r) + 0.012 + height * k
    me = _disc(name, radius, 0.0, 24, 96, zfn)
    for v in me.vertices:
        c = v.co
        k = max(0.0, 1 - math.hypot(c.x, c.y) / radius)
        v.co.z += 0.018 * k * (mnoise.noise(Vector((c.x * 9, c.y * 9, 2.0))) +
                               0.6 * mnoise.noise(Vector((c.x * 23, c.y * 23, 5.0))))
    _mats(me, [mat or M.tomato_sauce()])
    return new_obj(name, me, coll)


def water_surface(name, coll, radius, z):
    me = _disc(name, radius, z, 40, 128)
    _mats(me, [M.water()])
    o = new_obj(name, me, coll)
    # no refractive caustics: let light through so the pot and pasta under
    # the surface are lit instead of black
    o.visible_shadow = False
    fx.add_ripple(o, amp=0.01, scale=8.0, speed=0.22)
    return o


def oil_film(name, coll, radius, z):
    me = _disc(name, radius, z, 16, 96)
    _mats(me, [M.oil()])
    o = new_obj(name, me, coll)
    fx.add_ripple(o, amp=0.0015, scale=7.0, speed=0.05)
    return o


# --------------------------------------------------------------- pasta -----
STRAND_R = 0.0095      # cooked spaghetti radius (~1.9 mm diameter)


def strands_mesh(name, strands, strand_attrs=None):
    """Edge-chain mesh, one chain per strand.  Every point gets `s` (0..1 along
    its strand) plus the given per-strand attributes."""
    verts, edges, s_vals = [], [], []
    owner = []
    for k, pts in enumerate(strands):
        i0 = len(verts)
        n = len(pts)
        for i, p in enumerate(pts):
            verts.append(tuple(p))
            s_vals.append(i / max(n - 1, 1))
            owner.append(k)
            if i:
                edges.append((i0 + i - 1, i0 + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, edges, [])
    a = me.attributes.new("s", "FLOAT", "POINT")
    a.data.foreach_set("value", np.array(s_vals, dtype=np.float32))
    owner = np.array(owner)
    for nm, vals in (strand_attrs or {}).items():
        vals = np.asarray(vals, dtype=np.float32)
        a = me.attributes.new(nm, "FLOAT", "POINT")
        a.data.foreach_set("value", vals[owner])
    return me


def pasta_object(name, coll, strands, mat, group, inputs=None, strand_attrs=None, radius=STRAND_R):
    me = strands_mesh(name, strands, strand_attrs)
    o = new_obj(name, me, coll)
    mod = o.modifiers.new("Pasta", "NODES")
    mod.node_group = group
    vals = {"Radius": radius, "Material": mat}
    vals.update(inputs or {})
    fx.set_inputs(o, mod, vals)
    return o


def dry_bundle_strands(rng, n=110, L=2.5, br=0.075, flare=0.0):
    """Straight dry spaghetti, standing on z=0, base points in a small disc.
    flare > 0 fans the strands out slightly towards both ends (still life)."""
    th = rng.uniform(0, 2 * math.pi, n)
    rr = br * np.sqrt(rng.uniform(0, 1, n))
    bx, by = rr * np.cos(th), rr * np.sin(th)
    strands = []
    for k in range(n):
        s = np.linspace(0, 1, 48)
        u = s - 0.5
        fx_ = bx[k] * (1 + flare * 8 * np.abs(u) ** 1.5) + rng.normal(0, 0.002)
        fy_ = by[k] * (1 + flare * 8 * np.abs(u) ** 1.5)
        strands.append(np.stack([fx_, fy_, s * L], 1))
    az = np.arctan2(by, bx) + rng.normal(0, 0.25, n)
    return strands, dict(L=np.full(n, L), th=az, bx=bx, by=by, rnd=rng.uniform(0, 1, n))


def pile_z(r, Rp=0.78, h=0.2):
    return h * max(0.0, 1 - (r / Rp) ** 2) ** 0.7


def pile_strands(rng, n=140, steps=120, step=0.022, Rp=0.78, h=0.2, z0=0.0):
    """Cooked spaghetti tangled into a loose mound (pan / pot)."""
    strands = []
    for k in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = Rp * math.sqrt(rng.uniform(0, 0.9))
        p = np.array([r * math.cos(a), r * math.sin(a)])
        hd = rng.uniform(0, 2 * math.pi)
        curl = rng.normal(0, 0.05)
        layer = rng.uniform(0.15, 1.0)
        ph = rng.uniform(0, 50)
        pts = []
        for i in range(steps):
            rr = np.linalg.norm(p)
            if rr > 0.82 * Rp:
                inward = math.atan2(-p[1], -p[0])
                d = (inward - hd + math.pi) % (2 * math.pi) - math.pi
                hd += 0.35 * d
            hd += curl + rng.normal(0, 0.16)
            p = p + step * np.array([math.cos(hd), math.sin(hd)])
            rr = np.linalg.norm(p)
            z = z0 + pile_z(rr, Rp, h) * layer + 0.012 + 0.012 * mnoise.noise(Vector((p[0] * 6, p[1] * 6, ph)))
            pts.append((p[0], p[1], z))
        strands.append(np.array(pts))
    return strands


def mound_z(r, top=0.42, Rm=0.70):
    """Height of the twirled nest above the plate at radius r."""
    return top * max(0.0, 1 - (r / Rm) ** 2) ** 0.75


def nest_strands(rng, n=130, pts_per=170, top=0.42, Rm=0.70):
    """Fork-twirled spaghetti nest: coils around the axis stacked into a mound."""
    strands = []
    for k in range(n):
        layer = rng.uniform(0.55, 1.0) ** 0.7
        r0 = Rm * rng.uniform(0.15, 0.95) ** 0.8
        turns = rng.uniform(1.3, 2.6)
        a0 = rng.uniform(0, 2 * math.pi)
        dr = rng.normal(0, 0.12)
        ph = rng.uniform(0, 100)
        pts = []
        for i in range(pts_per):
            t = i / (pts_per - 1)
            a = a0 + 2 * math.pi * turns * t
            r = r0 * (1 + dr * (t - 0.5)) + 0.05 * math.sin(3 * a + ph)
            r += 0.02 * mnoise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, ph + t * 3)))
            r = max(0.04, min(Rm * 1.02, r))
            z = mound_z(r, top, Rm) * layer + 0.012 + 0.015 * mnoise.noise(Vector((math.cos(a) * 3, math.sin(a) * 3, ph)))
            pts.append((r * math.cos(a), r * math.sin(a), z))
        strands.append(np.array(pts))
    return strands


def mound_bvh(top=0.42, Rm=0.70, z0=0.0):
    """Invisible envelope of the nest (for parmesan landing ray casts)."""
    prof = [(Rm * k / 30, z0 + mound_z(Rm * k / 30, top, Rm) + 0.03) for k in range(31)]
    me = revolve_mesh("_mound", prof, 48, closed=False)
    b = fx.bvh_from_mesh(me)
    bpy.data.meshes.remove(me)
    return b


# ------------------------------------------------------------ prototypes ---
def _bubble_mat():
    m, p = M.mozzarella("mozz_bubble")
    p["melt"].outputs[0].default_value = 1.0
    p["brown"].outputs[0].default_value = 0.35
    return m


def proto_objects(coll):
    """Particle instance prototypes (hidden from all ray types)."""
    out = {}
    rng = random.Random(7)

    def chunk(name, subdiv, jitter, mat, flat=1.0):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        for v in bm.verts:
            v.co *= 1 + rng.uniform(-jitter, jitter)
            v.co.z *= flat
        for f in bm.faces:
            f.smooth = subdiv > 1
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        _mats(me, [mat])
        o = new_obj(name, me, coll)
        _hide_proto(o)
        return o

    def sphere(name, mat, u=16, v=10):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        _mats(me, [mat])
        o = new_obj(name, me, coll)
        _hide_proto(o)
        return o

    out["spice"] = chunk("proto_spice", 1, 0.35, M.spice())
    out["herb"] = chunk("proto_herb", 1, 0.4, M.herb(), flat=0.25)
    out["parm"] = chunk("proto_parm", 1, 0.45, M.parmesan(), flat=0.35)
    out["salt"] = chunk("proto_salt", 0, 0.2, M.salt())
    out["tomato"] = chunk("proto_tomato", 2, 0.35, M.tomato_sauce())
    out["garlic"] = chunk("proto_garlic", 2, 0.15, M.garlic_flesh(), flat=0.3)
    out["onion"] = chunk("proto_onion", 2, 0.3, M.onion_flesh(), flat=0.35)
    out["drop"] = sphere("proto_drop", M.sauce_drop())
    out["oil_drop"] = sphere("proto_oil_drop", M.droplet())
    out["wdrop"] = sphere("proto_wdrop", M.water_bubble())
    out["bubble"] = sphere("proto_bubble", M.water_bubble(), 20, 12)
    out["blub"] = sphere("proto_blub", M.sauce_drop(), 20, 12)
    out["oil_bubble"] = sphere("proto_oil_bubble", M.droplet((0.95, 0.80, 0.45)), 16, 10)

    def dice(name, mat, scl, cuts=1, jitter=0.08):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((*scl, 1.0)))
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
        for v in bm.verts:
            v.co *= 1 + rng.uniform(-jitter, jitter)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        _mats(me, [mat])
        o = new_obj(name, me, coll)
        _hide_proto(o)
        return o
    out["carrot"] = dice("proto_carrot", M.veg("veg_carrot_raw", *M.CARROT)[0], (1.0, 1.0, 1.0))
    out["celery"] = dice("proto_celery", M.veg("veg_celery_raw", *M.CELERY)[0], (1.0, 0.75, 0.45))
    out["onion_d"] = dice("proto_onion_d", M.veg("veg_onion_raw", *M.ONION)[0], (1.0, 0.9, 0.35), jitter=0.15)
    out["mince"] = chunk("proto_mince", 2, 0.45, M.mince("mince_raw")[0], flat=0.7)

    out["flour"] = chunk("proto_flour", 1, 0.4, M.flour(), flat=0.6)
    out["oregano"] = chunk("proto_oregano", 1, 0.4, M.oregano(), flat=0.2)
    out["cbubble"] = sphere("proto_cbubble", _bubble_mat(), 20, 12)

    # mozzarella shred (length along X); shape key "melt" flattens + widens it
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((1.0, 0.13, 0.09, 1.0)))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    for v in bm.verts:
        c = v.co
        v.co = Vector((c.x, c.y * (1 + 0.15 * math.sin(c.x * 9)), c.z + 0.06 * (1 - (2 * c.x) ** 2)))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new("proto_shred")
    bm.to_mesh(me)
    bm.free()
    _mats(me, [M.mozzarella("mozz_raw")[0]])
    o = new_obj("proto_shred", me, coll)
    o.shape_key_add(name="Basis")
    kb = o.shape_key_add(name="melt", from_mix=False)
    co = np.array([(v.co.x * 1.1, v.co.y * 2.8, (v.co.z - 0.05) * 0.3) for v in me.vertices], dtype=np.float32)
    kb.data.foreach_set("co", co.ravel())
    kb.value = 0.0
    _hide_proto(o)
    out["shred"] = o

    # pepperoni slice, unit radius; shape key "cup" curls the edge up
    prof = [(0, 0.06), (0.25, 0.06), (0.5, 0.06), (0.75, 0.059), (0.9, 0.055), (0.97, 0.042), (1.0, 0.015),
            (1.0, -0.015), (0.97, -0.042), (0.9, -0.055), (0.75, -0.059), (0.5, -0.06), (0.25, -0.06), (0, -0.06)]
    me = revolve_mesh("proto_pep", prof, 40, rfn=lambda th, z: 1 + 0.02 * math.sin(3 * th + 1.0))
    for pl in me.polygons:
        pl.use_smooth = True
    _mats(me, [M.pepperoni("pep_raw")[0]])
    o = new_obj("proto_pep", me, coll)
    o.shape_key_add(name="Basis")
    kb = o.shape_key_add(name="cup", from_mix=False)
    co = []
    for v in me.vertices:
        r = math.hypot(v.co.x, v.co.y)
        k = 1 - 0.07 * r
        co.append((v.co.x * k, v.co.y * k, v.co.z + 0.24 * r * r))
    kb.data.foreach_set("co", np.array(co, dtype=np.float32).ravel())
    kb.value = 0.0
    _hide_proto(o)
    out["pep"] = o

    me = bpy.data.meshes.new("proto_sprite")
    me.from_pydata([(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)], [], [(0, 1, 2, 3)])
    _mats(me, [M.steam()])
    o = new_obj("proto_sprite", me, coll)
    _hide_proto(o)
    out["sprite"] = o
    return out


# ------------------------------------------------------------- 3D text -----
_fonts = {}


def text3d(name, coll, body, font_path, size=0.3, extrude=0.03, bevel=0.006, mat=None, spacing=1.0):
    if font_path not in _fonts:
        _fonts[font_path] = bpy.data.fonts.load(font_path, check_existing=True)
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.font = _fonts[font_path]
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = 3
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_character = spacing
    if mat:
        cu.materials.append(mat)
    return new_obj(name, cu, coll)


# ================================================================= PIZZA ===
TAU = 2 * math.pi
PZ_TOP = 0.028           # top of the stretched base (2.8 mm)
PZ_R = 1.262             # outer crust radius (25 cm pizza)
PZ_SAUCE_R = 1.0
PZ_CHEESE_R = 0.965
PEP_R = 0.145            # pepperoni slice radius
DOUGH_BALL_R = 0.5


def _sstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def _catmull(pts, sub):
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        for k in range(sub):
            t = k / sub
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    out.append(pts[-1])
    return out


def _pizza_profile():
    top = [(r, PZ_TOP) for r in np.linspace(0.0, 0.88, 12)][:-1]
    knots = [(0.88, PZ_TOP), (0.96, PZ_TOP + 0.001), (1.03, PZ_TOP + 0.008), (1.08, 0.055), (1.12, 0.083),
             (1.165, 0.100), (1.205, 0.104), (1.237, 0.094), (1.256, 0.072), (1.262, 0.047), (1.256, 0.025),
             (1.237, 0.010), (1.20, 0.002), (1.12, 0.0)]
    rim = _catmull(knots, 5)
    bot = [(r, 0.0) for r in np.linspace(1.0, 0.0, 13)]
    return top + rim + bot


def _rim_noise(th):
    c, s = math.cos(th), math.sin(th)
    nr = mnoise.noise(Vector((c * 1.8, s * 1.8, 0.5))) + 0.5 * mnoise.noise(Vector((c * 5.0, s * 5.0, 2.0)))
    nz = mnoise.noise(Vector((c * 2.2, s * 2.2, 4.0))) + 0.5 * mnoise.noise(Vector((c * 6.0, s * 6.0, 7.0)))
    return nr, nz


def pizza_base(name, coll, th0=0.0, th1=TAU, nseg=192, puff=0.0, keys=False, mats=None):
    """Pizza base (dough) revolved from a crust profile.

    A full disc (th1 - th0 == 2 pi) or a wedge with cut faces (material 1).
    keys=True adds shape keys "ball" (dough ball, radius DOUGH_BALL_R) and
    "puff" (crust risen in the oven).  Vertex attribute `rim` = 0 centre..1 rim.
    """
    prof = _pizza_profile()
    P = len(prof)
    closed = abs((th1 - th0) - TAU) < 1e-6
    ncol = nseg if closed else nseg + 1
    L = np.cumsum([0.0] + [math.dist(a, b) for a, b in zip(prof[:-1], prof[1:])])
    sfrac = L / L[-1]
    verts, ball, puffed, rimv = [], [], [], []
    idx = {}

    def add(base, b, pf, rw):
        verts.append(base)
        ball.append(b)
        puffed.append(pf)
        rimv.append(rw)
        return len(verts) - 1

    for i, (r, z) in enumerate(prof):
        rw = _sstep(0.95, 1.12, r)
        phi = math.pi * sfrac[i]
        if r < 1e-6:
            bz = DOUGH_BALL_R * (1 + math.cos(phi))
            v = add((0.0, 0.0, z), (0.0, 0.0, bz), (0.0, 0.0, z), 0.0)
            for j in range(ncol):
                idx[i, j] = v
            continue
        for j in range(ncol):
            th = th0 + (th1 - th0) * j / (nseg)
            nr, nz = _rim_noise(th)
            r2 = r if r <= 0.95 else 0.95 + (r - 0.95) * (1 + 0.12 * nr)
            z2 = z * (1 + rw * 0.16 * nz)
            c, s = math.cos(th), math.sin(th)
            bump = 0.0
            if rw > 0 and z > 0.01:
                bump = 0.004 * rw * mnoise.noise(Vector((r2 * c * 15, r2 * s * 15, z2 * 15)))
            base = (r2 * c, r2 * s, z2 + bump)
            rp = r2 + 0.03 * rw
            zp = z2 * (1 + (0.55 + 0.25 * nz) * rw) + bump * 1.6
            pf = (rp * c, rp * s, zp)
            b = (DOUGH_BALL_R * math.sin(phi) * c, DOUGH_BALL_R * math.sin(phi) * s, DOUGH_BALL_R * (1 + math.cos(phi)))
            if puff:
                base = tuple(base[k] + (pf[k] - base[k]) * puff for k in range(3))
            idx[i, j] = add(base, b, pf, rw)
    faces, fmat = [], []
    for i in range(P - 1):
        for j in range(nseg):
            j2 = (j + 1) % ncol if closed else j + 1
            vs = [idx[i, j], idx[i + 1, j], idx[i + 1, j2], idx[i, j2]]
            vs = [v for k, v in enumerate(vs) if v not in vs[:k]]
            if len(vs) >= 3:
                faces.append(vs)
                fmat.append(0)
    if not closed:
        for j in (0, nseg):
            faces.append([idx[i, j] for i in range(P)])
            fmat.append(1)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("material_index", fmat)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = f.material_index == 0
        if f.material_index == 1:
            for e in f.edges:
                e.smooth = False
    bm.to_mesh(me)
    bm.free()
    a = me.attributes.new("rim", "FLOAT", "POINT")
    a.data.foreach_set("value", np.array(rimv, dtype=np.float32))
    for m in (mats or []):
        me.materials.append(m)
    o = new_obj(name, me, coll)
    if keys:
        o.shape_key_add(name="Basis")
        for kn, arr in (("ball", ball), ("puff", puffed)):
            kb = o.shape_key_add(name=kn, from_mix=False)
            kb.data.foreach_set("co", np.array(arr, dtype=np.float32).ravel())
            kb.value = 0.0          # Blender 5 creates new keys at full strength
    return o


def pizza_layer(name, coll, R, zfn, th0=0.0, th1=TAU, nseg=192, rings=36, edge=0.03, seed=0.0, mat=None):
    """Sauce / cheese layer: an irregular-edged disc (or wedge of one).
    zfn(x, y, rr) -> height above the object's origin; rr = 0 centre .. 1 edge."""
    closed = abs((th1 - th0) - TAU) < 1e-6
    ncol = nseg if closed else nseg + 1
    verts = [(0.0, 0.0, zfn(0.0, 0.0, 0.0))]
    for i in range(1, rings + 1):
        rr = (i / rings) ** 0.8
        for j in range(ncol):
            th = th0 + (th1 - th0) * j / nseg
            c, s = math.cos(th), math.sin(th)
            re = R * (1 + edge * (mnoise.noise(Vector((c * 2.5, s * 2.5, seed))) +
                                  0.6 * mnoise.noise(Vector((c * 9.0, s * 9.0, seed + 3.0)))))
            x, y = re * rr * c, re * rr * s
            verts.append((x, y, zfn(x, y, rr)))
    faces = []
    vi = lambda i, j: 0 if i == 0 else 1 + (i - 1) * ncol + (j % ncol if closed else j)
    for i in range(rings):
        for j in range(nseg):
            vs = [vi(i, j), vi(i + 1, j), vi(i + 1, j + 1), vi(i, j + 1)]
            vs = [v for k, v in enumerate(vs) if v not in vs[:k]]
            faces.append(vs)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.shade_smooth()
    if mat:
        me.materials.append(mat)
    return new_obj(name, me, coll)


def sauce_z(x, y, rr):
    edge = _sstep(1.0, 0.85, rr)
    return 0.001 + edge * (0.003 + 0.0015 * mnoise.noise(Vector((x * 9, y * 9, 0.7))))


def cheese_z(x, y, rr):
    edge = _sstep(1.0, 0.86, rr)
    n = mnoise.noise(Vector((x * 4.0, y * 4.0, 1.3)))
    b = max(0.0, mnoise.noise(Vector((x * 11.0, y * 11.0, 4.1)))) ** 1.5
    return 0.003 + edge * (0.011 + 0.004 * n + 0.012 * b)


def pepperoni_layout(off, n_wedge=8, seed=3):
    """Pepperoni positions (x, y, rz): three per wedge, clear of the cut lines
    at angles off + k * 2pi / n_wedge, so every slice sits inside one wedge."""
    rng = random.Random(seed)
    out = []
    dw = TAU / n_wedge
    for k in range(n_wedge):
        bis = off + (k + 0.5) * dw
        for r, d in ((0.48, 0.0), (0.83, 0.19), (0.83, -0.19)):
            rr = r + rng.uniform(-0.02, 0.02)
            a = bis + d + rng.uniform(-0.02, 0.02)
            out.append((rr * math.cos(a), rr * math.sin(a), rng.uniform(0, TAU), k))
    return out


def round_board(name, coll, R=1.5, h=0.07):
    prof = [(0, 0), (R - 0.03, 0), (R, 0.02), (R, h - 0.02), (R - 0.03, h), (0, h)]
    bm = bmesh.new()
    _revolve(bm, prof, 128)
    _box(bm, Vector((R + 0.32, 0, h / 2)), (0.78, 0.40, h))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    _mats(me, [M.wood()])
    o = new_obj(name, me, coll)
    bv = o.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.012
    bv.segments = 2
    bv.limit_method = "ANGLE"
    return o


ROUND_BOARD_TOP = 0.07


def floured_board(name, coll, s=4.2, h=0.12):
    bm = bmesh.new()
    _box(bm, Vector((0, 0, -h / 2)), (s, s * 0.9, h))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    _mats(me, [M.wood_floured()])
    o = new_obj(name, me, coll)
    bv = o.modifiers.new("Bevel", "BEVEL")
    bv.width = 0.04
    bv.segments = 4
    return o


def peel(name, coll, R=1.5):
    """Pizza peel: steel blade (top at z=0, centre at origin), long wooden
    handle along -Y."""
    prof = [(0, -0.012), (R - 0.02, -0.012), (R, -0.006), (R - 0.02, 0.0), (0, 0.0)]
    me = revolve_mesh(name, prof, 96)
    _mats(me, [M.brushed_steel()])
    o = new_obj(name, me, coll)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.07, radius2=0.06, depth=4.6,
                          matrix=Matrix.Translation((0, -R - 2.5, 0.02)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    _box(bm, Vector((0, -R - 0.12, -0.004)), (0.3, 0.36, 0.024))
    for f in bm.faces:
        f.smooth = True
    hm = bpy.data.meshes.new(name + "_handle")
    bm.to_mesh(hm)
    bm.free()
    _mats(hm, [M.wood()])
    h = new_obj(name + "_handle", hm, coll)
    h.parent = o
    return o


def cutter(name, coll, R=0.36):
    """Pizza wheel.  Root origin at the wheel centre; the wheel turns about
    local X (child object `<name>_wheel`); handle trails back (-Y) and up."""
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    prof = [(0, -0.03), (0.07, -0.03), (0.08, -0.008), (R - 0.03, -0.006), (R, 0.0), (R - 0.03, 0.006),
            (0.08, 0.008), (0.07, 0.03), (0, 0.03)]
    me = _once("cutter_wheel", lambda: revolve_mesh("cutter_wheel", prof, 96))
    if not me.materials:
        _mats(me, [M.steel()])
    wh = new_obj(name + "_wheel", me, coll)
    wh.parent = root
    wh.rotation_mode = "XYZ"
    wh.rotation_euler = (0, math.pi / 2, 0)
    wrap = bpy.data.objects.new(name + "_spin", None)
    coll.objects.link(wrap)
    wrap.parent = root
    wh.parent = wrap
    bm = bmesh.new()
    d = Vector((0, -math.cos(0.65), math.sin(0.65)))
    q = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.06, radius2=0.075, depth=1.25,
                          matrix=Matrix.Translation(d * (R + 0.75)) @ q)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.035, radius2=0.035, depth=R + 0.15,
                          matrix=Matrix.Translation(d * (R + 0.15) / 2) @ q)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.05, radius2=0.05, depth=0.1,
                          matrix=Matrix.Rotation(math.pi / 2, 4, "Y"))
    for f in bm.faces:
        f.smooth = True
    hm = bpy.data.meshes.new(name + "_handle")
    bm.to_mesh(hm)
    bm.free()
    _mats(hm, [M.plastic((0.06, 0.055, 0.05), 0.35)])
    h = new_obj(name + "_handle", hm, coll)
    h.parent = root
    return root, wrap


def dough_ball(name, coll, mat):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    for v in bm.verts:
        c = v.co
        k = 1 + 0.02 * mnoise.noise(c * 2.0)
        v.co = Vector((c.x * 0.5 * k, c.y * 0.5 * k, (c.z * 0.4 + 0.4) * k))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    _mats(me, [mat])
    return new_obj(name, me, coll)


def pepperoni_stick(name, coll, mat, L=1.1, r=0.17):
    prof = [(0, 0), (r * 0.7, 0.0), (r * 0.95, 0.03), (r, 0.08), (r, L - 0.06), (r * 0.9, L - 0.015), (r * 0.5, L),
            (0, L)]
    me = revolve_mesh(name, prof, 48, rfn=lambda th, z: 1 + 0.015 * math.sin(5 * th + z * 9))
    for p in me.polygons:
        p.use_smooth = True
    _mats(me, [mat])
    return new_obj(name, me, coll)


def flour_mound(name, coll, R=0.62, h=0.32):
    def zf(r):
        return h * max(0.0, 1 - (r / R) ** 2) ** 0.9
    me = _disc(name, R, 0.0, 24, 96, zf)
    for v in me.vertices:
        c = v.co
        v.co.z += 0.02 * mnoise.noise(Vector((c.x * 6, c.y * 6, 1.0))) * min(1.0, (R - math.hypot(c.x, c.y)) * 6)
    _mats(me, [M.flour()])
    return new_obj(name, me, coll)


# ------------------------------------------------------------------ oven ---
OVEN_R = 4.5
OVEN_WALL_Y = -3.4
ARCH_W, ARCH_H = 1.9, 1.95


def oven(name, coll):
    """Wood-fired dome oven: brick dome, stone floor, a front wall with an
    arched mouth (boolean), logs at the back left.  Returns root empty."""
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=OVEN_R)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < OVEN_WALL_Y - 0.3], context="FACES")
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name + "_dome")
    bm.to_mesh(me)
    bm.free()
    _mats(me, [M.brick()])
    dome = new_obj(name + "_dome", me, coll)
    dome.parent = root
    fl = new_obj(name + "_floor", _disc(name + "_floor", OVEN_R + 0.6, 0.0, 12, 96), coll)
    fl.data.materials.append(M.oven_stone())
    fl.parent = root
    # front wall with an arched mouth
    bm = bmesh.new()
    _box(bm, Vector((0, OVEN_WALL_Y - 0.25, 1.0)), (9.0, 0.5, 5.6))
    me = bpy.data.meshes.new(name + "_wall")
    bm.to_mesh(me)
    bm.free()
    _mats(me, [M.brick()])
    wall = new_obj(name + "_wall", me, coll)
    wall.parent = root
    pts = []
    for k in range(33):
        a = math.pi * k / 32
        pts.append((ARCH_W * math.cos(a), 1.25 + (ARCH_H - 1.25) * math.sin(a)))
    pts = [(ARCH_W, -0.02)] + pts + [(-ARCH_W, -0.02)]
    bm = bmesh.new()
    front = [bm.verts.new((x, OVEN_WALL_Y + 0.6, z)) for x, z in pts]
    back = [bm.verts.new((x, OVEN_WALL_Y - 1.2, z)) for x, z in pts]
    bm.faces.new(front)
    bm.faces.new(back[::-1])
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], back[i], back[j], front[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    cm = bpy.data.meshes.new(name + "_cutter")
    bm.to_mesh(cm)
    bm.free()
    cut = new_obj(name + "_cutter", cm, coll)
    cut.parent = root
    cut.hide_render = True
    cut.hide_viewport = True
    bo = wall.modifiers.new("Arch", "BOOLEAN")
    bo.operation = "DIFFERENCE"
    bo.solver = "EXACT"
    bo.object = cut
    # logs + ember bed at the back left
    bm = bmesh.new()
    for (x, y, rz, L) in ((-2.3, 2.1, 0.5, 1.5), (-1.9, 2.5, -0.4, 1.4), (-2.1, 2.3, 1.6, 1.2)):
        m = Matrix.Translation((x, y, 0.14)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "Y")
        bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.14, radius2=0.12, depth=L, matrix=m)
    lm = bpy.data.meshes.new(name + "_logs")
    bm.to_mesh(lm)
    bm.free()
    _mats(lm, [M.embers()])
    logs = new_obj(name + "_logs", lm, coll)
    logs.parent = root
    return root


def flame_tongue(name, coll, r=0.22, h=1.3, seed=0):
    rng = random.Random(seed)
    bm = bmesh.new()
    rings, seg = 14, 16
    rows = []
    for i in range(rings + 1):
        t = i / rings
        rad = r * (1 - t) ** 0.8 * (0.6 + 0.4 * math.sin(math.pi * min(1.0, t * 1.6 + 0.2)))
        row = []
        for j in range(seg):
            a = TAU * j / seg
            row.append(bm.verts.new((rad * math.cos(a), rad * math.sin(a), h * t)))
        rows.append(row)
    for i in range(rings):
        for j in range(seg):
            k = (j + 1) % seg
            bm.faces.new((rows[i][j], rows[i][k], rows[i + 1][k], rows[i + 1][j]))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    hv = np.array([v.co.z / h for v in me.vertices], dtype=np.float32)
    a = me.attributes.new("h", "FLOAT", "POINT")
    a.data.foreach_set("value", hv)
    _mats(me, [M.flame()])
    o = new_obj(name, me, coll)
    for at in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_shadow",
               "visible_volume_scatter"):
        setattr(o, at, False)
    mod = o.modifiers.new("Flicker", "NODES")
    mod.node_group = fx.flame_group()
    fx.set_inputs(o, mod, {"Seed": rng.uniform(0, 100), "Height": h})
    return o
