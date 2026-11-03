"""Procedural 3D food & prop models.  1 Blender unit = 10 cm."""
import math
import random
import bmesh
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion, noise as mnoise

from . import materials as M
from . import fx


# --------------------------------------------------------------- helpers ---
def new_obj(name, data, coll=None):
    o = bpy.data.objects.new(name, data)
    if coll is not None:
        coll.objects.link(o)
    return o


def _revolve(bm, prof, seg=64):
    rings = []
    for r, z in prof:
        if r < 1e-6:
            rings.append([bm.verts.new((0.0, 0.0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg),
                                        r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
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


def revolve_mesh(name, prof, seg=64, matfn=None, closed=True):
    bm = bmesh.new()
    faces = _revolve(bm, prof, seg)
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


# ------------------------------------------------------------------ buns ---
BUN_BOTTOM_H = 0.20
BUN_TOP_H = 0.39

_mesh_cache = {}


def _once(key, fn):
    if key not in _mesh_cache:
        _mesh_cache[key] = fn()
    return _mesh_cache[key]


def bun_bottom_mesh():
    def mk():
        prof = [(0, 0), (0.40, 0), (0.49, 0.006), (0.535, 0.025), (0.552, 0.055), (0.558, 0.10),
                (0.555, 0.145), (0.545, 0.175), (0.53, 0.193), (0.505, 0.200), (0.3, 0.203), (0, 0.204)]
        me = revolve_mesh("bun_bottom", prof, 72, lambda c: 1 if c.z > 0.197 else 0)
        _mats(me, [M.bun_crust(False), M.bun_crumb()])
        return me
    return _once("bun_bottom", mk)


def _dome(t):
    a = t * math.pi / 2
    r = 0.565 * max(math.cos(a), 0.0) ** 0.62
    z = 0.03 + 0.36 * math.sin(a) ** 0.85
    return r, z


def bun_top_mesh(seeds=70, seed=3):
    def mk():
        prof = [(0, 0), (0.40, 0.0), (0.50, 0.0), (0.535, 0.008), (0.555, 0.03)]
        prof += [_dome(t) for t in np.linspace(0, 1, 26)[1:]]
        prof[-1] = (0.0, prof[-1][1])
        bm = bmesh.new()
        faces = _revolve(bm, prof, 72)
        for f in faces:
            f.material_index = 1 if f.calc_center_median().z < 0.004 else 0
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        # sesame seeds scattered on the crown
        rng = random.Random(seed)
        pts = []
        tries = 0
        while len(pts) < seeds and tries < 5000:
            tries += 1
            t = rng.uniform(0.18, 0.98)
            phi = rng.uniform(0, 2 * math.pi)
            r, z = _dome(t)
            p = Vector((r * math.cos(phi), r * math.sin(phi), z))
            if any((p - q).length < 0.075 for q, _ in pts):
                continue
            r2, z2 = _dome(min(t + 0.01, 1.0))
            r1, z1 = _dome(max(t - 0.01, 0.0))
            dr, dz = r2 - r1, z2 - z1
            # outward normal of the dome
            n = Vector((math.cos(phi) * abs(dz), math.sin(phi) * abs(dz), abs(dr))).normalized()
            pts.append((p, n))
        for p, n in pts:
            q = n.to_track_quat("Z", "Y") @ Quaternion((0, 0, 1), rng.uniform(0, 6.28))
            mat = Matrix.Translation(p + n * 0.003) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((0.026, 0.0135, 0.0065, 1))
            res = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0, matrix=mat)
            for v in res["verts"]:
                for f in v.link_faces:
                    f.material_index = 2
                    f.smooth = True
        me = bpy.data.meshes.new("bun_top")
        bm.to_mesh(me)
        bm.free()
        _mats(me, [M.bun_crust(True), M.bun_crumb(), M.sesame()])
        return me
    return _once("bun_top", mk)


def bun_bottom(name, coll):
    return new_obj(name, bun_bottom_mesh(), coll)


def bun_top(name, coll):
    return new_obj(name, bun_top_mesh(), coll)


# --------------------------------------------------------------- chicken ---
CHICKEN_H = 0.19
CHICKEN_BOTTOM = 0.072


def chicken_mesh():
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=96, radius=1.0)
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


def chicken(name, coll, mat, coat=1.0, level=2):
    me = chicken_mesh()
    if not me.materials:
        me.materials.append(mat)
    o = new_obj(name, me, coll)
    # per-object material via object-linked slot (mesh is shared)
    o.material_slots[0].link = "OBJECT"
    o.material_slots[0].material = mat
    fx.add_crust(o, coat=coat, level=level)
    return o


# --------------------------------------------------------------- lettuce ---
def lettuce_mesh():
    def mk():
        bm = bmesh.new()
        rad_vals = []
        NR, NS = 26, 128
        for leaf, (rot, sc, dz, ph) in enumerate([(0.0, 1.0, 0.0, 0.0), (1.35, 0.93, 0.016, 1.9)]):
            center = bm.verts.new((0, 0, 0.012 + dz))
            rad_vals.append(0.0)
            rings = []
            for k in range(1, NR + 1):
                s = k / NR
                ring = []
                for i in range(NS):
                    th = 2 * math.pi * i / NS
                    R = 0.63 * sc * (1 + 0.05 * math.sin(5 * th + 1 + ph) + 0.035 * math.sin(11 * th + 0.3 + ph)
                                     + 0.02 * math.sin(17 * th + ph))
                    r = s * R
                    a0 = th + rot
                    nn = mnoise.noise(Vector((math.cos(a0) * 2.2, math.sin(a0) * 2.2, ph + s * 1.5)))
                    ruffle = 0.05 * s ** 2.0 * (0.55 * math.sin(11 * th + 3.0 * math.sin(3 * th + ph) + 4 * s)
                                                + 0.9 * nn)
                    droop = -0.6 * max(0.0, s - 0.8) ** 2
                    nz = 0.012 * mnoise.noise(Vector((math.cos(th + rot) * r * 4, math.sin(th + rot) * r * 4, ph)))
                    z = 0.012 + dz + ruffle + 0.02 * s + droop + nz
                    a = th + rot
                    ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
                    rad_vals.append(s)
                rings.append(ring)
            for i in range(NS):
                j = (i + 1) % NS
                bm.faces.new((center, rings[0][i], rings[0][j]))
            for a, b in zip(rings[:-1], rings[1:]):
                for i in range(NS):
                    j = (i + 1) % NS
                    bm.faces.new((a[i], b[i], b[j], a[j]))
        for f in bm.faces:
            f.smooth = True
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("lettuce")
        bm.to_mesh(me)
        bm.free()
        att = me.attributes.new("rad", "FLOAT", "POINT")
        att.data.foreach_set("value", np.array(rad_vals, dtype=np.float32))
        _mats(me, [M.lettuce()])
        return me
    return _once("lettuce", mk)


def lettuce(name, coll):
    o = new_obj(name, lettuce_mesh(), coll)
    s = o.modifiers.new("Solidify", "SOLIDIFY")
    s.thickness = 0.007
    s.offset = 0
    return o


# ---------------------------------------------------------------- cheese ---
def cheese(name, coll, drape_target=0.45):
    n = 40
    size = 0.94
    xs = np.linspace(-size / 2, size / 2, n + 1)
    verts = [(x, y, 0.0) for y in xs for x in xs]
    faces = [(j * (n + 1) + i, j * (n + 1) + i + 1, (j + 1) * (n + 1) + i + 1, (j + 1) * (n + 1) + i)
             for j in range(n) for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.shade_smooth()
    _mats(me, [M.cheese()])
    o = new_obj(name, me, coll)
    o.shape_key_add(name="Basis", from_mix=False)
    sk = o.shape_key_add(name="drape", from_mix=False)
    co = np.array(verts)
    rho = np.sqrt(co[:, 0] ** 2 + co[:, 1] ** 2)
    t = np.clip((rho - drape_target) / 0.22, 0, 1)
    t = t * t * (3 - 2 * t)
    th = np.arctan2(co[:, 1], co[:, 0])
    dz = -0.075 * t ** 1.5 - 0.008 * np.sin(6 * th) * t
    shrink = 1 - 0.03 * t
    new = np.stack([co[:, 0] * shrink, co[:, 1] * shrink, co[:, 2] + dz], 1)
    sk.data.foreach_set("co", new.astype(np.float32).ravel())
    s = o.modifiers.new("Solidify", "SOLIDIFY")
    s.thickness = 0.02
    s.offset = 1.0
    sub = o.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    return o


# ----------------------------------------------------------------- sauce ---
def sauce_spiral(name, coll, color, turns=3.2, r0=0.42, r1=0.04, z=0.018, depth=0.032, n=260):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = depth
    cu.bevel_resolution = 5
    cu.use_fill_caps = True
    cu.bevel_factor_mapping_end = "SPLINE"
    sp = cu.splines.new("POLY")
    sp.points.add(n - 1)
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a = 2 * math.pi * turns * t
        r = (r0 + (r1 - r0) * t) * (1 + 0.035 * math.sin(7 * a))
        p = (r * math.cos(a), r * math.sin(a), z + 0.006 * math.sin(3 * a))
        sp.points[i].co = (*p, 1.0)
        sp.points[i].radius = 0.85 + 0.25 * (0.5 + 0.5 * math.sin(5 * a + 1))
        pts.append(p)
    cu.materials.append(M.sauce(tuple(color)))
    o = new_obj(name, cu, coll)
    o["path"] = [c for p in pts for c in p]
    return o


def spiral_point(o, t):
    pts = o["path"]
    n = len(pts) // 3
    i = min(int(t * (n - 1)), n - 1)
    return Vector(pts[3 * i:3 * i + 3])


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


def round_board(name, coll, r=0.9, h=0.08):
    prof = [(0, 0), (r - 0.05, 0), (r - 0.02, 0.01), (r, 0.04), (r - 0.02, h - 0.01), (r - 0.05, h), (0, h)]
    me = revolve_mesh(name, [(a, b - h) for a, b in prof], 72)
    _mats(me, [M.wood()])
    return new_obj(name, me, coll)


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


def _disc(name, radius, z, rings=24, seg=96, zfn=None):
    prof = []
    for k in range(rings + 1):
        r = radius * k / rings
        prof.append((r, z if zfn is None else zfn(r)))
    me = revolve_mesh(name, prof, seg, closed=False)
    for p in me.polygons:
        p.use_smooth = True
    return me


def egg_liquid(name, coll):
    me = _disc(name, 0.772, DISH_LIQ_Z, 20, 96)
    _mats(me, [M.egg_liquid()])
    o = new_obj(name, me, coll)
    fx.add_ripple(o, amp=0.0)
    return o


def flour_mound(name, coll):
    def z(r):
        s = r / 0.74
        return 0.085 + 0.13 * max(0.0, 1 - s * s) ** 1.2
    prof = [(0.74 * k / 30, z(0.74 * k / 30)) for k in range(31)]
    bm = bmesh.new()
    _revolve(bm, prof, 96)
    for v in bm.verts:
        v.co.z += 0.014 * mnoise.noise(v.co * 6.0) + 0.006 * mnoise.noise(v.co * 25.0)
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    _mats(me, [M.flour()])
    return new_obj(name, me, coll)


POT_OIL_Z = 0.46


def pot(name, coll):
    prof = [(0, 0), (0.85, 0), (0.92, 0.03), (0.95, 0.1), (0.95, 0.58), (0.945, 0.615), (0.925, 0.632),
            (0.905, 0.625), (0.89, 0.6), (0.89, 0.1), (0.85, 0.06), (0, 0.06)]
    me = revolve_mesh(name, prof, 96)
    _mats(me, [M.cast_iron()])
    return new_obj(name, me, coll)


def oil_surface(name, coll):
    me = _disc(name, 0.893, POT_OIL_Z, 40, 128)
    _mats(me, [M.oil()])
    o = new_obj(name, me, coll)
    fx.add_ripple(o, amp=0.004, scale=5.0)
    return o


def shaker(name, coll):
    prof = [(0, 0), (0.10, 0), (0.12, 0.012), (0.125, 0.04), (0.125, 0.30), (0.12, 0.33), (0.112, 0.342),
            (0.119, 0.346), (0.119, 0.42), (0.112, 0.434), (0.08, 0.44), (0.0, 0.441)]
    me = _once("shaker", lambda: revolve_mesh("shaker", prof, 48, lambda c: 1 if c.z > 0.343 else 0))
    if not me.materials:
        _mats(me, [M.plastic((0.72, 0.10, 0.05), 0.35), M.shaker_cap()])
    return new_obj(name, me, coll)


def squeeze_bottle(name, coll, color):
    prof = [(0, 0), (0.10, 0), (0.125, 0.015), (0.132, 0.05), (0.132, 0.46), (0.12, 0.52), (0.085, 0.565),
            (0.07, 0.575), (0.078, 0.58), (0.078, 0.66), (0.04, 0.67), (0.03, 0.72), (0.012, 0.82),
            (0.0, 0.822)]

    def mf(c):
        return 0 if c.z < 0.577 else 1
    me = revolve_mesh(name, prof, 48, mf)
    _mats(me, [M.plastic(tuple(color), 0.28), M.plastic((0.95, 0.94, 0.92), 0.4)])
    o = new_obj(name, me, coll)
    o.shape_key_add(name="Basis", from_mix=False)
    sk = o.shape_key_add(name="squeeze", from_mix=False)
    co = np.zeros(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    z = co[:, 2]
    k = np.where((z > 0.06) & (z < 0.47), np.sin(np.pi * np.clip((z - 0.06) / 0.41, 0, 1)), 0.0)
    s = 1 - 0.32 * k
    co[:, 0] *= s
    co[:, 1] *= s
    sk.data.foreach_set("co", co.ravel())
    return o


def tongs(name, coll):
    """Two steel arms hinged at the top; returns (root_empty, arm_l, arm_r)."""
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    arms = []
    for side in (-1, 1):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            # long thin strip from hinge (z=1.3) down to the tip (z=0)
            v.co = (v.co.x * 0.055, v.co.y * 0.014, (v.co.z + 0.5) * 1.3)
        me = bpy.data.meshes.new(f"{name}_arm")
        bm.to_mesh(me)
        bm.free()
        _mats(me, [M.steel()])
        hinge = bpy.data.objects.new(f"{name}_hinge{side}", None)
        coll.objects.link(hinge)
        hinge.parent = root
        hinge.location = (0, 0, 1.3)
        a = new_obj(f"{name}_arm{side}", me, coll)
        a.parent = hinge
        a.location = (0, 0, -1.3)
        bv = a.modifiers.new("Bevel", "BEVEL")
        bv.width = 0.005
        bv.segments = 2
        arms.append(hinge)
    return root, arms[0], arms[1]


# ------------------------------------------------------------ prototypes ---
def proto_objects(coll):
    """Particle instance prototypes (hidden from all ray types)."""
    out = {}
    rng = random.Random(7)

    def chunk(name, subdiv, jitter, mat):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        for v in bm.verts:
            v.co *= 1 + rng.uniform(-jitter, jitter)
        for f in bm.faces:
            f.smooth = subdiv > 1
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        _mats(me, [mat])
        o = new_obj(name, me, coll)
        _hide_proto(o)
        return o

    out["spice"] = chunk("proto_spice", 1, 0.35, M.spice())
    out["flour"] = chunk("proto_flour", 1, 0.3, M.flour())
    out["crumb"] = chunk("proto_crumb", 2, 0.4, M.crumb())

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

    out["drop"] = sphere("proto_drop", M.droplet())
    out["egg_drop"] = sphere("proto_egg_drop", M.egg_liquid())
    out["bubble"] = sphere("proto_bubble", M.bubble(), 20, 12)
    out["seed"] = sphere("proto_seed", M.sesame(), 10, 6)

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


# --------------------------------------------------------------- burger ----
LAYER_ROT = {"cheese": 0.55, "lettuce": 0.3}
LAYER_H = {"bun_bottom": 0.20, "sauce": 0.022, "lettuce": 0.03, "cheese": 0.018,
           "chicken": 0.19, "bun_top": 0.39}


def stack_heights(order):
    z, out = 0.0, {}
    for k in order:
        out[k] = z
        z += LAYER_H[k]
    return out, z


def burger(prefix, coll, order, sauce_color, chicken_mat=None, level=2):
    """Build every layer as its own object (origin at the layer's base)."""
    objs = {}
    for k in order:
        n = f"{prefix}_{k}"
        if k == "bun_bottom":
            o = bun_bottom(n, coll)
        elif k == "bun_top":
            o = bun_top(n, coll)
        elif k == "sauce":
            o = sauce_spiral(n, coll, sauce_color)
            o.scale = (1, 1, 0.75)
        elif k == "lettuce":
            o = lettuce(n, coll)
        elif k == "cheese":
            o = cheese(n, coll)
            o.data.shape_keys.key_blocks["drape"].value = 1.0
        elif k == "chicken":
            o = chicken(n, coll, chicken_mat or M.chicken_fried(), coat=1.0, level=level)
        objs[k] = o
    return objs
