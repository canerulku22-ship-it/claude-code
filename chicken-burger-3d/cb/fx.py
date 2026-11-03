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


# ------------------------------------------------------------ crispy crust --
def crust_group():
    if "crust" in _groups:
        return _groups["crust"]
    ng, nb, gin, gout = _gn("FX_Crust")
    _in(ng, "Coat", default=1.0)
    _in(ng, "Level", "NodeSocketInt", 2)
    sub = nb.node("GeometryNodeSubdivisionSurface")
    nb.set(nb.sock(sub, "Mesh"), gin.outputs["Geometry"])
    nb.set(nb.sock(sub, "Level"), gin.outputs["Level"])
    pos = nb.out(nb.node("GeometryNodeInputPosition"))

    def noise(vec, scale, detail, rough, out=0):
        n = nb.node("ShaderNodeTexNoise")
        nb.set(nb.sock(n, "Vector"), vec)
        nb.set(nb.sock(n, "Scale"), scale)
        nb.set(nb.sock(n, "Detail"), detail)
        nb.set(nb.sock(n, "Roughness"), rough)
        return n.outputs[out]
    # domain warp -> irregular, flaky clusters instead of uniform bumps
    warp = nb.vm("SUBTRACT", noise(pos, 3.0, 2.0, 0.5, out=1), (0.5, 0.5, 0.5))
    p2 = nb.vadd(pos, nb.vscale(warp, 0.35))
    base = noise(p2, 8.0, 6.0, 0.58)
    ridge = nb.m("SUBTRACT", 1.0, nb.mul(nb.m("ABSOLUTE", nb.sub(noise(p2, 5.0, 4.0, 0.6), 0.5)), 2.0))
    vo = nb.node("ShaderNodeTexVoronoi", {"feature": "F1"})
    nb.set(nb.sock(vo, "Vector"), p2)
    nb.set(nb.sock(vo, "Scale"), 13.0)
    d = nb.sock(vo, "Distance", out=True)
    mounds = nb.m("SUBTRACT", 1.0, nb.smoothstep(0.0, 0.75, d))
    crag = nb.add(nb.mul(nb.sub(base, 0.5), 2.6), 0.5)
    crag = nb.add(crag, nb.mul(nb.sub(mounds, 0.5), 0.7))
    crag = nb.m("ADD", crag, nb.mul(nb.sub(nb.m("POWER", ridge, 4.0), 0.3), 0.6), clamp_=True)
    amt = nb.mul(nb.add(nb.mul(crag, 0.036), 0.006), gin.outputs["Coat"])
    nrm = nb.out(nb.node("GeometryNodeInputNormal"))
    sp = nb.node("GeometryNodeSetPosition")
    nb.set(nb.sock(sp, "Geometry"), nb.out(sub))
    nb.set(nb.sock(sp, "Offset"), nb.vscale(nrm, amt))
    st = nb.node("GeometryNodeStoreNamedAttribute", {"data_type": "FLOAT", "domain": "POINT"})
    nb.set(nb.sock(st, "Geometry"), nb.out(sp))
    nb.set(nb.sock(st, "Name"), "crag")
    nb.set(nb.sock(st, "Value"), nb.mul(crag, gin.outputs["Coat"]))
    nb.links.new(nb.out(st), gout.inputs[0])
    _groups["crust"] = ng
    return ng


def add_crust(obj, coat=1.0, level=2):
    g = crust_group()
    mod = obj.modifiers.new("Crust", "NODES")
    mod.node_group = g
    set_inputs(obj, mod, {"Coat": coat, "Level": level})
    return mod


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
