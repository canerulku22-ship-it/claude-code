"""'Kaiju' episode scene: Pepperoni Rex vs London (see hmtb/kaiju.py for the beats).

Builds the London set, the monster and every prop, animates them from the episode's
moments, sets up one camera per beat, and returns the sound events (stomps, flung
buses, the bite, slices, pineapples, splashes) for the soundtrack.
"""

import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import camera, london_set as L, pizza_kaiju, studio, toon
from . import materials as M
from .skyscraper import dusk_world, sun
from .util import box_bmesh, cylinder_bmesh, empty, mesh_from_bmesh, new_object, reset_scene, set_keys, \
    set_track, set_visibility

G = (25.0, -10.0)                                   # where it erupts and rises
P1 = (45.0, 131.0)                                  # where it stands to bite Big Ben
DIVE = (30.0, 40.0)


def _ballistic(obj, start_f, end_f, p0, v0, g=14.7, spin=(0, 0, 0), floor=None, hide_after=None):
    frames = np.arange(start_f - 1, end_f + 1)
    loc = np.zeros((len(frames), 3))
    rot = np.zeros((len(frames), 3))
    landed = None
    for i, f in enumerate(frames):
        t = max(0.0, (f - start_f) / 30.0)
        p = Vector(p0) + Vector(v0) * t + Vector((0, 0, -0.5 * g * t * t))
        if floor is not None and p.z < floor:
            if landed is None:
                landed = int(f)
            p.z = floor
            q = loc[i - 1] if i else p
            p.x, p.y = q[0], q[1]
            rot[i] = rot[i - 1] if i else 0
        else:
            rot[i] = (spin[0] * t, spin[1] * t, spin[2] * t)
        loc[i] = p
    for axis in range(3):
        set_track(obj, "location", frames, loc[:, axis], index=axis)
        set_track(obj, "rotation_euler", frames, rot[:, axis], index=axis)
    return landed


def _sphere(name, r, mat, segs=(16, 10)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=r)
    me = mesh_from_bmesh(name, bm, smooth=True)
    me.materials.append(mat)
    return new_object(name, me)


def _ring(name, mat, minor=0.03):
    """Flat unit torus (radius 1) for ripples and shockwaves."""
    bm = bmesh.new()
    seg, ring = 64, 6
    rows = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        rows.append([bm.verts.new(((1 + minor * math.cos(b)) * math.cos(a), (1 + minor * math.cos(b)) * math.sin(a),
                                   minor * 0.4 * math.sin(b))) for b in (2 * math.pi * j / ring for j in range(ring))])
    for i in range(seg):
        for j in range(ring):
            r0, r1 = rows[i], rows[(i + 1) % seg]
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % ring], r0[(j + 1) % ring]))
    me = mesh_from_bmesh(name, bm, smooth=True)
    me.materials.append(mat)
    return new_object(name, me)


def _expand_ring(o, at, centre, r0, r1, frames):
    fr = list(range(at - 1, at + frames + 1))
    rs = [r0 if f < at else r0 + (r1 - r0) * min(1.0, (f - at) / float(frames)) ** 0.7 for f in fr]
    o.location = (centre[0], centre[1], centre[2])
    for axis in (0, 1, 2):
        set_track(o, "scale", fr, rs, index=axis)
    set_visibility(o, [(at, at + frames)])


# ---------------------------------------------------------------------------
# Props
# ---------------------------------------------------------------------------

def geyser_props(tl, rng, events):
    """River bubbles, then a gooey cheese geyser: a stream of blobs rising up a column,
    a mushrooming crown, globs and pepperoni flung out, and ripples when the monster rises."""
    m = tl.moments
    cheese = M.principled("GeyserCheese", color=(1.0, 0.74, 0.22), roughness=0.35, coat=0.2,
                          emission=(1.0, 0.6, 0.1), emission_strength=0.45)
    water = M.principled("Foam", color=(0.85, 0.92, 0.95), roughness=0.2, emission=(0.8, 0.9, 1.0),
                         emission_strength=0.3)
    props = []
    for i in range(30):
        b = _sphere("CheeseBubble", 1.0, cheese, segs=(14, 9))
        r = 45 * math.sqrt(rng.random())
        a = rng.uniform(0, 2 * math.pi)
        b.location = (G[0] + r * math.cos(a), G[1] + r * math.sin(a), 0.0)
        keys = {m["bubbles"] - 1: 0.001}
        for c in range(3):
            t0 = m["bubbles"] + rng.randint(0, m["geyser"] - m["bubbles"] - 14)
            size = rng.uniform(4.0, 10.0) * (1.0 - r / 70.0)
            keys.update({t0: 0.001, t0 + 6: size, t0 + 11: size * 1.12, t0 + 12: 0.001})
        fr = sorted(keys)
        for axis in range(3):
            set_keys(b, "scale", fr, [keys[f] * (0.6 if axis == 2 else 1.0) for f in fr], index=axis)
        set_visibility(b, [(m["bubbles"], m["geyser"] + 5)])
        props.append(b)
    events.append({"type": "bubbles", "frame": m["bubbles"]})

    gs, ge = m["geyser"], m["rise_start"] + 24
    top_h = 175.0

    def height(f):
        grow = min(1.0, max(0.0, (f - gs) / 9.0))
        fall = 1.0 - min(1.0, max(0.0, (f - (ge - 24)) / 24.0))
        return top_h * (grow ** 0.7) * fall * (1 + 0.05 * math.sin(f * 0.9))

    fr = list(range(gs - 1, ge + 1))
    n = 48
    for i in range(n):
        b = _sphere("GeyserBlob", 1.0, cheese, segs=(14, 9))
        xs, ys, zs, ss = [], [], [], []
        for f in fr:
            h = height(f)
            p = ((f - gs) * 0.045 + i / float(n)) % 1.0          # position up the column, wraps
            r = (11.5 + 1.8 * math.sin(i * 1.7 + f * 0.31)) * (0.8 + 0.45 * p)
            if p > 0.88:
                r *= max(0.0, (1.0 - p) / 0.12)                # swallowed by the crown
            r *= min(1.0, h / 40.0)
            xs.append(G[0] + 3.0 * math.sin(f * 0.4 + i))
            ys.append(G[1] + 3.0 * math.cos(f * 0.37 + i * 1.3))
            zs.append(p * h)
            ss.append(max(0.001, r))
        set_track(b, "location", fr, xs, index=0)
        set_track(b, "location", fr, ys, index=1)
        set_track(b, "location", fr, zs, index=2)
        for axis in range(3):
            set_track(b, "scale", fr, [v * (1.15 if axis == 2 else 1.0) for v in ss], index=axis)
        set_visibility(b, [(gs, ge)])
        props.append(b)
    for i in range(9):                                       # the crown on top
        b = _sphere("GeyserCrown", 1.0, cheese, segs=(14, 9))
        a0 = 2 * math.pi * i / 9
        xs, ys, zs, ss = [], [], [], []
        for f in fr:
            h = height(f)
            spread = 14.0 + 4.0 * math.sin(f * 0.5 + i)
            xs.append(G[0] + spread * math.cos(a0 + f * 0.05))
            ys.append(G[1] + spread * math.sin(a0 + f * 0.05))
            zs.append(h - 4.0 + 3.0 * math.sin(f * 0.6 + i * 2.0))
            ss.append(max(0.001, (13.0 + 3.0 * math.sin(f * 0.45 + i)) * min(1.0, h / 60.0)))
        set_track(b, "location", fr, xs, index=0)
        set_track(b, "location", fr, ys, index=1)
        set_track(b, "location", fr, zs, index=2)
        for axis in range(3):
            set_track(b, "scale", fr, [v * (0.8 if axis == 2 else 1.0) for v in ss], index=axis)
        set_visibility(b, [(gs, ge)])
        props.append(b)
    base = _sphere("GeyserBase", 1.0, cheese, segs=(24, 10))
    base.location = (G[0], G[1], 0.0)
    for axis, k in ((0, 1.0), (1, 1.0), (2, 0.18)):
        set_track(base, "scale", fr, [max(0.001, k * (24.0 + 3.0 * math.sin(f * 0.8)) * min(1.0, height(f) / 50.0))
                                      for f in fr], index=axis)
    set_visibility(base, [(gs, ge)])
    props.append(base)
    events.append({"type": "geyser", "frame": gs})
    for i in range(26):                                      # globs and pepperoni flung from the top
        a = rng.uniform(0, 2 * math.pi)
        sp = rng.uniform(15, 50)
        start = gs + rng.randint(5, ge - gs - 30)
        if i % 3 == 0:
            o = new_object("FlyingPepperoni", mesh_from_bmesh("FlyingPepperoni", cylinder_bmesh(6.0, 1.4, segments=20)))
            o.data.materials.append(M.pepperoni())
        else:
            o = _sphere("CheeseGlob", rng.uniform(3.0, 6.5), cheese, segs=(12, 8))
        _ballistic(o, start, start + 90, (G[0], G[1], height(start) - 5), (math.cos(a) * sp, math.sin(a) * sp,
                                                                             rng.uniform(5, 30)),
                   g=22.0, spin=(rng.uniform(-6, 6), rng.uniform(-6, 6), 0), floor=-12.0)
        set_visibility(o, [(start, start + 90)])
        props.append(o)
    for k, delay in enumerate((0, 14, 30)):
        ring = _ring("RiseRipple", water)
        _expand_ring(ring, m["rise_start"] + delay, (G[0], G[1], 0.3), 15.0, 190.0, 70)
        props.append(ring)
    events.append({"type": "rise", "frame": m["rise_start"]})
    return props


def fling_vehicles(vehicles, ch, plants, tl, rng, events):
    """Buses and cabs on the bridge get kicked into the river as the monster passes."""
    m = tl.moments
    for v in vehicles:
        vy = v.location.y
        launch = None
        for f in range(m["walk_start"], m["walk_end"]):
            if abs(ch["root.y"][f] - vy) < 16:
                launch = f
                break
        if launch is None:
            continue
        p0 = (v.location.x, v.location.y, v.location.z)
        v0 = (rng.uniform(14, 26), rng.uniform(-8, 8), rng.uniform(22, 34))
        landed = _ballistic(v, launch, launch + 75, p0, v0, g=16.0,
                            spin=(rng.uniform(-5, 5), rng.uniform(-6, 6), rng.uniform(-4, 4)), floor=-12.0)
        events.append({"type": "fling", "frame": launch, "heavy": v.name.startswith("Bus")})
        if landed:
            events.append({"type": "water_hit", "frame": landed - 6})


def bite_props(top, top_parts, tl, rng, events):
    b = tl.moments["bite"]
    for o in [top] + top_parts:
        set_visibility(o, [(-10, b + 1)])
    stone = M.principled("Rubble", color=(0.78, 0.64, 0.42), roughness=0.8)
    props = []
    for i in range(18):
        chunk = new_object("BigBenRubble", mesh_from_bmesh("BigBenRubble", box_bmesh(*(rng.uniform(1.5, 3.5),) * 3)))
        chunk.data.materials.append(stone)
        p0 = (L.BIG_BEN.x + rng.uniform(-5, 5), L.BIG_BEN.y + rng.uniform(-5, 5), L.BIG_BEN.z + rng.uniform(62, 72))
        v0 = (rng.uniform(-12, 12), rng.uniform(-12, 12), rng.uniform(-2, 10))
        _ballistic(chunk, b + 1, b + 70, p0, v0, g=14.0, spin=(rng.uniform(-6, 6),) * 3, floor=L.LAND_Z + 1.0)
        set_visibility(chunk, [(b + 1, 10 ** 7)])
        props.append(chunk)
    events.append({"type": "bite", "frame": b})
    for k in range(4):
        events.append({"type": "chew", "frame": b + 8 + k * 7})
    return props


def eye_props(hub, slice_row, tl, rng, events):
    """Stomp shockwave, then the wheel snaps off and rolls east slicing buildings."""
    s = tl.moments["stomp"]
    roll = tl.moments["eye_roll"]
    shock = M.principled("Shockwave", color=(1.0, 0.85, 0.4), roughness=0.5, emission=(1.0, 0.75, 0.3),
                         emission_strength=3.0)
    dust = M.principled("SliceDustMat", color=(0.55, 0.45, 0.38), roughness=1.0)
    ring = _ring("StompShockwave", shock, minor=0.012)
    _expand_ring(ring, s, (P1[0], P1[1], L.LAND_Z + 1.0), 20.0, 750.0, 40)
    events.append({"type": "stomp_big", "frame": s})
    end = tl.segments["eye"][1] + 5
    fr = list(range(s, end + 1))
    xs, zs, rys, rxs = [], [], [], []
    for f in fr:
        if f < roll:
            k = max(0.0, (f - (s + 8)) / float(roll - s - 8))
            xs.append(L.EYE_HUB.x)
            zs.append(L.EYE_HUB.z)
            rys.append(0.05 * math.sin(f * 1.7) * k)
            rxs.append(0.03 * math.sin(f * 1.3) * k)
        else:
            u = (f - roll) / float(end - roll)
            drop = min(1.0, (f - roll) / 8.0)
            x = L.EYE_HUB.x + 720.0 * (u ** 1.5)
            xs.append(x)
            zs.append(L.EYE_HUB.z - (L.EYE_HUB.z - (L.EYE_R + L.LAND_Z)) * drop)
            rys.append((x - L.EYE_HUB.x) / L.EYE_R)
            rxs.append(0.05 * math.sin(f * 0.8))
    set_track(hub, "location", fr, xs, index=0)
    set_track(hub, "location", fr, zs, index=2)
    set_track(hub, "rotation_euler", fr, rys, index=1)
    set_track(hub, "rotation_euler", fr, rxs, index=0)
    track = dict(zip(fr, xs))

    def wheel_x(f):
        return track.get(f, xs[0] if f < fr[0] else xs[-1])

    events.append({"type": "eye_detach", "frame": roll})
    events.append({"type": "eye_roll", "frame": roll + 4, "until": end})
    for bx, pair in zip(L.SLICE_XS, slice_row):
        hit = next((f for f, x in zip(fr, xs) if x >= bx - 30), None)
        if hit is None:
            continue
        events.append({"type": "slice", "frame": hit})
        for side, half in zip((-1, 1), pair):
            # The halves part, then topple away from the cut (the front one towards the camera).
            f2 = list(range(hit - 1, hit + 31))
            u = [min(1.0, max(0.0, (f - hit) / 28.0)) for f in f2]
            set_track(half, "location", f2, [L.SLICE_Y + side * 16.0 * (k ** 0.6) for k in u], index=1)
            set_track(half, "location", f2, [L.LAND_Z - 3.0 * k for k in u], index=2)
            set_track(half, "rotation_euler", f2, [-side * 1.25 * (k ** 2.2) for k in u], index=0)
        for i in range(6):                                   # a puff of dust where it hit
            d = _sphere("SliceDust", 1.0, dust, segs=(10, 6))
            d.location = (bx + rng.uniform(-25, 25), L.SLICE_Y + rng.uniform(-25, 25), L.LAND_Z + 4)
            fr2 = [hit - 1, hit + 3, hit + 30]
            for axis in range(3):
                set_keys(d, "scale", fr2, [0.01, rng.uniform(6, 10), rng.uniform(16, 22)], index=axis,
                         interpolation="BEZIER")
            set_keys(d, "location", fr2, [L.LAND_Z + 2, L.LAND_Z + 8, L.LAND_Z + 22], index=2, interpolation="BEZIER")
            set_visibility(d, [(hit, hit + 30)])
    return wheel_x


def pineapple_template():
    body_mat, fresh = M.new_material("PineappleSkin")
    if fresh:
        nt = body_mat.node_tree
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs[0], out.inputs[0])
        tex = nt.nodes.new("ShaderNodeTexCoord")
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.feature = "DISTANCE_TO_EDGE"
        vor.inputs["Scale"].default_value = 6.0
        nt.links.new(tex.outputs["Object"], vor.inputs["Vector"])
        ramp = M._ramp(nt, [(0.0, (0.35, 0.22, 0.05)), (0.08, (0.85, 0.62, 0.12)), (0.3, (0.95, 0.75, 0.2))])
        nt.links.new(vor.outputs["Distance"], ramp.inputs[0])
        nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.6
    leaf = M.principled("PineappleLeaf", color=(0.12, 0.45, 0.12), roughness=0.5)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=14, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.5, 0.5, 0.7), verts=bm.verts)
    me = mesh_from_bmesh("Pineapple", bm, smooth=True)
    me.materials.append(body_mat)
    me.materials.append(leaf)
    bm = bmesh.new()
    bm.from_mesh(me)
    for k in range(9):
        a = 2 * math.pi * k / 9
        tilt = 0.35 + 0.25 * (k % 2)
        tip = Vector((math.cos(a) * tilt, math.sin(a) * tilt, 1.0 + 0.35 * (k % 3)))
        base = Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.62))
        d = tip - base
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.09, radius2=0.0, depth=d.length)
        mtx = Matrix.Translation(base + d / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=mtx, verts=res["verts"])
        for f in {f for v in res["verts"] for f in v.link_faces}:
            f.material_index = 1
    bm.to_mesh(me)
    bm.free()
    return me


def pineapple_props(tl, rng, events):
    m = tl.moments
    me = pineapple_template()
    props = []
    for k in range(11):
        o = new_object("Pineapple", me)
        s = rng.uniform(18, 26)
        o.scale = (s, s, s)
        land = m["pineapples"] + k * 4 + rng.randint(0, 3)
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(15, 75)
        x, y = P1[0] + r * math.cos(a), P1[1] + r * math.sin(a) * 0.7
        fall = 34
        g = 2 * 480.0 / (fall / 30.0) ** 2
        start = land - fall
        z_floor = (L.LAND_Z if y > L.BANK_Y else -6.0) + 0.7 * s
        frames = list(range(start - 1, land + 30))
        zs = []
        for f in frames:
            t = (f - start) / 30.0
            if f <= land:
                zs.append(max(z_floor, z_floor + 480.0 - 0.5 * g * t * t))
            else:
                tt = (f - land) / 30.0
                zs.append(z_floor + max(0.0, 26.0 * tt - 0.5 * 140.0 * tt * tt))
        o.location = (x, y, z_floor + 480)
        set_track(o, "location", frames, zs, index=2)
        set_keys(o, "rotation_euler", [start, land + 30], [rng.uniform(-0.4, 0.4), rng.uniform(-0.6, 0.6)],
                 index=0, interpolation="BEZIER")
        set_visibility(o, [(start, 10 ** 7)])
        events.append({"type": "pineapple_land", "frame": land})
        props.append(o)
    events.append({"type": "gag", "frame": m["gag"]})
    return props


def splash_props(tl, rng, events):
    sf = tl.moments["splash"]
    foam = M.principled("SplashFoam", color=(0.85, 0.93, 1.0), roughness=0.2, emission=(0.8, 0.9, 1.0),
                        emission_strength=0.5)
    props = []
    for i in range(46):
        d = _sphere("SplashDrop", rng.uniform(2.5, 6.0), foam, segs=(10, 6))
        a = rng.uniform(0, 2 * math.pi)
        sp = rng.uniform(10, 40)
        start = sf + rng.randint(0, 6)
        vz = rng.uniform(25, 50)
        land = start + int(30 * 2 * vz / 45.0) + 2
        gone = min(land, tl.hold_f - 4)            # nothing in the air on the frozen end frame
        _ballistic(d, start, land + 2, (DIVE[0], DIVE[1], 5.0), (math.cos(a) * sp, math.sin(a) * sp, vz),
                   g=45.0, floor=-10.0)
        set_visibility(d, [(start, max(start + 6, gone))])
        props.append(d)
    for k, delay in enumerate((0, 8, 16)):
        ring = _ring("SplashRing", foam)
        _expand_ring(ring, sf + delay, (DIVE[0], DIVE[1], 0.4), 20.0, 150.0, 30)
        props.append(ring)
    events.append({"type": "splash", "frame": sf})
    return props


# ---------------------------------------------------------------------------
# Cameras
# ---------------------------------------------------------------------------

def _cam(name, lens, keys):
    """Camera with (frame, location, target) keys."""
    cam = camera.make_camera(name, lens=lens)
    cam.data.clip_start = 0.5
    cam.data.clip_end = 12000.0
    prev = None
    for f, loc, target in keys:
        cam.location = loc
        q = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
        cam.rotation_euler = q.to_euler("XYZ", prev) if prev else q.to_euler()
        prev = cam.rotation_euler.copy()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    return cam


RISE_CAM = (100.0, -125.0)
LATE_CAM = (190.0, -40.0)
# Keep city blocks off the camera positions and sight lines (see london_set.build_city).
KEEP_CLEAR = [(-110.0, -170.0, 80.0), (30.0, 150.0, 330.0, 420.0),
              (170.0, -560.0, 1260.0, -262.0, 13.0),       # low rooftops in front of the Eye camera
              (170.0, -520.0, 1260.0, -420.0)]             # and nothing right under it


def build_cameras(tl, ch, plants, wheel_x):
    s = tl.segments
    m = tl.moments
    cams = {}
    cams["hook"] = _cam("CamHook", 36, [(s["hook"][0], (290, -40, 58), (15, 150, 56)),
                                         (s["hook"][1], (262, -24, 52), (15, 150, 56))])
    g = m["geyser"]
    cams["erupt"] = _cam("CamErupt", 34, [(s["erupt"][0], (-112, -172, 52), (15, 10, 12)),
                                           (g - 2, (-104, -162, 49), (18, 4, 16)),
                                           (g + 22, (-100, -156, 48), (25, -10, 78)),
                                           (s["erupt"][1], (-96, -150, 47), (25, -10, 84))])
    # Looks up above the head so the monster sits lower and the name card has the sky.
    cams["rise"] = _cam("CamRise", 28, [(s["rise"][0], (102, -128, 14), (25, -10, 55)),
                                         (m["roar"], (98, -122, 12), (25, -10, 96)),
                                         (s["rise"][1], (92, -114, 13), (25, -10, 92))])
    keys = []
    for f in range(s["bridge"][0], s["bridge"][1] + 1, 6):
        rx, ry = ch["root.x"][f], ch["root.y"][f]
        keys.append((f, (rx + 200, ry - 120, 40), (rx, ry, 62)))
    cams["bridge"] = _cam("CamBridge", 30, keys)
    cams["bite"] = _cam("CamBite", 36, [(s["bite"][0], (252, 332, 96), (40, 160, 84)),
                                         (s["bite"][1], (238, 318, 92), (40, 160, 80))])
    roll = m["eye_roll"]
    keys = [(s["eye"][0], (440, -480, 70), (220, -60, 72)), (roll - 2, (420, -478, 68), (290, -150, 68))]
    for f in range(roll + 8, s["eye"][1] + 1, 4):
        wx = wheel_x(f)
        keys.append((f, (wx + 10, -470, 62), (wx + 45, -180, 56)))
    cams["eye"] = _cam("CamEye", 24, keys)
    cams["pineapple"] = _cam("CamPineapple", 26, [(s["pineapple"][0], (205, -52, 48), (45, 131, 80)),
                                                   (m["pineapples"] - 30, (195, -44, 46), (45, 131, 100)),
                                                   (m["gag"], (190, -40, 45), (45, 131, 84)),
                                                   (m["dive"] + 10, (182, -32, 42), (38, 90, 46)),
                                                   (s["pineapple"][1], (176, -26, 40), (30, 40, 18))])
    cams["end"] = _cam("CamEnd", 34, [(s["end"][0], (278, -48, 96), (25, 145, 36)),
                                       (s["end"][1], (300, -62, 106), (25, 145, 36))])
    # Shakes on the big hits.
    camera.add_shake(cams["erupt"], g, 30, 1.5, scale=1.3)
    camera.add_shake(cams["rise"], m["rise_start"], 40, 0.8, scale=1.2)
    camera.add_shake(cams["rise"], m["roar"], 50, 0.8, scale=1.2)
    for f in plants:
        camera.add_shake(cams["bridge"], f, 10, 1.4, scale=1.1)
    camera.add_shake(cams["bite"], m["bite"], 14, 0.6, scale=1.1)
    camera.add_shake(cams["eye"], m["stomp"], 26, 2.5, scale=1.2)
    camera.add_shake(cams["pineapple"], m["pineapples"], 50, 1.0, scale=1.2)
    camera.add_shake(cams["pineapple"], m["splash"], 22, 1.6, scale=1.2)
    return cams


# ---------------------------------------------------------------------------
# Whole scene
# ---------------------------------------------------------------------------

def build_scene(cfg, tl, width, height, samples):
    scene = reset_scene()
    scene.frame_start = 0
    scene.frame_end = tl.total_frames
    studio.setup_render(scene, width, height, samples)
    if hasattr(scene.eevee, "shadow_resolution_scale"):
        scene.eevee.shadow_resolution_scale = 0.5
    dusk_world(scene)
    rng = random.Random(cfg["seed"])
    key = sun("SunsetKey", -105.0, 9.0, 3.2, (1.0, 0.62, 0.38))
    key.data.specular_factor = 0.3              # no blinding sun glint on the river
    fill = sun("SkyFill", 150.0, 30.0, 1.6, (0.55, 0.65, 1.0), shadow=False)
    fill.data.specular_factor = 0.0

    ground = L.build_ground()
    parliament = L.build_parliament()
    ben_base, ben_top, ben_parts = L.build_big_ben()
    bridge = L.build_bridge()
    hub, wheel_parts, eye_legs = L.build_london_eye()
    skyline = L.build_skyline()
    city = L.build_city(rng, KEEP_CLEAR)
    slice_row = L.build_slice_row(rng)
    vehicles = L.build_vehicles(rng)

    rig = pizza_kaiju.build_monster()
    places = {"geyser": G, "bite_spot": P1, "rise_cam": RISE_CAM, "late_cam": LATE_CAM,
              "dive_spot": DIVE, "big_ben": (L.BIG_BEN.x, L.BIG_BEN.y), "bank_y": L.BANK_Y}
    ch, plants = pizza_kaiju.animate(rig, tl, places)

    events = [{"type": "bong", "frame": tl.moments["bong1"]}, {"type": "bong", "frame": tl.moments["bong2"]}]
    events += [{"type": "stomp", "frame": f} for f in plants]
    events.append({"type": "roar", "frame": tl.moments["roar"]})
    events.append({"type": "roar", "frame": tl.moments["stomp"] + 110, "small": True})
    events.append({"type": "roar", "frame": tl.moments["pineapples"] - 100, "small": True})
    props = geyser_props(tl, rng, events)
    fling_vehicles(vehicles, ch, plants, tl, rng, events)
    props += bite_props(ben_top, ben_parts, tl, rng, events)
    wheel_x = eye_props(hub, slice_row, tl, rng, events)
    pineapples = pineapple_props(tl, rng, events)
    props += splash_props(tl, rng, events)
    events.append({"type": "dive", "frame": tl.moments["dive"]})

    cams = build_cameras(tl, ch, plants, wheel_x)
    scene.camera = cams["hook"]

    studio.no_transparent_shadows()
    toon.outline_scene(rig.meshes, 1.9)                                   # rig units (x100)
    toon.outline_scene([parliament, ben_base, ben_top, eye_legs] + bridge + wheel_parts + skyline + city +
                       [h for pair in slice_row for h in pair], 150.0)
    toon.outline_scene(vehicles, 30.0)
    toon.outline_scene(pineapples, 5.6)
    toon.outline_scene([o for o in props if o.name.split(".")[0] in ("GeyserBlob", "GeyserCrown", "CheeseBubble")],
                       12.0)                                              # unit spheres, scaled up
    toon.outline_scene([o for o in props if o.name.split(".")[0] in ("CheeseGlob", "FlyingPepperoni",
                                                                     "BigBenRubble")], 120.0)
    events.sort(key=lambda e: e["frame"])
    return {"scene": scene, "cams": cams, "events": events}
