"""'Fill' episode scene: a dusk city, a glass supertall that fills with phones.

* The tower is extruded tier by tier from hmtb/skyline.py. Its glass facade is
  see-through, so the fill inside shows.
* The fill is an inset copy of the occupied tiers. Its shader draws stacked colourful
  phones and cuts everything above an animated ``FillLevel``.
* Giant (stylised) phones rain down inside the tower onto the rising fill. A single
  real-size phone lands at the tower's foot for the scale gag, and a spray of phones
  bursts out of the top when it's full.
"""

import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from hmtb import skyline

from . import camera, drop_objects, studio, toon
from . import materials as M
from .util import (box_bmesh, cylinder_bmesh, mesh_from_bmesh, new_object, set_keys, set_track,
                   set_visibility)

RAIN_SCALE = 55.0        # stylised giant phones inside the tower (8 m long)
RAIN_COUNT = 36
RAIN_FALL_S = 1.35
BURST_COUNT = 70


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def dusk_world(scene):
    world = bpy.data.worlds.new("DuskSky")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.98, 0.45, 0.22, 1)     # horizon glow
    els[1].position, els[1].color = 0.42, (0.03, 0.04, 0.16, 1)    # deep indigo overhead
    mid = els.new(0.07)
    mid.color = (0.62, 0.26, 0.42, 1)
    mid2 = els.new(0.18)
    mid2.color = (0.16, 0.12, 0.34, 1)
    nt.links.new(sep.outputs[2], ramp.inputs[0])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(ramp.outputs[0], bg.inputs[0])
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])


def sun(name, az, el, energy, color, shadow=True):
    data = bpy.data.lights.new(name, "SUN")
    data.energy = energy
    data.color = color
    data.angle = math.radians(1.5)
    data.use_shadow = shadow
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    d = Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)),
                -math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el))))
    obj.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return obj


def ground_material():
    mat, fresh = M.new_material("CityGround")
    if not fresh:
        return mat
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Object"], sep.inputs[0])

    def grid(spacing, width):
        mins = []
        for axis in (0, 1):
            m = nt.nodes.new("ShaderNodeMath")
            m.operation = "MULTIPLY"
            nt.links.new(sep.outputs[axis], m.inputs[0])
            m.inputs[1].default_value = 1.0 / spacing
            p = nt.nodes.new("ShaderNodeMath")
            p.operation = "PINGPONG"
            nt.links.new(m.outputs[0], p.inputs[0])
            p.inputs[1].default_value = 0.5
            mins.append(p)
        mn = nt.nodes.new("ShaderNodeMath")
        mn.operation = "MINIMUM"
        nt.links.new(mins[0].outputs[0], mn.inputs[0])
        nt.links.new(mins[1].outputs[0], mn.inputs[1])
        lt = nt.nodes.new("ShaderNodeMath")
        lt.operation = "LESS_THAN"
        nt.links.new(mn.outputs[0], lt.inputs[0])
        lt.inputs[1].default_value = width
        return lt.outputs[0]

    roads = grid(160.0, 0.035)
    tiles = grid(1.5, 0.02)
    mix1 = nt.nodes.new("ShaderNodeMix")
    mix1.data_type = "RGBA"
    nt.links.new(tiles, mix1.inputs["Factor"])
    mix1.inputs[6].default_value = (0.035, 0.035, 0.05, 1)
    mix1.inputs[7].default_value = (0.06, 0.06, 0.08, 1)
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    nt.links.new(roads, mix2.inputs["Factor"])
    nt.links.new(mix1.outputs[2], mix2.inputs[6])
    mix2.inputs[7].default_value = (0.30, 0.22, 0.14, 1)
    nt.links.new(mix2.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.7
    return mat


def city_block_material(name, tone):
    """Low-rise buildings with lit dusk windows (a brick texture as the window grid)."""
    mat, fresh = M.new_material(name)
    if not fresh:
        return mat
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tex.outputs["Object"], mapping.inputs[0])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(mapping.outputs[0], sep.inputs[0])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(sep.outputs[0], add.inputs[0])
    nt.links.new(sep.outputs[1], add.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(add.outputs[0], comb.inputs[0])
    nt.links.new(sep.outputs[2], comb.inputs[1])
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 0.25
    brick.inputs["Mortar Size"].default_value = 0.35
    brick.inputs["Color1"].default_value = (0, 0, 0, 1)
    brick.inputs["Color2"].default_value = (1, 1, 1, 1)
    nt.links.new(comb.outputs[0], brick.inputs["Vector"])
    lit = nt.nodes.new("ShaderNodeMath")
    lit.operation = "GREATER_THAN"
    nt.links.new(brick.outputs["Color"], lit.inputs[0])
    lit.inputs[1].default_value = 0.55
    win = nt.nodes.new("ShaderNodeMath")
    win.operation = "MULTIPLY"
    nt.links.new(lit.outputs[0], win.inputs[0])
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[0].default_value = 1.0
    nt.links.new(brick.outputs["Fac"], sub.inputs[1])
    nt.links.new(sub.outputs[0], win.inputs[1])
    bsdf.inputs["Base Color"].default_value = (*tone, 1)
    bsdf.inputs["Roughness"].default_value = 0.6
    em = M._input(bsdf, "emission")
    em.default_value = (1.0, 0.75, 0.4, 1)
    nt.links.new(win.outputs[0], bsdf.inputs["Emission Strength"])
    return mat


def build_city(rng):
    ground = new_object("Ground", mesh_from_bmesh("Ground", box_bmesh(9000, 9000, 1.0, center=(0, 0, -0.5))))
    ground.data.materials.append(ground_material())
    tones = [(0.10, 0.10, 0.16), (0.16, 0.13, 0.15), (0.09, 0.12, 0.17)]
    mats = [city_block_material("CityBlock%d" % i, t) for i, t in enumerate(tones)]
    blocks = []
    tries = 0
    while len(blocks) < 140 and tries < 4000:
        tries += 1
        r = rng.uniform(230, 1500)
        a = rng.uniform(0, 2 * math.pi)
        x, y = r * math.cos(a), r * math.sin(a)
        if y < 0 and abs(x) < 260:          # keep the view to the tower clear
            continue
        w, d = rng.uniform(30, 70), rng.uniform(30, 70)
        h = rng.uniform(18, 70) + (rng.random() ** 3) * 160
        o = new_object("Block", mesh_from_bmesh("Block", box_bmesh(w, d, h, center=(0, 0, h / 2))),
                       location=(x, y, 0))
        o.rotation_euler.z = rng.uniform(0, math.pi)
        o.data.materials.append(rng.choice(mats))
        blocks.append(o)
    # Podium around the tower's base.
    pod = new_object("Podium", mesh_from_bmesh("Podium", cylinder_bmesh(95, 0.5, segments=6, center=(0, 0, 0.25))))
    pod.rotation_euler.z = math.radians(30)
    pod.data.materials.append(M.principled("PodiumStone", color=(0.32, 0.30, 0.34), roughness=0.5))
    return ground, blocks, pod


# ---------------------------------------------------------------------------
# Tower and fill
# ---------------------------------------------------------------------------

def _extrude_tiers(name, tiers, inset=1.0):
    bm = bmesh.new()
    for z0, z1, pts in tiers:
        verts = [bm.verts.new((x * inset, y * inset, z0)) for x, y in pts]
        face = bm.faces.new(verts)
        res = bmesh.ops.extrude_face_region(bm, geom=[face])
        top = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(0, 0, z1 - z0), verts=top)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return mesh_from_bmesh(name, bm)


def facade_material():
    """See-through blue glass with floor bands and mullions, faintly lit."""
    mat, fresh = M.new_material("TowerGlass")
    if not fresh:
        return mat
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Object"], sep.inputs[0])
    floors = nt.nodes.new("ShaderNodeMath")
    floors.operation = "MULTIPLY"
    nt.links.new(sep.outputs[2], floors.inputs[0])
    floors.inputs[1].default_value = 1.0 / 3.6
    pp = nt.nodes.new("ShaderNodeMath")
    pp.operation = "PINGPONG"
    nt.links.new(floors.outputs[0], pp.inputs[0])
    pp.inputs[1].default_value = 0.5
    band = nt.nodes.new("ShaderNodeMath")
    band.operation = "LESS_THAN"
    nt.links.new(pp.outputs[0], band.inputs[0])
    band.inputs[1].default_value = 0.06
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(band.outputs[0], col.inputs["Factor"])
    col.inputs[6].default_value = (0.30, 0.50, 0.78, 1)
    col.inputs[7].default_value = (0.75, 0.82, 0.95, 1)
    nt.links.new(col.outputs[2], bsdf.inputs["Base Color"])
    alpha = nt.nodes.new("ShaderNodeMath")
    alpha.operation = "MULTIPLY_ADD"
    nt.links.new(band.outputs[0], alpha.inputs[0])
    alpha.inputs[1].default_value = 0.30
    alpha.inputs[2].default_value = 0.10
    nt.links.new(alpha.outputs[0], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.12
    bsdf.inputs["Metallic"].default_value = 0.3
    M._set(bsdf, "coat", 0.6)
    # A faint interior glow keeps the glass blue instead of reading as a dark hole.
    nt.links.new(col.outputs[2], M._input(bsdf, "emission"))
    bsdf.inputs["Emission Strength"].default_value = 0.35
    M.set_blended(mat)
    return mat


def fill_material():
    """Stacked colourful phones (a brick texture as the phone grid), cut off above
    the animated FillLevel. Returns (material, FillLevel value node)."""
    mat, _ = M.new_material("PhoneFill")
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Object"], sep.inputs[0])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(sep.outputs[0], add.inputs[0])
    nt.links.new(sep.outputs[1], add.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(add.outputs[0], comb.inputs[0])
    nt.links.new(sep.outputs[2], comb.inputs[1])
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Brick Width"].default_value = 5.9          # a stylised phone, edge-on
    brick.inputs["Row Height"].default_value = 1.6
    brick.inputs["Mortar Size"].default_value = 0.22
    brick.inputs["Color1"].default_value = (0, 0, 0, 1)
    brick.inputs["Color2"].default_value = (1, 1, 1, 1)
    brick.inputs["Mortar"].default_value = (0.02, 0.02, 0.04, 1)
    brick.offset = 0.37
    nt.links.new(comb.outputs[0], brick.inputs["Vector"])
    palette = M._ramp(nt, [
        (0.00, (0.90, 0.20, 0.25)), (0.17, (0.10, 0.55, 0.95)), (0.34, (0.15, 0.80, 0.55)),
        (0.51, (0.98, 0.75, 0.10)), (0.68, (0.60, 0.35, 0.95)), (0.85, (0.92, 0.92, 0.95)),
    ], interpolation="CONSTANT")
    nt.links.new(brick.outputs["Color"], palette.inputs[0])
    mortar = nt.nodes.new("ShaderNodeMix")
    mortar.data_type = "RGBA"
    nt.links.new(brick.outputs["Fac"], mortar.inputs["Factor"])
    nt.links.new(palette.outputs[0], mortar.inputs[6])
    mortar.inputs[7].default_value = (0.02, 0.02, 0.04, 1)
    nt.links.new(mortar.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(mortar.outputs[2], M._input(bsdf, "emission"))
    bsdf.inputs["Emission Strength"].default_value = 0.55
    bsdf.inputs["Roughness"].default_value = 0.35
    level = nt.nodes.new("ShaderNodeValue")
    level.name = "FillLevel"
    level.outputs[0].default_value = 0.0
    below = nt.nodes.new("ShaderNodeMath")
    below.operation = "LESS_THAN"
    nt.links.new(sep.outputs[2], below.inputs[0])
    nt.links.new(level.outputs[0], below.inputs[1])
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(below.outputs[0], mix.inputs[0])
    nt.links.new(transparent.outputs[0], mix.inputs[1])
    nt.links.new(bsdf.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return mat, level


def build_tower():
    occ = skyline.occupied_tiers()
    mech = skyline.mechanical_tiers()
    me = _extrude_tiers("TowerFacade", occ + mech)
    facade = new_object("TowerFacade", me)
    me.materials.append(facade_material())
    spire = new_object("Spire", mesh_from_bmesh("Spire", cylinder_bmesh(
        5.0, skyline.H_TIP - skyline.H_MECH, segments=24, radius2=0.35,
        center=(0, 0, (skyline.H_TIP + skyline.H_MECH) / 2))))
    spire.data.materials.append(M.principled("SpireSteel", color=(0.82, 0.85, 0.9), roughness=0.2, metallic=1.0))
    fill = new_object("PhoneFillVolume", _extrude_tiers("PhoneFillVolume", occ, inset=0.96))
    mat, level = fill_material()
    fill.data.materials.append(mat)
    return facade, spire, fill, level


# ---------------------------------------------------------------------------
# Phones in motion
# ---------------------------------------------------------------------------

def _phone_objects(template, n, scale, prefix):
    objs = []
    for i in range(n):
        o = bpy.data.objects.new("%s_%02d" % (prefix, i), template.data)
        bpy.context.scene.collection.objects.link(o)
        o.scale = (scale, scale, scale)
        objs.append(o)
    return objs


def animate_rain(objs, ftl, rng):
    """Giant phones falling inside the tower onto the rising fill, in a steady stream."""
    a, b = ftl.segments["fill"]
    fps = ftl.fps
    fall_f = int(RAIN_FALL_S * fps)
    period = fall_f + 3
    frames = np.arange(a - 1, b + 2)
    for k, o in enumerate(objs):
        offset = int(k * period / len(objs))
        loc = np.zeros((len(frames), 3))
        rot = np.zeros((len(frames), 3))
        scl = np.zeros(len(frames))
        cycle = -1
        start = (0.0, 0.0)
        spin = (0.0, 0.0, 0.0)
        for i, f in enumerate(frames):
            t = f - a - offset
            if t < 0 or f >= b:
                continue
            c, ph = divmod(t, period)
            if c != cycle:
                cycle = c
                rr, aa = rng.uniform(0, 7.0), rng.uniform(0, 2 * math.pi)
                start = (rr * math.cos(aa), rr * math.sin(aa))
                spin = (rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(-3, 3))
            if ph >= fall_f:
                continue
            u = ph / float(fall_f)
            level = ftl.level[min(f, len(ftl.level) - 1)]
            z_top = min(skyline.H_OCC - 8.0, level + 170.0)
            z = z_top + (level + 3.0 - z_top) * u * u
            loc[i] = (start[0], start[1], z)
            rot[i] = (spin[0] * u, spin[1] * u, spin[2] * u)
            scl[i] = RAIN_SCALE
        for axis in range(3):
            set_track(o, "location", frames, loc[:, axis], index=axis)
            set_track(o, "rotation_euler", frames, rot[:, axis], index=axis)
            set_track(o, "scale", frames, scl, index=axis)


BURST_SCALE = 75.0


def animate_burst(objs, ftl, rng):
    """FULL: phones spray out of the top of the tower and tumble away."""
    a = ftl.segments["full"][0]
    end = ftl.hold_f + 1
    frames = np.arange(a - 1, end + 1)
    g = 9.81 * 4.0
    for o in objs:
        ang = rng.uniform(0, 2 * math.pi)
        out_v = rng.uniform(30, 75)
        up_v = rng.uniform(25, 70)
        z0 = skyline.H_OCC - rng.uniform(0, 25)
        r0 = rng.uniform(8, 18)
        delay = rng.randint(0, 18)
        spin = (rng.uniform(-8, 8), rng.uniform(-8, 8), rng.uniform(-4, 4))
        loc = np.zeros((len(frames), 3))
        rot = np.zeros((len(frames), 3))
        scl = np.zeros(len(frames))
        for i, f in enumerate(frames):
            t = (f - a - delay) / float(ftl.fps)
            if t < 0:
                continue
            x = math.cos(ang) * (r0 + out_v * t)
            y = math.sin(ang) * (r0 + out_v * t)
            z = z0 + up_v * t - 0.5 * g * t * t
            loc[i] = (x, y, max(z, 1.0))
            rot[i] = (spin[0] * t, spin[1] * t, spin[2] * t)
            scl[i] = BURST_SCALE
        for axis in range(3):
            set_track(o, "location", frames, loc[:, axis], index=axis)
            set_track(o, "rotation_euler", frames, rot[:, axis], index=axis)
            set_track(o, "scale", frames, scl, index=axis)


def animate_hero_phone(o, ftl):
    """One real-size phone drops onto the plaza in front of the tower."""
    rel, imp = ftl.drop_release_f, ftl.drop_impact_f
    frames = list(range(rel - 1, imp + 12))
    zs, rx = [], []
    for f in frames:
        if f <= imp:
            u = max(0.0, (f - rel) / float(imp - rel))
            zs.append(0.5055 + 1.6 * (1 - u * u))
            rx.append(0.8 * (1 - u))
        else:
            t = f - imp
            zs.append(0.5055 + 0.03 * max(0.0, math.sin(math.pi * t / 6.0)) * (1 if t < 6 else 0))
            rx.append(0.0)
    for axis, val in ((0, 0.0), (1, HERO_Y)):
        set_keys(o, "location", [frames[0]], [val], index=axis, interpolation="CONSTANT")
    set_track(o, "location", frames, zs, index=2)
    set_track(o, "rotation_euler", frames, rx, index=0)
    set_keys(o, "rotation_euler", [frames[0]], [math.radians(18)], index=2, interpolation="CONSTANT")
    set_visibility(o, [(rel, 10 ** 7)])


# ---------------------------------------------------------------------------
# Cameras
# ---------------------------------------------------------------------------

TOWER_BOX = ([-60.0, -60.0, 0.0], [60.0, 60.0, skyline.H_TIP])
HERO_Y = -75.0           # the single phone lands on the plaza, 22 m in front of the tower
# Leave the top of the frame for the counters, the bottom 20% for TikTok's UI.
FILL_SCREEN_BOX = (0.33, 0.56, 0.215, 0.665)


def animate_cameras(scene, ftl, hook_cam, main_cam):
    # Hook: worm's-eye view from the street, slow push towards the tower.
    hook_cam.data.lens = 24.0
    look = Vector((0.0, 0.0, 360.0))
    for f, loc in ((0, Vector((-170.0, -540.0, 4.0))), (ftl.segments["hook"][1], Vector((-150.0, -495.0, 5.0)))):
        hook_cam.location = loc
        hook_cam.rotation_euler = (look - loc).to_track_quat("-Z", "Y").to_euler()
        hook_cam.keyframe_insert("location", frame=f)
        hook_cam.keyframe_insert("rotation_euler", frame=f)

    # Main: close on the plaza for the single phone, the big pull-back, then a per-frame
    # plan that tracks the rising fill in medium shots and pulls out to show progress.
    plan_main_camera(ftl, main_cam)


def _smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def camera_plan(ftl):
    """Per-frame (target_z, distance, yaw, pitch, shift_y) for the main camera."""
    fps = ftl.fps
    a_one = ftl.segments["one"][0]
    b_zoom = ftl.segments["zoom"][1]
    full = ftl.segments["full"][0]

    def at(sec):
        return int(round(sec * fps))

    WIDE = ("wide", 400.0, 2150.0, 6.0, 0.035)
    MED = ("med", None, 430.0, 3.0, 0.07)
    TOP = ("top", 560.0, 560.0, 4.0, 0.06)
    span = ftl.segments["fill"][1] - b_zoom
    poses = [(b_zoom, WIDE), (b_zoom + int(0.05 * span), MED), (b_zoom + int(0.19 * span), MED),
             (b_zoom + int(0.25 * span), WIDE), (b_zoom + int(0.31 * span), WIDE),
             (b_zoom + int(0.38 * span), MED), (b_zoom + int(0.69 * span), MED),
             (b_zoom + int(0.77 * span), WIDE), (full - at(3.5), WIDE), (full - at(1.4), TOP),
             (full, TOP), (ftl.hold_f, ("top", 575.0, 700.0, 6.0, 0.05))]

    def params(pose, f):
        name, tz, dist, pitch, sy = pose
        if name == "med":
            tz = max(70.0, ftl.level[f] + 30.0)
        return tz, dist, pitch, sy

    plan = {}
    for f in range(b_zoom, ftl.hold_f + 1):
        i = max(k for k in range(len(poses)) if poses[k][0] <= f) if f >= poses[0][0] else 0
        j = min(i + 1, len(poses) - 1)
        fa, pa = poses[i]
        fb, pb = poses[j]
        u = 0.0 if fb == fa else _smooth((f - fa) / float(fb - fa))
        A, B = params(pa, f), params(pb, f)
        # Distance blends in log space so pull-outs feel like a smooth zoom.
        tz = A[0] + (B[0] - A[0]) * u
        dist = math.exp(math.log(A[1]) + (math.log(B[1]) - math.log(A[1])) * u)
        pitch = A[2] + (B[2] - A[2]) * u
        sy = A[3] + (B[3] - A[3]) * u
        yaw = -20.0 + 45.0 * (f - b_zoom) / float(max(1, ftl.hold_f - b_zoom))
        plan[f] = (tz, dist, yaw, pitch, sy)
    return plan


def plan_main_camera(ftl, cam):
    a_one = ftl.segments["one"][0]
    a_zoom, b_zoom = ftl.segments["zoom"]
    cam.data.clip_start = 0.02
    cam.data.clip_end = 20000.0
    close_loc = Vector((0.12, HERO_Y - 0.95, 0.61))
    target = Vector((0.0, HERO_Y + 4.0, 1.75))
    close_rot = (target - close_loc).to_track_quat("-Z", "Y").to_euler()
    keys = {}   # frame -> (loc, rot, shift_x, shift_y, lens)
    keys[a_one] = (close_loc, close_rot, 0.0, 0.0, 20.0)
    keys[a_zoom] = (close_loc + Vector((0, 0.12, 0.0)), close_rot, 0.0, 0.0, 20.0)
    plan = camera_plan(ftl)
    prev = close_rot
    punches = [(m["frame"], 0.05) for m in ftl.milestones] + [(ftl.segments["full"][0], 0.08)]
    for f, (tz, dist, yaw, pitch, sy) in plan.items():
        y, p = math.radians(yaw), math.radians(pitch)
        T = Vector((0.0, 0.0, tz))
        d = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
        loc = T + d * dist
        rot = (T - loc).to_track_quat("-Z", "Y").to_euler("XYZ", prev)
        prev = rot
        lens = 50.0
        for pf, s in punches:
            t = f - pf
            if t >= 0:
                lens *= 1.0 + s * (t / 2.0 if t < 2 else math.exp(-(t - 2) / 3.5))
        keys[f] = (loc, rot, 0.03, sy, lens)
    frames = sorted(keys)
    for axis in range(3):
        set_keys(cam, "location", frames, [keys[f][0][axis] for f in frames], index=axis, interpolation="BEZIER")
        set_keys(cam, "rotation_euler", frames, [keys[f][1][axis] for f in frames], index=axis,
                 interpolation="BEZIER")
    set_keys(cam.data, "shift_x", frames, [keys[f][2] for f in frames], interpolation="BEZIER")
    set_keys(cam.data, "shift_y", frames, [keys[f][3] for f in frames], interpolation="BEZIER")
    set_keys(cam.data, "lens", frames, [keys[f][4] for f in frames], interpolation="BEZIER")
    camera.add_shake(cam, ftl.segments["full"][0], 24, 3.0, scale=1.4)


def animate_outline_thickness(objects, ftl, cams, base=0.0016):
    """Keep outlines ~3 px wide whether the camera is 1 m or 2 km away."""
    scene = bpy.context.scene
    frames, vals = [], []
    for f in range(ftl.total_frames):
        shot = ftl.shot_at(f)
        cam = cams[shot.camera]
        sf = ftl.scene_frame(f)[0]
        if shot.hold and f > shot.video_start:
            continue
        scene.frame_set(sf)
        d = (cam.matrix_world.translation - Vector((0, 0, 200.0))).length
        frames.append(sf)
        vals.append(min(3.2, max(0.04, base * d)))
    uniq = {}
    for f, v in zip(frames, vals):
        uniq[f] = v
    fs = sorted(uniq)
    for o in objects:
        mod = o.modifiers.get("Outline")
        if mod is not None:
            set_track(mod, "thickness", fs, [uniq[f] for f in fs])


# ---------------------------------------------------------------------------
# Whole scene
# ---------------------------------------------------------------------------

def build_scene(cfg, ftl, width, height, samples):
    from .util import reset_scene
    scene = reset_scene()
    scene.frame_start = 0
    scene.frame_end = ftl.total_frames
    studio.setup_render(scene, width, height, samples)
    if hasattr(scene.eevee, "shadow_resolution_scale"):
        scene.eevee.shadow_resolution_scale = 0.5
    dusk_world(scene)
    rng = random.Random(cfg["seed"])
    sun("SunKey", -55.0, 14.0, 4.2, (1.0, 0.62, 0.38))
    sun("SkyFill", 120.0, 35.0, 0.9, (0.45, 0.55, 1.0), shadow=False)

    ground, blocks, podium = build_city(rng)
    facade, spire, fill, level_node = build_tower()
    frames = list(range(ftl.total_frames))
    set_track(level_node.outputs[0], "default_value", frames,
              [lv + (0.0 if lv <= 0 else 0.5) for lv in ftl.level])

    template = drop_objects.build("iphone")
    hero = bpy.data.objects.new("HeroPhone", template.data)
    scene.collection.objects.link(hero)
    animate_hero_phone(hero, ftl)
    rain = _phone_objects(template, RAIN_COUNT, RAIN_SCALE, "RainPhone")
    animate_rain(rain, ftl, rng)
    burst = _phone_objects(template, BURST_COUNT, RAIN_SCALE, "BurstPhone")
    animate_burst(burst, ftl, rng)

    hook_cam = camera.make_camera("HookCam", lens=24.0)
    main_cam = camera.make_camera("MainCam", lens=50.0)
    for c in (hook_cam, main_cam):
        c.data.clip_end = 20000.0
    scene.camera = hook_cam
    animate_cameras(scene, ftl, hook_cam, main_cam)

    studio.no_transparent_shadows()
    fill.visible_shadow = False
    toon.outline_scene([facade, spire] + blocks, 780.0)   # not the plaza: the low camera sits inside its shell
    toon.outline_scene([hero] + rain + burst, 1.0)
    animate_outline_thickness([facade, spire] + blocks, ftl, {"hook": hook_cam, "main": main_cam})
    return {"scene": scene, "cams": {"hook": hook_cam, "main": main_cam}, "fill_cam": "main",
            "hero": (Vector((0.0, HERO_Y, 0.5)), "main")}
