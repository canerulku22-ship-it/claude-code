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


# --------------------------------------------------------------- liquids ---
def sauce_surface(name, coll, radius, z=0.0, rings=34, seg=128, amp=0.012):
    """Chunky tomato-sauce surface (origin at its mean height)."""
    me = _disc(name, radius, 0.0, rings, seg)
    for v in me.vertices:
        c = v.co
        r = math.hypot(c.x, c.y) / radius
        edge = min(1.0, (1 - r) * 8)
        v.co.z = amp * edge * (mnoise.noise(Vector((c.x * 7, c.y * 7, 0.3))) +
                               0.5 * mnoise.noise(Vector((c.x * 19, c.y * 19, 1.7))))
    _mats(me, [M.tomato_sauce()])
    o = new_obj(name, me, coll)
    o.location.z = z
    fx.add_ripple(o, amp=0.002, scale=6.0, speed=0.02)
    return o


def sauce_cap(name, coll, radius, height, base_fn):
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
    _mats(me, [M.tomato_sauce()])
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
