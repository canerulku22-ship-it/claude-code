"""Geometry-Nodes effects.

All particle systems are *analytic*: positions are computed from the scene
frame inside the node tree (no simulation cache / baking needed), so any
frame can be rendered independently and the .blend is fully self-contained.
"""
import math
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from .util import NB

_groups = {}


def _gn(name):
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nb = NB(ng)
    gin = nb.node("NodeGroupInput")
    gout = nb.node("NodeGroupOutput")
    return ng, nb, gin, gout


def _in(ng, name, typ="NodeSocketFloat", default=None):
    s = ng.interface.new_socket(name=name, in_out="INPUT", socket_type=typ)
    if default is not None:
        s.default_value = default
    return s


def ident(group, name):
    return group.interface.items_tree[name].identifier


def _input(mod, name):
    """Blender 5.x stores GN modifier inputs in mod.properties.inputs."""
    return getattr(mod.properties.inputs, ident(mod.node_group, name))


def set_inputs(obj, mod, values):
    for k, v in values.items():
        _input(mod, k).value = v


def key_input(obj, mod_name, name, f, v):
    mod = obj.modifiers[mod_name]
    _input(mod, name).value = v
    obj.keyframe_insert(f'modifiers["{mod_name}"].properties.inputs.{ident(mod.node_group, name)}.value', frame=f)


def _attr(nb, name, typ="FLOAT"):
    n = nb.node("GeometryNodeInputNamedAttribute", {"data_type": typ})
    nb.set(nb.sock(n, "Name"), name)
    return nb.sock(n, "Attribute", out=True)


def _frame(nb):
    return nb.sock(nb.node("GeometryNodeInputSceneTime"), "Frame", out=True)


# ------------------------------------------------------------------ pasta --
def _pasta_tail(ng, nb, gin, gout, geo):
    """Edge chains -> round noodle tubes with the group's radius and material."""
    m2c = nb.node("GeometryNodeMeshToCurve")
    nb.set(nb.sock(m2c, "Mesh"), geo)
    rad = nb.node("GeometryNodeSetCurveRadius")
    nb.set(nb.sock(rad, "Curve"), nb.out(m2c))
    nb.set(nb.sock(rad, "Radius"), gin.outputs["Radius"])
    prof = nb.node("GeometryNodeCurvePrimitiveCircle")
    nb.set(nb.sock(prof, "Resolution"), 6)
    nb.set(nb.sock(prof, "Radius"), 1.0)
    c2m = nb.node("GeometryNodeCurveToMesh")
    nb.set(nb.sock(c2m, "Curve"), nb.out(rad))
    nb.set(nb.sock(c2m, "Profile Curve"), nb.out(prof))
    nb.set(nb.sock(c2m, "Scale"), nb.out(nb.node("GeometryNodeInputRadius")))
    nb.set(nb.sock(c2m, "Fill Caps"), True)
    sm = nb.node("GeometryNodeSetShadeSmooth")
    nb.set(nb.sock(sm, "Geometry"), nb.out(c2m))
    mt = nb.node("GeometryNodeSetMaterial")
    nb.set(nb.sock(mt, "Geometry"), nb.out(sm))
    nb.set(nb.sock(mt, "Material"), gin.outputs["Material"])
    nb.links.new(nb.out(mt), gout.inputs[0])


def _pasta_inputs(ng):
    _in(ng, "Radius", default=0.0095)
    _in(ng, "Material", "NodeSocketMaterial")


def pasta_static_group():
    if "pasta_static" in _groups:
        return _groups["pasta_static"]
    ng, nb, gin, gout = _gn("FX_Pasta")
    _pasta_inputs(ng)
    _pasta_tail(ng, nb, gin, gout, gin.outputs["Geometry"])
    _groups["pasta_static"] = ng
    return ng


def pasta_dry_group():
    """Dry spaghetti dropped into boiling water.

    Each strand is an arc from its base point: lean a0 from vertical and a
    constant curvature k.  Fan leans the bundle out against the rim; Soft
    leans and curls the strands so they slump and sink, swirling round the
    pot.  A smooth radial clamp keeps them inside the pot wall.
    point attrs: s (0..1 along), L, th (azimuth), bx, by (base), rnd
    """
    if "pasta_dry" in _groups:
        return _groups["pasta_dry"]
    ng, nb, gin, gout = _gn("FX_PastaDry")
    _pasta_inputs(ng)
    for nm, dv in (("Fan", 0.0), ("Soft", 0.0), ("Drop", 0.0), ("Swirl", 0.6), ("Rmax", 0.85),
                   ("Zmin", 0.07), ("BaseZ", 0.07)):
        _in(ng, nm, default=dv)
    g = gin.outputs
    s, L, th, bx, by, rnd = (_attr(nb, k) for k in ("s", "L", "th", "bx", "by", "rnd"))
    sig = nb.mul(s, L)
    a0 = nb.add(nb.mul(g["Fan"], nb.add(0.30, nb.mul(rnd, 0.08))), nb.mul(g["Soft"], nb.add(1.25, nb.mul(rnd, 0.3))))
    kk = nb.div(nb.add(nb.mul(g["Soft"], nb.add(2.0, nb.mul(rnd, 1.5))), 0.02), L)
    phi = nb.add(a0, nb.mul(kk, sig))
    h = nb.div(nb.sub(nb.m("COSINE", a0), nb.m("COSINE", phi)), kk)
    v = nb.div(nb.sub(nb.m("SINE", phi), nb.m("SINE", a0)), kk)
    thz = nb.add(th, nb.mul(nb.mul(nb.mul(g["Soft"], g["Swirl"]), sig), nb.add(0.6, nb.mul(rnd, 0.8))))
    x = nb.add(bx, nb.mul(h, nb.m("COSINE", thz)))
    y = nb.add(by, nb.mul(h, nb.m("SINE", thz)))
    r = nb.add(nb.m("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y))), 1e-5)
    R0 = nb.sub(g["Rmax"], 0.12)
    over = nb.mx(nb.sub(r, R0), 0.0)
    rc = nb.add(nb.mn(r, R0), nb.mul(nb.m("TANH", nb.div(over, 0.12)), 0.12))
    k = nb.div(rc, r)
    x, y = nb.mul(x, k), nb.mul(y, k)
    z = nb.add(nb.add(g["BaseZ"], v), g["Drop"])
    z = nb.mx(z, nb.add(g["Zmin"], nb.mul(rnd, 0.012)))
    p = nb.xyz(x, y, z)
    nz = nb.node("ShaderNodeTexNoise")
    nb.set(nb.sock(nz, "Vector"), nb.vadd(nb.vscale(p, 3.0), nb.xyz(nb.mul(rnd, 7.0), 0.0, 0.0)))
    nb.set(nb.sock(nz, "Scale"), 1.0)
    nb.set(nb.sock(nz, "Detail"), 1.0)
    wig = nb.vscale(nb.vm("SUBTRACT", nz.outputs[1], (0.5, 0.5, 0.5)), nb.mul(g["Soft"], 0.05))
    sp = nb.node("GeometryNodeSetPosition")
    nb.set(nb.sock(sp, "Geometry"), g["Geometry"])
    nb.set(nb.sock(sp, "Position"), nb.vadd(p, wig))
    _pasta_tail(ng, nb, gin, gout, nb.out(sp))
    _groups["pasta_dry"] = ng
    return ng


def pasta_pile_group():
    """Cooked spaghetti that falls into the pan as a clump and gets tossed.

    point attrs: e (fall delay, frames), ta (toss amplitude), td (toss delay)
    The rest position is the settled pile.
    """
    if "pasta_pile" in _groups:
        return _groups["pasta_pile"]
    ng, nb, gin, gout = _gn("FX_PastaPile")
    _pasta_inputs(ng)
    for nm, dv in (("FallStart", 1.0), ("FallDur", 12.0), ("Height", 2.0), ("TossStart", 1e5),
                   ("TossDur", 14.0), ("TossAmp", 0.5)):
        _in(ng, nm, default=dv)
    _in(ng, "Center", "NodeSocketVector", (0.0, 0.0, 0.0))
    g = gin.outputs
    F = _frame(nb)
    e, ta, td = _attr(nb, "e"), _attr(nb, "ta"), _attr(nb, "td")
    tf = nb.m("DIVIDE", nb.sub(nb.sub(F, g["FallStart"]), e), g["FallDur"], clamp_=True)
    drop = nb.mul(g["Height"], nb.m("SUBTRACT", 1.0, nb.mul(tf, tf)))
    sq = nb.add(0.72, nb.mul(nb.mul(nb.mul(tf, tf), nb.m("SUBTRACT", 3.0, nb.mul(tf, 2.0))), 0.28))
    tt = nb.m("DIVIDE", nb.sub(nb.sub(F, g["TossStart"]), td), g["TossDur"], clamp_=True)
    toss = nb.mul(nb.mul(nb.mul(g["TossAmp"], ta), 4.0), nb.mul(tt, nb.m("SUBTRACT", 1.0, tt)))
    tsm = nb.mul(nb.mul(tt, tt), nb.m("SUBTRACT", 3.0, nb.mul(tt, 2.0)))
    ang = nb.mul(nb.mul(nb.sub(ta, 0.85), 0.9), tsm)
    pos = nb.out(nb.node("GeometryNodeInputPosition"))
    px, py, pz = nb.sep(pos)
    cx, cy, cz = nb.sep(g["Center"])
    dx, dy = nb.sub(px, cx), nb.sub(py, cy)
    ca, sa = nb.m("COSINE", ang), nb.m("SINE", ang)
    rx = nb.sub(nb.mul(dx, ca), nb.mul(dy, sa))
    ry = nb.add(nb.mul(dx, sa), nb.mul(dy, ca))
    x = nb.add(cx, nb.mul(rx, sq))
    y = nb.add(cy, nb.mul(ry, sq))
    z = nb.add(nb.add(pz, drop), toss)
    sp = nb.node("GeometryNodeSetPosition")
    nb.set(nb.sock(sp, "Geometry"), g["Geometry"])
    nb.set(nb.sock(sp, "Position"), nb.xyz(x, y, z))
    _pasta_tail(ng, nb, gin, gout, nb.out(sp))
    _groups["pasta_pile"] = ng
    return ng


# ----------------------------------------------------------------- ripple ---
def ripple_group():
    if "ripple" in _groups:
        return _groups["ripple"]
    ng, nb, gin, gout = _gn("FX_Ripple")
    _in(ng, "Amp", default=0.004)
    _in(ng, "Scale", default=5.0)
    _in(ng, "Speed", default=0.04)
    _in(ng, "RingAmp", default=0.0)
    _in(ng, "RingStart", default=1.0)
    _in(ng, "RingCenter", "NodeSocketVector", (0.0, 0.0, 0.0))
    F = _frame(nb)
    pos = nb.out(nb.node("GeometryNodeInputPosition"))
    nz = nb.node("ShaderNodeTexNoise", {"noise_dimensions": "4D"})
    nb.set(nb.sock(nz, "Vector"), pos)
    nb.set(nb.sock(nz, "W"), nb.mul(F, gin.outputs["Speed"]))
    nb.set(nb.sock(nz, "Scale"), gin.outputs["Scale"])
    nb.set(nb.sock(nz, "Detail"), 3.0)
    base = nb.mul(nb.mul(nb.sub(nz.outputs[0], 0.5), 2.0), gin.outputs["Amp"])
    # expanding ring wave from RingCenter after RingStart
    dist = nb.vm("DISTANCE", pos, gin.outputs["RingCenter"])
    age = nb.mx(nb.sub(F, gin.outputs["RingStart"]), 0.0)
    wave = nb.m("SINE", nb.sub(nb.mul(dist, 38.0), nb.mul(age, 0.9)))
    env = nb.mul(nb.m("EXPONENT", nb.mul(age, -0.06)), nb.m("EXPONENT", nb.mul(dist, -2.2)))
    front = nb.m("LESS_THAN", nb.mul(dist, 38.0), nb.add(nb.mul(age, 0.9), 1.5))
    ring = nb.mul(nb.mul(nb.mul(wave, env), front), gin.outputs["RingAmp"])
    on = nb.m("GREATER_THAN", F, gin.outputs["RingStart"])
    dz = nb.add(base, nb.mul(ring, on))
    sp = nb.node("GeometryNodeSetPosition")
    nb.set(nb.sock(sp, "Geometry"), gin.outputs["Geometry"])
    nb.set(nb.sock(sp, "Offset"), nb.xyz(0.0, 0.0, dz))
    nb.links.new(nb.out(sp), gout.inputs[0])
    _groups["ripple"] = ng
    return ng


def add_ripple(obj, amp=0.004, scale=5.0, speed=0.04):
    g = ripple_group()
    mod = obj.modifiers.new("Ripple", "NODES")
    mod.node_group = g
    set_inputs(obj, mod, {"Amp": amp, "Scale": scale, "Speed": speed})
    return mod


# ------------------------------------------------- ballistic particles -----
def ballistic_group():
    """Points with attributes p0, v0 (units/s), e (emit frame), land (frames
    of flight), life (frames before fading), fade (frames), s, sv, rot, spin.
    """
    if "ballistic" in _groups:
        return _groups["ballistic"]
    ng, nb, gin, gout = _gn("FX_Ballistic")
    _in(ng, "Instance", "NodeSocketObject")
    _in(ng, "Gravity", default=40.0)
    _in(ng, "FPS", default=30.0)
    _in(ng, "Drag", default=0.0)
    _in(ng, "ScaleMult", default=1.0)
    F = _frame(nb)
    age = nb.sub(F, _attr(nb, "e"))
    ta = nb.mn(nb.mx(age, 0.0), _attr(nb, "land"))
    t = nb.div(ta, gin.outputs["FPS"])
    dragf = nb.div(t, nb.add(1.0, nb.mul(gin.outputs["Drag"], t)))
    p = nb.vadd(_attr(nb, "p0", "FLOAT_VECTOR"), nb.vscale(_attr(nb, "v0", "FLOAT_VECTOR"), dragf))
    p = nb.vadd(p, nb.xyz(0.0, 0.0, nb.mul(nb.mul(nb.mul(t, t), gin.outputs["Gravity"]), -0.5)))
    sp = nb.node("GeometryNodeSetPosition")
    nb.set(nb.sock(sp, "Geometry"), gin.outputs["Geometry"])
    nb.set(nb.sock(sp, "Position"), p)
    kf = nb.m("SUBTRACT", 1.0, nb.m("DIVIDE", nb.sub(age, _attr(nb, "life")), _attr(nb, "fade"), clamp_=True))
    kf = nb.m("ADD", kf, 0.0, clamp_=True)
    kin = nb.m("DIVIDE", age, 2.0, clamp_=True)
    sc = nb.mul(nb.mul(nb.mul(_attr(nb, "s"), kf), kin), gin.outputs["ScaleMult"])
    rot = nb.vadd(_attr(nb, "rot", "FLOAT_VECTOR"), nb.vscale(_attr(nb, "spin", "FLOAT_VECTOR"), ta))
    return _finish_instancer(ng, nb, gin, gout, sp, sc, rot, "ballistic")


def _finish_instancer(ng, nb, gin, gout, sp, sc, rot, key, store_u=None):
    geo = nb.out(sp)
    if store_u is not None:
        st = nb.node("GeometryNodeStoreNamedAttribute", {"data_type": "FLOAT", "domain": "POINT"})
        nb.set(nb.sock(st, "Geometry"), geo)
        nb.set(nb.sock(st, "Name"), "u")
        nb.set(nb.sock(st, "Value"), store_u)
        geo = nb.out(st)
    dl = nb.node("GeometryNodeDeleteGeometry", {"domain": "POINT"})
    nb.set(nb.sock(dl, "Geometry"), geo)
    cmp = nb.node("FunctionNodeCompare", {"data_type": "FLOAT", "operation": "LESS_EQUAL"})
    nb.set(nb.sock(cmp, "A"), sc)
    nb.set(nb.sock(cmp, "B"), 1e-5)
    nb.set(nb.sock(dl, "Selection"), nb.sock(cmp, "Result", out=True))
    oi = nb.node("GeometryNodeObjectInfo")
    oi.transform_space = "ORIGINAL"
    nb.set(nb.sock(oi, "Object"), gin.outputs["Instance"])
    e2r = nb.node("FunctionNodeEulerToRotation")
    nb.set(nb.sock(e2r, "Euler"), rot)
    ip = nb.node("GeometryNodeInstanceOnPoints")
    nb.set(nb.sock(ip, "Points"), nb.out(dl))
    nb.set(nb.sock(ip, "Instance"), nb.sock(oi, "Geometry", out=True))
    nb.set(nb.sock(ip, "Rotation"), nb.out(e2r))
    nb.set(nb.sock(ip, "Scale"), nb.vscale(_attr(nb, "sv", "FLOAT_VECTOR"), sc))
    nb.links.new(nb.out(ip), gout.inputs[0])
    _groups[key] = ng
    return ng


# ------------------------------------------------------ looping particles --
def loop_group():
    """Cyclic particles (bubbles, steam, floating crumbs).
    attrs: p0, vel (units/frame), ph, per, s, sv, rot, spin, wob, wf, dens."""
    if "loop" in _groups:
        return _groups["loop"]
    ng, nb, gin, gout = _gn("FX_Loop")
    _in(ng, "Instance", "NodeSocketObject")
    _in(ng, "Density", default=1.0)
    _in(ng, "ScaleMult", default=1.0)
    _in(ng, "PopShape", default=0.0)
    F = _frame(nb)
    ph = _attr(nb, "ph")
    per = _attr(nb, "per")
    age = nb.m("FLOORED_MODULO", nb.add(F, ph), per)
    u = nb.div(age, per)
    wf = _attr(nb, "wf")
    wob = _attr(nb, "wob")
    wx = nb.mul(nb.m("SINE", nb.add(nb.mul(F, wf), ph)), wob)
    wy = nb.mul(nb.m("COSINE", nb.add(nb.mul(nb.mul(F, wf), 1.3), nb.mul(ph, 1.7))), wob)
    p = nb.vadd(_attr(nb, "p0", "FLOAT_VECTOR"), nb.vscale(_attr(nb, "vel", "FLOAT_VECTOR"), age))
    p = nb.vadd(p, nb.xyz(wx, wy, 0.0))
    sp = nb.node("GeometryNodeSetPosition")
    nb.set(nb.sock(sp, "Geometry"), gin.outputs["Geometry"])
    nb.set(nb.sock(sp, "Position"), p)
    prof_sine = nb.m("POWER", nb.mx(nb.m("SINE", nb.mul(u, math.pi)), 0.0), 0.7)
    prof_pop = nb.mul(nb.m("SQRT", u), nb.m("SUBTRACT", 1.0, nb.smoothstep(0.84, 1.0, u)))
    prof = nb.mixf(gin.outputs["PopShape"], prof_sine, prof_pop)
    vis = nb.m("LESS_THAN", _attr(nb, "dens"), gin.outputs["Density"])
    sc = nb.mul(nb.mul(nb.mul(_attr(nb, "s"), prof), vis), gin.outputs["ScaleMult"])
    rot = nb.vadd(_attr(nb, "rot", "FLOAT_VECTOR"), nb.vscale(_attr(nb, "spin", "FLOAT_VECTOR"), age))
    return _finish_instancer(ng, nb, gin, gout, sp, sc, rot, "loop", store_u=u)


# --------------------------------------------------------- point objects ---
def points_object(name, coll, attrs, group, inputs, parent=None):
    p0 = np.asarray(attrs["p0"], dtype=np.float32)
    n = len(p0)
    me = bpy.data.meshes.new(name)
    me.vertices.add(n)
    me.vertices.foreach_set("co", p0.ravel())
    for k, arr in attrs.items():
        arr = np.asarray(arr, dtype=np.float32)
        if arr.ndim == 2:
            a = me.attributes.new(k, "FLOAT_VECTOR", "POINT")
            a.data.foreach_set("vector", arr.ravel())
        else:
            a = me.attributes.new(k, "FLOAT", "POINT")
            a.data.foreach_set("value", arr)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    mod = o.modifiers.new("FX", "NODES")
    mod.node_group = group
    set_inputs(o, mod, inputs)
    if parent is not None:
        o.parent = parent
    return o


def bvh_from_mesh(me, matrix=None):
    verts = [(matrix @ v.co) if matrix else v.co.copy() for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(verts, polys)


def landing(p0, v0, g, fps=30.0, drag=0.0, bvh=None, floor_z=None, max_frames=120.0, step=0.5):
    """Frames of flight until each trajectory hits the BVH or floor plane."""
    n = len(p0)
    land = np.full(n, max_frames, dtype=np.float32)
    for i in range(n):
        P0 = Vector(p0[i])
        V0 = Vector(v0[i])

        def pos(fr):
            t = fr / fps
            k = t / (1 + drag * t)
            return P0 + V0 * k + Vector((0, 0, -0.5 * g * t * t))
        prev = pos(0.0)
        fr = step
        while fr <= max_frames:
            cur = pos(fr)
            hit = False
            if bvh is not None:
                d = cur - prev
                L = d.length
                if L > 1e-9:
                    loc, nrm, idx, dist = bvh.ray_cast(prev, d / L, L)
                    if loc is not None:
                        land[i] = fr - step + step * (dist / L)
                        hit = True
            if not hit and floor_z is not None and cur.z <= floor_z and prev.z > floor_z:
                land[i] = fr - step + step * (prev.z - floor_z) / max(prev.z - cur.z, 1e-9)
                hit = True
            if hit:
                break
            prev = cur
            fr += step
    return land


def face_camera_euler(points, cam_loc):
    out = []
    for p in points:
        d = Vector(cam_loc) - Vector(p)
        q = d.to_track_quat("Z", "Y")
        out.append(tuple(q.to_euler()))
    return np.array(out, dtype=np.float32)


def rand_unit(rng, n):
    v = rng.normal(size=(n, 3))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


# ------------------------------------------------------------------ flame ---
def flame_group():
    """Flickering flame tongue: noise sway that grows towards the tip."""
    if "flame" in _groups:
        return _groups["flame"]
    ng, nb, gin, gout = _gn("FX_Flame")
    _in(ng, "Seed", default=0.0)
    _in(ng, "Height", default=1.0)
    F = _frame(nb)
    pos = nb.out(nb.node("GeometryNodeInputPosition"))
    _, _, pz = nb.sep(pos)
    h = nb.m("DIVIDE", pz, gin.outputs["Height"], clamp_=True)
    nz = nb.node("ShaderNodeTexNoise", {"noise_dimensions": "4D"})
    nb.set(nb.sock(nz, "Vector"), nb.vadd(nb.vscale(pos, 1.3), nb.xyz(gin.outputs["Seed"], 0.0, 0.0)))
    nb.set(nb.sock(nz, "W"), nb.add(nb.mul(F, 0.14), gin.outputs["Seed"]))
    nb.set(nb.sock(nz, "Scale"), 1.0)
    nb.set(nb.sock(nz, "Detail"), 2.0)
    cx, cy, cz = nb.sep(nb.vm("SUBTRACT", nz.outputs[1], (0.5, 0.5, 0.5)))
    w = nb.mul(nb.m("POWER", h, 1.3), 0.55)
    off = nb.xyz(nb.mul(cx, w), nb.mul(cy, w), nb.mul(nb.mul(cz, h), 0.5))
    sp = nb.node("GeometryNodeSetPosition")
    nb.set(nb.sock(sp, "Geometry"), gin.outputs["Geometry"])
    nb.set(nb.sock(sp, "Offset"), off)
    nb.links.new(nb.out(sp), gout.inputs[0])
    _groups["flame"] = ng
    return ng


# ------------------------------------------------------------ cheese pull ---
def cheese_pull_group():
    """Molten-cheese strings between the pizza and a slice being lifted.

    Edge chains; point attrs: a (fixed end, object space), bl (slice end, in
    the slice object's space), u (0..1 along), brk (stretch at which the
    string snaps), rr (radius scale), sd (seed).  The slice object's live
    transform (Object Info, relative) places the moving end, so the strings
    follow whatever animation the slice has.  Strings sag and thin as they
    stretch, then snap from the middle out.
    """
    if "cheese_pull" in _groups:
        return _groups["cheese_pull"]
    ng, nb, gin, gout = _gn("FX_CheesePull")
    _in(ng, "Slice", "NodeSocketObject")
    _in(ng, "Radius", default=0.012)
    _in(ng, "Sag", default=0.35)
    _in(ng, "Material", "NodeSocketMaterial")
    g = gin.outputs
    oi = nb.node("GeometryNodeObjectInfo")
    oi.transform_space = "RELATIVE"
    nb.set(nb.sock(oi, "Object"), g["Slice"])
    tp = nb.node("FunctionNodeTransformPoint")
    nb.set(nb.sock(tp, "Vector"), _attr(nb, "bl", "FLOAT_VECTOR"))
    nb.set(nb.sock(tp, "Transform"), nb.sock(oi, "Transform", out=True))
    a = _attr(nb, "a", "FLOAT_VECTOR")
    wb = nb.sock(tp, "Vector", out=True)
    d = nb.vm("SUBTRACT", wb, a)
    L = nb.vm("LENGTH", d)
    u = _attr(nb, "u")
    mid = nb.mul(nb.mul(u, nb.m("SUBTRACT", 1.0, u)), 4.0)
    p = nb.vadd(a, nb.vscale(d, u))
    nz = nb.node("ShaderNodeTexNoise")
    nb.set(nb.sock(nz, "Vector"), nb.xyz(nb.mul(u, 2.5), _attr(nb, "sd"), 0.0))
    nb.set(nb.sock(nz, "Scale"), 1.0)
    nb.set(nb.sock(nz, "Detail"), 1.0)
    wig = nb.vscale(nb.vm("SUBTRACT", nz.outputs[1], (0.5, 0.5, 0.5)), nb.mul(nb.mul(mid, L), 0.12))
    sag = nb.xyz(0.0, 0.0, nb.mul(nb.mul(nb.mul(mid, L), g["Sag"]), -1.0))
    p = nb.vadd(nb.vadd(p, sag), wig)
    sp = nb.node("GeometryNodeSetPosition")
    nb.set(nb.sock(sp, "Geometry"), g["Geometry"])
    nb.set(nb.sock(sp, "Position"), p)
    # radius: thins in the middle as it stretches; snaps from the middle out
    r_end = nb.mul(g["Radius"], _attr(nb, "rr"))
    thin = nb.div(0.3, nb.add(0.3, L))
    shape = nb.m("POWER", mid, 0.7)
    rad = nb.mul(r_end, nb.mixf(shape, 1.0, thin))
    gbrk = nb.smoothstep(_attr(nb, "brk"), nb.add(_attr(nb, "brk"), 0.25), L)
    c = nb.sub(nb.mul(gbrk, 1.1), 0.1)
    x = nb.m("ABSOLUTE", nb.sub(nb.mul(u, 2.0), 1.0))
    rad = nb.mul(rad, nb.smoothstep(c, nb.add(c, 0.1), x))
    rad = nb.mul(rad, nb.smoothstep(0.004, 0.04, L))
    m2c = nb.node("GeometryNodeMeshToCurve")
    nb.set(nb.sock(m2c, "Mesh"), nb.out(sp))
    sr = nb.node("GeometryNodeSetCurveRadius")
    nb.set(nb.sock(sr, "Curve"), nb.out(m2c))
    nb.set(nb.sock(sr, "Radius"), rad)
    prof = nb.node("GeometryNodeCurvePrimitiveCircle")
    nb.set(nb.sock(prof, "Resolution"), 8)
    nb.set(nb.sock(prof, "Radius"), 1.0)
    c2m = nb.node("GeometryNodeCurveToMesh")
    nb.set(nb.sock(c2m, "Curve"), nb.out(sr))
    nb.set(nb.sock(c2m, "Profile Curve"), nb.out(prof))
    nb.set(nb.sock(c2m, "Scale"), nb.out(nb.node("GeometryNodeInputRadius")))
    nb.set(nb.sock(c2m, "Fill Caps"), True)
    sm = nb.node("GeometryNodeSetShadeSmooth")
    nb.set(nb.sock(sm, "Geometry"), nb.out(c2m))
    mt = nb.node("GeometryNodeSetMaterial")
    nb.set(nb.sock(mt, "Geometry"), nb.out(sm))
    nb.set(nb.sock(mt, "Material"), g["Material"])
    nb.links.new(nb.out(mt), gout.inputs[0])
    _groups["cheese_pull"] = ng
    return ng


def strands_object(name, coll, chains, attrs, group, inputs, parent=None):
    """Edge-chain mesh: chains = list of (k,3) point arrays; attrs = dict of
    per-point arrays (same total length)."""
    verts, edges = [], []
    for ch in chains:
        b = len(verts)
        verts.extend(map(tuple, ch))
        edges.extend((b + i, b + i + 1) for i in range(len(ch) - 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, edges, [])
    for k, arr in attrs.items():
        arr = np.asarray(arr, dtype=np.float32)
        if arr.ndim == 2:
            at = me.attributes.new(k, "FLOAT_VECTOR", "POINT")
            at.data.foreach_set("vector", arr.ravel())
        else:
            at = me.attributes.new(k, "FLOAT", "POINT")
            at.data.foreach_set("value", arr)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    mod = o.modifiers.new("FX", "NODES")
    mod.node_group = group
    set_inputs(o, mod, inputs)
    if parent is not None:
        o.parent = parent
    return o
