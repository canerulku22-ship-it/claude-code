"""Pepperoni Rex: an original pizza kaiju, built from parts on a simple bone rig.

Design: a stocky, upright dinosaur with cheese skin, sauce patches and pepperoni spots,
pizza slices stuck point-first along its spine and tail (crust edge up), glowing
pepperoni eyes, crust teeth, a hinged jaw with stringy cheese, stubby arms and thick
legs. Everything is modelled in "rig units" (1 unit = 100 m) under a scaled root.

The rig is a hierarchy of empties (hips, torso, neck, head, jaw, arms, legs, a
7-segment tail). ``animate()`` samples a pose for every frame from the episode's beats
(rise, roar, walk, bite, stomp, pineapple gag, dive) and keyframes it.

Forward is -Y in rig space; the monster's left is +X.
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from . import materials as M
from .util import empty, mesh_from_bmesh, new_object, set_track, set_visibility

SCALE = 100.0


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def skin_material():
    """Molten-cheese skin: browned in places, sauce patches, pepperoni spots."""
    mat, fresh = M.new_material("KaijuSkin")
    if not fresh:
        return mat
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 5.0
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    base = M._ramp(nt, [(0.30, (0.85, 0.45, 0.10)), (0.55, (1.0, 0.75, 0.22)), (0.75, (1.0, 0.85, 0.40))])
    nt.links.new(noise.outputs["Fac"], base.inputs[0])
    sauce_n = nt.nodes.new("ShaderNodeTexNoise")
    sauce_n.inputs["Scale"].default_value = 5.0
    nt.links.new(tex.outputs["Object"], sauce_n.inputs["Vector"])
    sauce = nt.nodes.new("ShaderNodeMath")
    sauce.operation = "GREATER_THAN"
    nt.links.new(sauce_n.outputs["Fac"], sauce.inputs[0])
    sauce.inputs[1].default_value = 0.62
    mix1 = nt.nodes.new("ShaderNodeMix")
    mix1.data_type = "RGBA"
    nt.links.new(sauce.outputs[0], mix1.inputs["Factor"])
    nt.links.new(base.outputs[0], mix1.inputs[6])
    mix1.inputs[7].default_value = (0.70, 0.07, 0.03, 1)
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 22.0
    nt.links.new(tex.outputs["Object"], vor.inputs["Vector"])
    spot = nt.nodes.new("ShaderNodeMath")
    spot.operation = "LESS_THAN"
    nt.links.new(vor.outputs["Distance"], spot.inputs[0])
    spot.inputs[1].default_value = 0.22
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    nt.links.new(spot.outputs[0], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs[2], mix2.inputs[6])
    mix2.inputs[7].default_value = (0.45, 0.05, 0.03, 1)
    nt.links.new(mix2.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    M._set(bsdf, "coat", 0.15)
    M._set(bsdf, "subsurface", 0.1)
    nt.links.new(mix2.outputs[2], M._input(bsdf, "emission"))
    bsdf.inputs["Emission Strength"].default_value = 0.12
    mat.diffuse_color = (1.0, 0.7, 0.2, 1)
    return mat


def eye_material():
    return M.principled("KaijuEye", color=(1.0, 0.8, 0.2), roughness=0.2, emission=(1.0, 0.8, 0.2),
                        emission_strength=5.0)


def mouth_material():
    return M.principled("KaijuMouth", color=(0.25, 0.02, 0.02), roughness=0.5)


# ---------------------------------------------------------------------------
# Geometry helpers (rig units, parent-local)
# ---------------------------------------------------------------------------

def _blob(name, parent, center, radii, mat, rot=None, segs=(24, 14)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
    bmesh.ops.scale(bm, vec=radii, verts=bm.verts)
    if rot is not None:
        bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    me = mesh_from_bmesh(name, bm, smooth=True)
    me.materials.append(mat)
    o = new_object(name, me)
    o.parent = parent
    return o


def _cone(bm, base, tip, r):
    d = Vector(tip) - Vector(base)
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=r, radius2=0.0, depth=d.length)
    m = Matrix.Translation(Vector(base) + d / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=m, verts=res["verts"])


def _parts(name, parent, build, mat, smooth=False):
    bm = bmesh.new()
    build(bm)
    me = mesh_from_bmesh(name, bm, smooth=smooth)
    me.materials.append(mat)
    o = new_object(name, me)
    o.parent = parent
    return o


def _slice_plate(name, parent, base, size, lean, skin, crust):
    """A pizza slice stuck point-first into the back, crust edge up (the dorsal plates)."""
    bm = bmesh.new()
    w, h, t = 0.075 * size, 0.17 * size, 0.018 * size
    verts = [bm.verts.new(p) for p in ((-t, 0, 0), (-t, -w, h), (-t, w, h), (t, 0, 0), (t, -w, h), (t, w, h))]
    bm.faces.new((verts[0], verts[1], verts[2]))
    bm.faces.new((verts[3], verts[5], verts[4]))
    bm.faces.new((verts[0], verts[3], verts[4], verts[1]))
    bm.faces.new((verts[0], verts[2], verts[5], verts[3]))
    bm.faces.new((verts[1], verts[4], verts[5], verts[2]))
    # Puffy crust bead along the top edge.
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=t * 1.6, radius2=t * 1.6, depth=2 * w)
    rot = Matrix.Rotation(math.radians(90), 4, "X")
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, 0, h)) @ rot, verts=res["verts"])
    m = Matrix.Translation(base) @ Matrix.Rotation(lean, 4, "X")
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    me = mesh_from_bmesh(name, bm)
    me.materials.append(skin)
    me.materials.append(crust)
    o = new_object(name, me)
    o.parent = parent
    # The top edge (face 4) and the crust bead after it get the crust material.
    for i, poly in enumerate(me.polygons):
        poly.material_index = 1 if i >= 4 else 0
    return o


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

class Rig:
    def __init__(self):
        self.bones = {}
        self.meshes = []

    def bone(self, name, parent, offset):
        b = empty("Rex_" + name, location=offset)
        if parent is not None:
            b.parent = parent
        b.empty_display_size = 0.05
        self.bones[name] = b
        return b


def build_monster():
    skin, crust, belly = skin_material(), M.dough(), M._noisy("KaijuBelly", (0.85, 0.55, 0.25),
                                                                 (0.98, 0.80, 0.50), 12.0, roughness=0.6)
    pep, eye, mouth = M.pepperoni(), eye_material(), mouth_material()
    cheese = M.cheese()
    rig = Rig()
    root = rig.bone("root", None, (0, 0, 0))
    root.scale = (SCALE, SCALE, SCALE)
    hips = rig.bone("hips", root, (0, 0, 0.55))
    torso = rig.bone("torso", hips, (0, 0, 0))
    neck = rig.bone("neck", torso, (0, -0.05, 0.40))
    head = rig.bone("head", neck, (0, -0.05, 0.12))
    jaw = rig.bone("jaw", head, (0, -0.02, -0.03))
    ms = rig.meshes

    ms.append(_blob("RexTorso", torso, (0, 0.02, 0.18), (0.21, 0.19, 0.27), skin))
    ms.append(_blob("RexBelly", torso, (0, -0.10, 0.12), (0.15, 0.10, 0.21), belly))
    ms.append(_blob("RexHips", hips, (0, 0.03, 0.0), (0.19, 0.17, 0.13), skin))
    ms.append(_blob("RexNeck", neck, (0, -0.02, 0.05), (0.10, 0.10, 0.12), skin))
    ms.append(_blob("RexHead", head, (0, -0.07, 0.05), (0.12, 0.15, 0.10), skin))
    ms.append(_blob("RexSnout", head, (0, -0.19, 0.0), (0.085, 0.11, 0.06), skin))
    ms.append(_blob("RexBrow", head, (0, -0.10, 0.10), (0.11, 0.06, 0.035), crust))
    pupil = M.principled("KaijuPupil", color=(0.01, 0.01, 0.01), roughness=0.3)
    for sx in (-1, 1):
        # Big glowing eyes on top of the head (they must poke out of the head blob),
        # slit pupils looking forward, and an angry crust brow slanting down to the middle.
        ms.append(_blob("RexEye", head, (sx * 0.066, -0.125, 0.125), (0.040, 0.038, 0.040), eye))
        ms.append(_blob("RexPupil", head, (sx * 0.068, -0.160, 0.127), (0.011, 0.009, 0.027), pupil))
        ms.append(_blob("RexBrowL", head, (sx * 0.062, -0.135, 0.168), (0.055, 0.032, 0.017), crust,
                        rot=Euler((0.0, sx * 0.45, 0.0)).to_matrix().to_4x4()))
    ms.append(_blob("RexMouth", head, (0, -0.15, -0.035), (0.07, 0.11, 0.02), mouth))

    def upper_teeth(bm):
        for k in range(7):
            y = -0.11 - k * 0.025
            for sx in (-1, 1):
                x = sx * (0.062 - k * 0.003)
                _cone(bm, (x, y, -0.04), (x, y, -0.075), 0.011)
    ms.append(_parts("RexTeethUp", head, upper_teeth, crust))
    ms.append(_blob("RexJaw", jaw, (0, -0.14, -0.035), (0.075, 0.12, 0.032), skin))

    def lower_teeth(bm):
        for k in range(6):
            y = -0.09 - k * 0.026
            for sx in (-1, 1):
                x = sx * (0.055 - k * 0.003)
                _cone(bm, (x, y, -0.01), (x, y, 0.022), 0.009)
    ms.append(_parts("RexTeethDown", jaw, lower_teeth, crust))

    def drool(bm):        # stringy cheese hanging off the jaw
        for x, y, L in ((0.045, -0.2, 0.06), (-0.035, -0.17, 0.085), (0.012, -0.235, 0.045)):
            res = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.0035, radius2=0.0055, depth=L)
            bmesh.ops.translate(bm, vec=(x, y, -0.04 - L / 2), verts=res["verts"])
    ms.append(_parts("RexDrool", jaw, drool, cheese, smooth=True))

    # Dorsal pizza slices: down the back, neck and tail.
    for k, (z, size) in enumerate(((0.40, 0.75), (0.31, 0.95), (0.21, 1.05), (0.10, 1.0), (0.0, 0.9))):
        y = 0.02 + 0.19 * math.sqrt(max(0.0, 1 - ((z - 0.18) / 0.27) ** 2)) - 0.015
        ms.append(_slice_plate("RexPlate", torso, (0, y, z), size, -0.35 - k * 0.12, skin, crust))
    ms.append(_slice_plate("RexPlate", neck, (0, 0.07, 0.07), 0.6, -0.2, skin, crust))
    ms.append(_slice_plate("RexPlate", head, (0, 0.02, 0.12), 0.45, -0.5, skin, crust))

    # Arms.
    for side, sx in (("L", 1), ("R", -1)):
        arm = rig.bone("arm_" + side, torso, (sx * 0.17, -0.10, 0.30))
        fore = rig.bone("fore_" + side, arm, (sx * 0.03, -0.06, -0.12))
        ms.append(_blob("RexUpperArm", arm, (sx * 0.015, -0.03, -0.06), (0.045, 0.045, 0.08), skin))
        ms.append(_blob("RexForearm", fore, (0, -0.05, -0.01), (0.035, 0.07, 0.035), skin))

        def claws(bm, sx=sx):
            for dx in (-0.02, 0.0, 0.02):
                _cone(bm, (dx, -0.11, -0.01), (dx, -0.15, -0.03), 0.01)
        ms.append(_parts("RexClaws", fore, claws, crust))

    # Legs.
    for side, sx in (("L", 1), ("R", -1)):
        thigh = rig.bone("thigh_" + side, hips, (sx * 0.12, 0.0, 0.0))
        shin = rig.bone("shin_" + side, thigh, (sx * 0.02, 0.03, -0.26))
        foot = rig.bone("foot_" + side, shin, (0, -0.02, -0.25))
        ms.append(_blob("RexThigh", thigh, (sx * 0.02, 0.0, -0.11), (0.10, 0.11, 0.15), skin))
        ms.append(_blob("RexShin", shin, (0, 0.0, -0.11), (0.075, 0.075, 0.13), skin))
        ms.append(_blob("RexFoot", foot, (0, -0.06, -0.01), (0.09, 0.13, 0.04), skin))

        def toes(bm):
            for dx in (-0.045, 0.0, 0.045):
                _cone(bm, (dx, -0.17, -0.02), (dx, -0.22, -0.04), 0.017)
        ms.append(_parts("RexToes", foot, toes, crust))

    # Tail: a chain of shrinking segments, slices on the first few.
    parent = hips
    offset = (0, 0.17, 0.02)
    for k in range(7):
        seg = rig.bone("tail%d" % k, parent, offset)
        s = 0.86 ** k
        ms.append(_blob("RexTail", seg, (0, 0.07 * s, 0.0), (0.10 * s, 0.11 * s, 0.09 * s), skin))
        if k < 4:
            ms.append(_slice_plate("RexPlate", seg, (0, 0.06 * s, 0.07 * s), 0.8 * s, -0.9, skin, crust))
        parent = seg
        offset = (0, 0.13 * s, -0.015)
    return rig


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

def _ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def _ramp(f, a, b):
    return _ease((f - a) / float(max(1, b - a)))


def _yaw_to(src, dst):
    """Root yaw so rig-forward (-Y) points from src to dst."""
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    return math.atan2(dx, -dy)


def plan(tl, places):
    """Per-frame pose channels. Returns (frames, {channel: values}, events)."""
    m = tl.moments
    n = tl.total_frames
    frames = np.arange(n)
    ch = {}

    def track(name):
        if name not in ch:
            ch[name] = np.zeros(n)
        return ch[name]

    G, P1, cam_rise, cam_end, river_end = (places[k] for k in ("geyser", "bite_spot", "rise_cam", "late_cam",
                                                                "dive_spot"))
    yaw_rise = _yaw_to(G, cam_rise) + 0.55          # three-quarter view, not head-on
    yaw_walk = _yaw_to(G, P1)
    yaw_bite = _yaw_to(P1, places["big_ben"])
    yaw_late = _yaw_to(P1, cam_end)
    walk_a, walk_b = m["walk_start"], m["walk_end"]
    period = 24
    plants = []
    for f in range(n):
        t = f / 30.0
        x, y, z, yaw = G[0], G[1], -170.0, yaw_rise
        hips_rx = torso_rx = neck_rx = head_rx = head_rz = jaw = 0.0
        torso_ry = torso_rz = 0.0
        arm_rx = [0.2, 0.2]
        arm_rz = [0.0, 0.0]
        thigh = [0.0, 0.0]
        shin = [0.0, 0.0]
        tail_sway = 0.12 * math.sin(2 * math.pi * t / 2.3)
        breathe = 0.03 * math.sin(2 * math.pi * t / 2.0)
        if f >= m["rise_start"]:
            # Rise out of the river with a jiggle.
            # Fast burst out of the water with a little overshoot, then it settles.
            q = min(1.0, (f - m["rise_start"]) / 45.0)
            u = 1 + 2.2 * (q - 1) ** 3 + 1.2 * (q - 1) ** 2
            z = -170.0 + 160.0 * u + 3.0 * math.sin(f * 0.35) * (1 - q)
            torso_rx = -0.15 * (1 - u)
            arm_rx = [-0.6 * (1 - u) + 0.2 * u] * 2
        # Roar: head up, jaw wide, arms out, body shakes.
        r = m["roar"]
        if r <= f < r + 75:
            k = _ramp(f, r, r + 10) * (1 - _ramp(f, r + 60, r + 75))
            head_rx -= 0.55 * k
            neck_rx -= 0.25 * k
            jaw += 0.75 * k
            arm_rz = [0.6 * k, -0.6 * k]
            torso_rz += 0.025 * math.sin(f * 2.1) * k
            torso_rx -= 0.12 * k
        # Idle chomping at the camera while the name card is up.
        if r + 75 <= f < walk_a:
            jaw += 0.12 * max(0.0, math.sin(f * 0.25))
            head_rz += 0.15 * math.sin(f * 0.05)
        # Turn and walk to the north bank beside Big Ben.
        if f >= walk_a - 18:
            yaw = yaw_rise + (yaw_walk - yaw_rise) * _ramp(f, walk_a - 18, walk_a + 6)
        if walk_a <= f:
            u = min(1.0, (f - walk_a) / float(walk_b - walk_a))
            x = G[0] + (P1[0] - G[0]) * u
            y = G[1] + (P1[1] - G[1]) * u
            land = _ramp(y, places["bank_y"] - 20, places["bank_y"] + 5)
            if f < walk_b:
                ph = 2 * math.pi * (f - walk_a) / period
                thigh = [-0.42 * math.sin(ph), 0.42 * math.sin(ph)]
                shin = [0.55 * max(0.0, math.sin(ph + math.pi / 2)), 0.55 * max(0.0, -math.sin(ph + math.pi / 2))]
                z = -10.0 + 12.0 * land + 3.0 * abs(math.cos(ph))
                torso_ry = 0.07 * math.sin(ph)
                hips_rx = 0.0
                arm_rx = [0.2 + 0.35 * math.sin(ph), 0.2 - 0.35 * math.sin(ph)]
                tail_sway = 0.18 * math.sin(ph)
                head_rz += 0.05 * math.sin(ph)
                if int(f - walk_a) % (period // 2) == period // 4:
                    plants.append(f)
            else:
                z = 2.0
        # Bite the top off Big Ben.
        if f >= walk_b:
            yaw = yaw_walk + (yaw_bite - yaw_walk) * _ramp(f, walk_b, walk_b + 20)
            b = m["bite"]
            lean = _ramp(f, b - 40, b - 6) * (1 - _ramp(f, b + 14, b + 50))
            torso_rx += 0.6 * lean
            neck_rx += 0.3 * lean
            head_rx += 0.2 * lean
            if b - 30 <= f < b:
                jaw += 0.85 * _ramp(f, b - 30, b - 8)
            elif b <= f < b + 60:
                jaw += 0.22 * abs(math.sin((f - b) * 0.45))        # chewing
        # Ground-shaking stomp (sends the London Eye rolling).
        s = m["stomp"]
        if s - 30 <= f < s + 40:
            lift = _ramp(f, s - 28, s - 6) * (1 - _ramp(f, s - 6, s))
            thigh[1] += -0.9 * lift
            shin[1] += 0.9 * lift
            if f >= s:
                k = 1 - _ramp(f, s, s + 40)
                jaw += 0.7 * k
                head_rx -= 0.4 * k
                arm_rz = [0.7 * k, -0.7 * k]
            z -= 3.0 * (1 - _ramp(abs(f - s), 0, 6))
        if f >= s + 40:
            yaw = yaw_bite + (yaw_late - yaw_bite) * _ramp(f, s + 40, s + 100)
        # Roars while the Eye rolls, and before the pineapples.
        for rr in (s + 110, m["pineapples"] - 100):
            if rr <= f < rr + 60:
                k = _ramp(f, rr, rr + 8) * (1 - _ramp(f, rr + 45, rr + 60))
                jaw += 0.6 * k
                head_rx -= 0.4 * k
        # Pineapples: disgust, then a dive back into the Thames.
        g = m["gag"]
        if f >= g:
            k = _ramp(f, g, g + 8)
            head_rz += 0.35 * math.sin((f - g) * 0.9) * k * (1 - _ramp(f, m["dive"], m["dive"] + 10))
            jaw += 0.3 * k
            arm_rx = [-1.1 * k, -1.1 * k]
            torso_rx -= 0.2 * k
        if f >= m["dive"]:
            u = _ramp(f, m["dive"], m["dive"] + 55)
            yaw = yaw_late + (_yaw_to(P1, river_end) - yaw_late) * _ramp(f, m["dive"], m["dive"] + 12)
            x = P1[0] + (river_end[0] - P1[0]) * u
            y = P1[1] + (river_end[1] - P1[1]) * u
            z = 2.0 + 25.0 * math.sin(math.pi * min(u, 0.5)) - 200.0 * max(0.0, u - 0.35) / 0.65
            torso_rx = 0.2 + 1.0 * u
            arm_rx = [-1.3, -1.3]
        torso_rx += breathe
        track("root.x")[f] = x
        track("root.y")[f] = y
        track("root.z")[f] = z
        track("root.yaw")[f] = yaw
        track("hips.rx")[f] = hips_rx
        track("torso.rx")[f] = torso_rx
        track("torso.ry")[f] = torso_ry
        track("torso.rz")[f] = torso_rz
        track("neck.rx")[f] = neck_rx
        track("head.rx")[f] = head_rx
        track("head.rz")[f] = head_rz
        track("jaw.rx")[f] = jaw
        for i, side in enumerate("LR"):
            track("arm_%s.rx" % side)[f] = arm_rx[i]
            track("arm_%s.rz" % side)[f] = arm_rz[i]
            track("thigh_%s.rx" % side)[f] = thigh[i]
            track("shin_%s.rx" % side)[f] = shin[i]
            track("foot_%s.rx" % side)[f] = -(thigh[i] + shin[i]) * 0.6
        for k in range(7):
            track("tail%d.rz" % k)[f] = tail_sway * (0.6 + 0.2 * k) * math.cos(t * 1.1 - k * 0.45)
            track("tail%d.rx" % k)[f] = 0.08 + 0.02 * math.sin(t * 1.3 - k * 0.5)
    return frames, ch, plants


def animate(rig, tl, places):
    frames, ch, plants = plan(tl, places)
    root = rig.bones["root"]
    for i, axis in enumerate("xyz"):
        set_track(root, "location", frames, ch["root." + axis], index=i)
    set_track(root, "rotation_euler", frames, ch["root.yaw"], index=2)
    for key, vals in ch.items():
        name, attr = key.split(".")
        if name == "root":
            continue
        idx = {"rx": 0, "ry": 1, "rz": 2}[attr]
        set_track(rig.bones[name], "rotation_euler", frames, vals, index=idx)
    # Hidden once it has dived (and before it rises, it's under the water anyway).
    for o in rig.meshes:
        set_visibility(o, [(tl.moments["rise_start"] - 2, tl.moments["dive"] + 70)])
    return ch, plants
