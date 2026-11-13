"""'Fill' episode scene for the whole Earth: a cutaway globe that fills with pizzas.

* A cartoon Earth (real continents from Natural Earth, assets/earth_land_2048.png) with
  an orange-slice wedge cut out towards the camera, so you can see inside.
* Inside: a sphere of stacked pizzas, drawn as strata (crust / sauce / cheese) on the
  cut faces, with a "sea of pizzas" disc on top that rises with ``FillLevel``.
* Giant pizzas rain down into the open wedge, and a spray of pizzas bursts out of the
  top when it's full.
* A separate picnic-table set (real metres, far from the planet) for the single real
  pizza at the start. The overlay's swipe covers the cut from table to space.

Scene units: the planet has radius 1000 (1 unit = 6.371 km); the table set uses metres.
"""

import math
import os
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from hmtb import PROJECT_DIR
from hmtb.containers import EARTH_R

from . import camera, drop_objects, studio, toon
from . import materials as M
from .util import (box_bmesh, cylinder_bmesh, mesh_from_bmesh, new_object, reset_scene, set_keys, set_track,
                   set_visibility)

WEDGE_HALF = math.radians(42)        # half-angle of the slice cut out towards the camera
WEDGE_AZ = math.radians(-90)         # it faces -Y, where the camera is
LON_OFFSET = math.radians(70)        # Africa/Europe face the hook; the slice falls on the Pacific
FILL_R = 0.975 * EARTH_R
TABLE_Z = -8000.0                    # the picnic set sits far below the planet
RAIN_SCALE = 115.0                   # giant pizzas (~40 units, ~260 km across)
RAIN_COUNT = 30
BURST_COUNT = 60


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def space_world(scene):
    world = bpy.data.worlds.new("Space")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 420.0
    noise.inputs["Detail"].default_value = 0.0
    nt.links.new(tex.outputs["Generated"], noise.inputs["Vector"])
    stars = nt.nodes.new("ShaderNodeValToRGB")
    els = stars.color_ramp.elements
    els[0].position, els[0].color = 0.74, (0.004, 0.005, 0.018, 1)
    els[1].position, els[1].color = 0.78, (1.0, 1.0, 1.0, 1)
    nt.links.new(noise.outputs["Fac"], stars.inputs[0])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(stars.outputs[0], bg.inputs[0])
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])


def sun(name, az, el, energy, color, shadow=True):
    data = bpy.data.lights.new(name, "SUN")
    data.energy = energy
    data.color = color
    data.angle = math.radians(1.0)
    data.use_shadow = shadow
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    d = Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)),
                -math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el))))
    obj.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return obj


# ---------------------------------------------------------------------------
# Planet
# ---------------------------------------------------------------------------

def _in_wedge(x, y):
    a = math.atan2(y, x) - WEDGE_AZ
    a = (a + math.pi) % (2 * math.pi) - math.pi
    return abs(a) < WEDGE_HALF


def _wedge_planes():
    """Two planes bounding the wedge (through the Z axis)."""
    planes = []
    for s in (-1, 1):
        a = WEDGE_AZ + s * WEDGE_HALF
        d = Vector((math.cos(a), math.sin(a), 0.0))
        n = Vector((-d.y, d.x, 0.0)) * s          # points into the wedge
        planes.append(n)
    return planes


def _sphere_minus_wedge(name, radius, segs=128, rings=64, cap_cut=True):
    """UV sphere with the wedge removed; cut faces filled when ``cap_cut``."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    for n in _wedge_planes():
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=(0, 0, 0), plane_no=n)
    doomed = [f for f in bm.faces if _in_wedge(f.calc_center_median().x, f.calc_center_median().y)
              and f.calc_center_median().length > 1e-3]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    if cap_cut:
        boundary = [e for e in bm.edges if e.is_boundary]
        if boundary:
            res = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
            for f in res["faces"]:
                f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return mesh_from_bmesh(name, bm, smooth=True)


def earth_material():
    """Cartoon Earth: blue oceans, green land from the Natural Earth mask, white poles."""
    mat, fresh = M.new_material("EarthSurface")
    if not fresh:
        return mat
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Object"], sep.inputs[0])

    def math_node(op, a, b=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    lon = math_node("ADD", math_node("ARCTAN2", sep.outputs[1], sep.outputs[0]), -LON_OFFSET)
    u = math_node("ADD", math_node("DIVIDE", lon, 2 * math.pi), 0.5)
    u = math_node("FRACT", u)
    length = nt.nodes.new("ShaderNodeVectorMath")
    length.operation = "LENGTH"
    nt.links.new(tex.outputs["Object"], length.inputs[0])
    lat = math_node("ARCSINE", math_node("DIVIDE", sep.outputs[2], length.outputs["Value"]))
    v = math_node("ADD", math_node("DIVIDE", lat, math.pi), 0.5)
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(u, comb.inputs[0])
    nt.links.new(v, comb.inputs[1])
    img = nt.nodes.new("ShaderNodeTexImage")
    path = os.path.join(PROJECT_DIR, "assets", "earth_land_2048.png")
    img.image = bpy.data.images.load(path, check_existing=True)
    img.image.colorspace_settings.name = "Non-Color"
    img.extension = "REPEAT"
    nt.links.new(comb.outputs[0], img.inputs[0])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.004
    noise.inputs["Detail"].default_value = 3.0
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    land_col = M._ramp(nt, [(0.35, (0.20, 0.55, 0.20)), (0.65, (0.55, 0.62, 0.25))])
    nt.links.new(noise.outputs["Fac"], land_col.inputs[0])
    surf = nt.nodes.new("ShaderNodeMix")
    surf.data_type = "RGBA"
    nt.links.new(img.outputs["Color"], surf.inputs["Factor"])
    surf.inputs[6].default_value = (0.04, 0.28, 0.75, 1)
    nt.links.new(land_col.outputs[0], surf.inputs[7])
    polar = math_node("GREATER_THAN", math_node("ABSOLUTE", lat), math.radians(68))
    ice = nt.nodes.new("ShaderNodeMix")
    ice.data_type = "RGBA"
    nt.links.new(math_node("MULTIPLY", polar, img.outputs["Color"]), ice.inputs["Factor"])
    nt.links.new(surf.outputs[2], ice.inputs[6])
    ice.inputs[7].default_value = (0.92, 0.95, 1.0, 1)
    nt.links.new(ice.outputs[2], bsdf.inputs["Base Color"])
    rough = math_node("MULTIPLY_ADD", img.outputs["Color"], 0.55)
    rough.node.inputs[2].default_value = 0.25          # glossy oceans, matte land
    nt.links.new(rough, bsdf.inputs["Roughness"])
    return mat


def atmosphere_material():
    mat, fresh = M.new_material("Atmosphere")
    if not fresh:
        return mat
    nt = mat.node_tree
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.35, 0.65, 1.0, 1)
    em.inputs["Strength"].default_value = 2.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    pw.inputs[1].default_value = 3.0
    nt.links.new(pw.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], out.inputs[0])
    M.set_blended(mat)
    return mat


def strata_material():
    """Stacked pizzas seen side-on: crust, sauce and cheese bands, cut above FillLevel."""
    mat, _ = M.new_material("PizzaStrata")
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
    brick.inputs["Brick Width"].default_value = 130.0         # one giant stylised pizza, side-on
    brick.inputs["Row Height"].default_value = 30.0
    brick.inputs["Mortar Size"].default_value = 1.5
    brick.inputs["Color1"].default_value = (0, 0, 0, 1)
    brick.inputs["Color2"].default_value = (1, 1, 1, 1)
    brick.offset = 0.43
    nt.links.new(comb.outputs[0], brick.inputs["Vector"])
    # Within each 9-unit row: crust, sauce, cheese, crust.
    band = nt.nodes.new("ShaderNodeMath")
    band.operation = "FRACT"
    div = nt.nodes.new("ShaderNodeMath")
    div.operation = "DIVIDE"
    nt.links.new(sep.outputs[2], div.inputs[0])
    div.inputs[1].default_value = 30.0
    nt.links.new(div.outputs[0], band.inputs[0])
    layers = M._ramp(nt, [(0.0, (0.78, 0.48, 0.18)), (0.28, (0.85, 0.10, 0.05)),
                          (0.42, (1.0, 0.86, 0.30)), (0.80, (0.88, 0.60, 0.26))], interpolation="CONSTANT")
    nt.links.new(band.outputs[0], layers.inputs[0])
    mortar = nt.nodes.new("ShaderNodeMix")
    mortar.data_type = "RGBA"
    nt.links.new(brick.outputs["Fac"], mortar.inputs["Factor"])
    nt.links.new(layers.outputs[0], mortar.inputs[6])
    mortar.inputs[7].default_value = (0.22, 0.10, 0.04, 1)
    nt.links.new(mortar.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.5
    nt.links.new(mortar.outputs[2], M._input(bsdf, "emission"))
    bsdf.inputs["Emission Strength"].default_value = 0.4
    level = nt.nodes.new("ShaderNodeValue")
    level.name = "FillLevel"
    below = nt.nodes.new("ShaderNodeMath")
    below.operation = "LESS_THAN"
    nt.links.new(sep.outputs[2], below.inputs[0])
    nt.links.new(level.outputs[0], below.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(below.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(bsdf.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return mat, level


def pizza_sea_material():
    """Top-down sea of pizzas: Voronoi cells become pizzas with crust, cheese and pepperoni."""
    mat, fresh = M.new_material("PizzaSea")
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1 / 40.0, 1 / 40.0, 1 / 40.0)   # ~40-unit pizzas, world space
    nt.links.new(geo.outputs["Position"], mapping.inputs[0])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "F1"
    vor.inputs["Randomness"].default_value = 0.12
    vor.inputs["Scale"].default_value = 1.0
    nt.links.new(mapping.outputs[0], vor.inputs["Vector"])
    pep = nt.nodes.new("ShaderNodeTexVoronoi")
    pep.inputs["Scale"].default_value = 6.0
    nt.links.new(mapping.outputs[0], pep.inputs["Vector"])
    ring = M._ramp(nt, [(0.0, (1.0, 0.85, 0.30)), (0.34, (0.85, 0.12, 0.05)), (0.38, (0.90, 0.60, 0.26)),
                        (0.47, (0.18, 0.08, 0.03))], interpolation="CONSTANT")
    nt.links.new(vor.outputs["Distance"], ring.inputs[0])
    is_cheese = nt.nodes.new("ShaderNodeMath")
    is_cheese.operation = "LESS_THAN"
    nt.links.new(vor.outputs["Distance"], is_cheese.inputs[0])
    is_cheese.inputs[1].default_value = 0.32
    spot = nt.nodes.new("ShaderNodeMath")
    spot.operation = "LESS_THAN"
    nt.links.new(pep.outputs["Distance"], spot.inputs[0])
    spot.inputs[1].default_value = 0.16
    both = nt.nodes.new("ShaderNodeMath")
    both.operation = "MULTIPLY"
    nt.links.new(is_cheese.outputs[0], both.inputs[0])
    nt.links.new(spot.outputs[0], both.inputs[1])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(both.outputs[0], col.inputs["Factor"])
    nt.links.new(ring.outputs[0], col.inputs[6])
    col.inputs[7].default_value = (0.55, 0.06, 0.04, 1)
    nt.links.new(col.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(col.outputs[2], M._input(bsdf, "emission"))
    bsdf.inputs["Emission Strength"].default_value = 0.45
    bsdf.inputs["Roughness"].default_value = 0.45
    return mat


def _cap_mesh(segs=160):
    """Unit disc minus the wedge sector (the top of the fill, scaled per frame)."""
    bm = bmesh.new()
    centre = bm.verts.new((0, 0, 0))
    rim = []
    start = WEDGE_AZ + WEDGE_HALF
    sweep = 2 * math.pi - 2 * WEDGE_HALF
    for i in range(segs + 1):
        a = start + sweep * i / segs
        rim.append(bm.verts.new((math.cos(a), math.sin(a), 0.0)))
    for i in range(segs):
        bm.faces.new((centre, rim[i], rim[i + 1]))
    return mesh_from_bmesh("PizzaSeaCap", bm)


def _sector_fill(name, radius):
    """Sphere minus the wedge, built from two convex sectors so the cut faces are flat."""
    def n_at(a):
        return Vector((-math.sin(a), math.cos(a), 0.0))

    a1 = WEDGE_AZ + WEDGE_HALF
    mid = WEDGE_AZ + math.pi
    a2 = WEDGE_AZ + 2 * math.pi - WEDGE_HALF
    bm_all = bmesh.new()
    for lo, hi in ((a1, mid), (mid, a2)):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=128, v_segments=64, radius=radius)
        for plane_no in (-n_at(lo), n_at(hi)):
            geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=(0, 0, 0), plane_no=plane_no,
                                   clear_outer=True)
            boundary = [e for e in bm.edges if e.is_boundary]
            if boundary:
                for f in bmesh.ops.holes_fill(bm, edges=boundary, sides=0)["faces"]:
                    f.material_index = 1
                    f.smooth = False
        for f in bm.faces:
            if f.material_index == 0:
                f.smooth = True
        me = bpy.data.meshes.new("tmp")
        bm.to_mesh(me)
        bm.free()
        bm_all.from_mesh(me)
        bpy.data.meshes.remove(me)
    bmesh.ops.recalc_face_normals(bm_all, faces=list(bm_all.faces))
    return mesh_from_bmesh(name, bm_all)


def build_planet():
    shell_me = _sphere_minus_wedge("EarthShell", EARTH_R, cap_cut=False)
    shell = new_object("EarthShell", shell_me)
    shell_me.materials.append(earth_material())
    shell_me.materials.append(M.principled("EarthCrust", color=(0.55, 0.30, 0.14), roughness=0.8,
                                           emission=(0.9, 0.35, 0.08), emission_strength=0.25))
    sol = shell.modifiers.new("Crust", "SOLIDIFY")
    sol.thickness = 22.0
    sol.offset = -1.0
    sol.use_rim = True
    sol.material_offset = 1          # the inside of the shell is warm rock, not a black void
    sol.material_offset_rim = 1
    atmo = new_object("Atmosphere", mesh_from_bmesh("Atmosphere", _uv_sphere(EARTH_R * 1.035)))
    atmo.data.materials.append(atmosphere_material())
    fill_me = _sector_fill("PizzaFill", FILL_R)
    fill = new_object("PizzaFill", fill_me)
    mat, level = strata_material()
    fill_me.materials.append(mat)
    fill_me.materials.append(mat)
    cap = new_object("PizzaSeaCap", _cap_mesh())
    cap.data.materials.append(pizza_sea_material())
    return shell, atmo, fill, cap, level


def _uv_sphere(r):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=r)
    for f in bm.faces:
        f.smooth = True
    return bm


# ---------------------------------------------------------------------------
# Picnic table (real metres)
# ---------------------------------------------------------------------------

def build_table_set():
    z = TABLE_Z
    grass = new_object("Grass", mesh_from_bmesh("Grass", box_bmesh(60, 60, 0.2, center=(0, 0, z - 0.85))))
    grass.data.materials.append(M._noisy("GrassMat", (0.12, 0.35, 0.08), (0.22, 0.50, 0.12), 3.0, roughness=0.9))
    top = new_object("TableTop", mesh_from_bmesh("TableTop", box_bmesh(1.8, 1.0, 0.05, center=(0, 0, z - 0.025))))
    top.data.materials.append(M.tablecloth())
    legs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg = new_object("TableLeg", mesh_from_bmesh("TableLeg", box_bmesh(
                0.07, 0.07, 0.72, center=(sx * 0.8, sy * 0.42, z - 0.41))))
            leg.data.materials.append(M.wood("TableWood"))
            legs.append(leg)
    lamp = bpy.data.lights.new("TableLight", "AREA")
    lamp.size = 2.0
    lamp.energy = 120.0
    lamp.use_shadow = False
    lo = bpy.data.objects.new("TableLight", lamp)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = (-0.8, -1.2, z + 2.2)
    lo.rotation_euler = (Vector((0, 0, z)) - lo.location).to_track_quat("-Z", "Y").to_euler()
    return [grass, top] + legs


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

def _fill_radius(level):
    return math.sqrt(max(0.0, FILL_R ** 2 - level ** 2))


def animate_cap(cap, ftl):
    frames = list(range(ftl.total_frames))
    zs, rs = [], []
    for f in frames:
        lv = ftl.level[f]
        zs.append(lv)
        rs.append(max(0.001, _fill_radius(lv) * 0.995) if lv > -FILL_R + 1 else 0.001)
    set_track(cap, "location", frames, zs, index=2)
    for axis in (0, 1):
        set_track(cap, "scale", frames, rs, index=axis)
    set_visibility(cap, [(ftl.segments["fill"][0], 10 ** 7)])


def animate_rain(objs, ftl, rng):
    a, b = ftl.segments["fill"]
    fall_f = int(1.3 * ftl.fps)
    period = fall_f + 3
    frames = np.arange(a - 1, b + 2)
    for k, o in enumerate(objs):
        offset = int(k * period / len(objs))
        loc = np.zeros((len(frames), 3))
        rot = np.zeros((len(frames), 3))
        scl = np.zeros(len(frames))
        cycle = -1
        sx = sy = 0.0
        spin = (0, 0, 0)
        for i, f in enumerate(frames):
            t = f - a - offset
            if t < 0 or f >= b:
                continue
            c, ph = divmod(t, period)
            lv = ftl.level[min(f, len(ftl.level) - 1)]
            if c != cycle:
                cycle = c
                r = _fill_radius(lv) * rng.uniform(0.15, 0.8)
                ang = WEDGE_AZ + rng.uniform(-0.8, 0.8) * WEDGE_HALF
                sx, sy = r * math.cos(ang), r * math.sin(ang)
                spin = (rng.uniform(-5, 5), rng.uniform(-5, 5), rng.uniform(-2, 2))
            if ph >= fall_f:
                continue
            u = ph / float(fall_f)
            z_top = lv + 520.0
            z = z_top + (lv + 6.0 - z_top) * u * u
            loc[i] = (sx, sy, z)
            rot[i] = (spin[0] * (1 - u), spin[1] * (1 - u), spin[2] * u)
            scl[i] = RAIN_SCALE
        for axis in range(3):
            set_track(o, "location", frames, loc[:, axis], index=axis)
            set_track(o, "rotation_euler", frames, rot[:, axis], index=axis)
            set_track(o, "scale", frames, scl, index=axis)


def animate_burst(objs, ftl, rng):
    a = ftl.segments["full"][0]
    frames = np.arange(a - 1, ftl.hold_f + 2)
    g = 9.81 * 25.0
    for o in objs:
        ang = WEDGE_AZ + rng.uniform(-1.6, 1.6)
        out_v = rng.uniform(180, 520)
        up_v = rng.uniform(250, 650)
        r0 = rng.uniform(0, 300)
        delay = rng.randint(0, 15)
        spin = (rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(-3, 3))
        loc = np.zeros((len(frames), 3))
        rot = np.zeros((len(frames), 3))
        scl = np.zeros(len(frames))
        for i, f in enumerate(frames):
            t = (f - a - delay) / float(ftl.fps)
            if t < 0:
                continue
            rr = r0 + out_v * t
            loc[i] = (math.cos(ang) * rr, math.sin(ang) * rr, FILL_R * 0.9 + up_v * t - 0.5 * g * t * t)
            rot[i] = (spin[0] * t, spin[1] * t, spin[2] * t)
            scl[i] = RAIN_SCALE * 1.2
        for axis in range(3):
            set_track(o, "location", frames, loc[:, axis], index=axis)
            set_track(o, "rotation_euler", frames, rot[:, axis], index=axis)
            set_track(o, "scale", frames, scl, index=axis)


def animate_hero(o, ftl):
    """One real pizza drops onto the picnic table with a squashy landing."""
    rel, imp = ftl.drop_release_f, ftl.drop_impact_f
    frames = list(range(rel - 1, imp + 16))
    zs, sz, rx = [], [], []
    rest = TABLE_Z + 0.015
    for f in frames:
        if f <= imp:
            u = max(0.0, (f - rel) / float(imp - rel))
            zs.append(rest + 1.2 * (1 - u * u))
            sz.append(1.0)
            rx.append(0.5 * (1 - u))
        else:
            t = f - imp
            q = 0.35 * math.exp(-t / 3.0) * math.cos(2 * math.pi * t / 8.0)
            zs.append(rest - q * 0.015)
            sz.append(1.0 - q)
            rx.append(0.0)
    set_keys(o, "location", [frames[0]], [0.0], index=0, interpolation="CONSTANT")
    set_keys(o, "location", [frames[0]], [0.0], index=1, interpolation="CONSTANT")
    set_track(o, "location", frames, zs, index=2)
    set_track(o, "scale", frames, sz, index=2)
    set_track(o, "rotation_euler", frames, rx, index=0)
    set_visibility(o, [(rel, 10 ** 7)])


# ---------------------------------------------------------------------------
# Cameras
# ---------------------------------------------------------------------------

def _smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def _look(loc, target, prev=None):
    q = (target - loc).to_track_quat("-Z", "Y")
    return q.to_euler("XYZ", prev) if prev is not None else q.to_euler()


def animate_table_cam(cam, ftl):
    """Close on the pizza, then rocket straight up (the swipe hides the cut to space)."""
    a_one = ftl.segments["one"][0]
    cut = ftl.segments["zoom"][0] + int(1.25 * ftl.fps)
    cam.data.lens = 32.0
    cam.data.clip_start = 0.01
    cam.data.clip_end = 500.0
    p = Vector((0.0, 0.0, TABLE_Z + 0.02))
    keys = [(a_one, Vector((0.0, -0.62, TABLE_Z + 0.52))), (ftl.segments["zoom"][0], Vector((0.0, -0.58, TABLE_Z + 0.5))),
            (cut, Vector((0.0, -0.4, TABLE_Z + 40.0)))]
    prev = None
    for f, loc in keys:
        cam.location = loc
        cam.rotation_euler = _look(loc, p, prev)
        prev = cam.rotation_euler.copy()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    return cut


def plan_space_cam(cam, ftl, cut):
    """Hook close-up, the pull-back from the cut, then wide / medium shots of the fill."""
    fps = ftl.fps
    cam.data.lens = 50.0
    cam.data.clip_start = 5.0
    cam.data.clip_end = 60000.0
    hook_end = ftl.segments["hook"][1]
    b_zoom = ftl.segments["zoom"][1]
    full = ftl.segments["full"][0]
    fill_a, fill_b = ftl.segments["fill"]
    span = fill_b - fill_a

    WIDE = (0.0, 5600.0, 14.0, 0.05)
    CLOSE = (0.0, 2700.0, 8.0, 0.05)
    TOP = (650.0, 3300.0, 22.0, 0.05)
    poses = [(fill_a, WIDE), (fill_a + int(0.10 * span), "med"), (fill_a + int(0.24 * span), "med"),
             (fill_a + int(0.31 * span), WIDE), (fill_a + int(0.38 * span), WIDE),
             (fill_a + int(0.46 * span), "med"), (fill_a + int(0.72 * span), "med"),
             (fill_a + int(0.80 * span), WIDE), (full - int(3.0 * fps), WIDE), (full - int(1.0 * fps), TOP),
             (full, TOP), (ftl.hold_f, (500.0, 4600.0, 18.0, 0.05))]

    def params(pose, f):
        if pose == "med":
            lv = ftl.level[f]
            return (lv + 120.0, 2300.0, 30.0, 0.07)
        return pose

    keys = {}
    for f in range(0, hook_end + 1):                     # hook: slow push on the globe
        u = f / float(hook_end)
        keys[f] = (0.0, 3900.0 - 500.0 * u, 10.0, 186.0 - 6.0 * u, 0.05)
    for f in range(cut, ftl.hold_f + 1):
        if f < b_zoom:                                   # pull-back from just above the surface
            u = _smooth((f - cut) / float(b_zoom - cut))
            dist = math.exp(math.log(1150.0) + (math.log(WIDE[1]) - math.log(1150.0)) * u)
            keys[f] = (0.0, dist, 18.0 - 4.0 * u, 180.0, 0.05)
            continue
        i = max(k for k in range(len(poses)) if poses[k][0] <= f) if f >= poses[0][0] else 0
        j = min(i + 1, len(poses) - 1)
        fa, pa = poses[i]
        fb, pb = poses[j]
        u = 0.0 if fb == fa else _smooth((f - fa) / float(fb - fa))
        A, B = params(pa, f), params(pb, f)
        tz = A[0] + (B[0] - A[0]) * u
        dist = math.exp(math.log(A[1]) + (math.log(B[1]) - math.log(A[1])) * u)
        pitch = A[2] + (B[2] - A[2]) * u
        sy = A[3] + (B[3] - A[3]) * u
        # Orbit from the intact side round to the cutaway, then drift slowly.
        orbit_end = b_zoom + int(3.5 * fps)
        if f < orbit_end:
            yaw = 180.0 + 166.0 * _smooth((f - b_zoom) / float(orbit_end - b_zoom))
        else:
            yaw = 346.0 + 26.0 * (f - orbit_end) / float(max(1, ftl.hold_f - orbit_end))
        keys[f] = (tz, dist, pitch, yaw, sy)
    punches = [(m["frame"], 0.05) for m in ftl.milestones] + [(full, 0.08)]
    frames = sorted(keys)
    locs, rots, lens = [], [], []
    prev = None
    for f in frames:
        tz, dist, pitch, yaw, sy = keys[f]
        y, p = math.radians(yaw), math.radians(pitch)
        T = Vector((0.0, 0.0, tz))
        loc = T + Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
        rot = _look(loc, T, prev)
        prev = rot
        locs.append(loc)
        rots.append(rot)
        L = 50.0
        for pf, s in punches:
            t = f - pf
            if t >= 0:
                L *= 1.0 + s * (t / 2.0 if t < 2 else math.exp(-(t - 2) / 3.5))
        lens.append(L)
    for axis in range(3):
        set_keys(cam, "location", frames, [l[axis] for l in locs], index=axis, interpolation="BEZIER")
        set_keys(cam, "rotation_euler", frames, [r[axis] for r in rots], index=axis, interpolation="BEZIER")
    set_keys(cam.data, "shift_x", frames, [0.03] * len(frames), interpolation="CONSTANT")
    set_keys(cam.data, "shift_y", frames, [keys[f][4] for f in frames], interpolation="BEZIER")
    set_keys(cam.data, "lens", frames, lens, interpolation="BEZIER")
    camera.add_shake(cam, full, 24, 18.0, scale=1.4)
    return {f: keys[f][3] for f in frames}


def animate_sun(sun_obj, yaw_by_frame, ftl, offset=-40.0, el=22.0):
    """Keep the planet's camera-facing side in daylight as the camera orbits."""
    frames, rots = [], []
    last = None
    prev = None
    for f in range(ftl.total_frames):
        yaw = yaw_by_frame.get(f, last)
        if yaw is None:
            continue
        last = yaw
        az, e = math.radians(yaw + offset), math.radians(el)
        d = Vector((math.sin(az) * math.cos(e), -math.cos(az) * math.cos(e), math.sin(e)))
        q = (-d).to_track_quat("-Z", "Y")
        r = q.to_euler("XYZ", prev) if prev is not None else q.to_euler()
        prev = r
        frames.append(f)
        rots.append(r)
    for axis in range(3):
        set_track(sun_obj, "rotation_euler", frames, [r[axis] for r in rots], index=axis)


# ---------------------------------------------------------------------------
# Whole scene
# ---------------------------------------------------------------------------

def build_scene(cfg, ftl, width, height, samples):
    scene = reset_scene()
    scene.frame_start = 0
    scene.frame_end = ftl.total_frames
    studio.setup_render(scene, width, height, samples)
    space_world(scene)
    rng = random.Random(cfg["seed"])
    key_sun = sun("Sun", -40.0, 22.0, 3.6, (1.0, 0.95, 0.88))
    sun("BounceFill", 125.0, 10.0, 0.6, (0.45, 0.6, 1.0), shadow=False)

    shell, atmo, fill, cap, level_node = build_planet()
    set_track(level_node.outputs[0], "default_value", list(range(ftl.total_frames)),
              [lv + 0.5 for lv in ftl.level])
    animate_cap(cap, ftl)
    table = build_table_set()

    template = drop_objects.build("pizza")
    hero = bpy.data.objects.new("HeroPizza", template.data)
    scene.collection.objects.link(hero)
    animate_hero(hero, ftl)
    rain = []
    for i in range(RAIN_COUNT):
        o = bpy.data.objects.new("RainPizza_%02d" % i, template.data)
        scene.collection.objects.link(o)
        rain.append(o)
    animate_rain(rain, ftl, rng)
    burst = []
    for i in range(BURST_COUNT):
        o = bpy.data.objects.new("BurstPizza_%02d" % i, template.data)
        scene.collection.objects.link(o)
        burst.append(o)
    animate_burst(burst, ftl, rng)

    table_cam = camera.make_camera("TableCam", lens=32.0)
    space_cam = camera.make_camera("SpaceCam", lens=50.0)
    scene.camera = space_cam
    cut = animate_table_cam(table_cam, ftl)
    yaws = plan_space_cam(space_cam, ftl, cut)
    animate_sun(key_sun, yaws, ftl)

    studio.no_transparent_shadows()
    fill.visible_shadow = False
    cap.visible_shadow = False
    toon.outline_scene([hero] + rain + burst + table, 1.0)
    return {"scene": scene, "cams": {"space": space_cam, "table": table_cam}, "fill_cam": "space",
            "hero": (Vector((0.0, 0.0, TABLE_Z + 0.02)), "table"), "cut_frame": cut,
            "shots": [("space", 0, ftl.segments["hook"][1]), ("table", ftl.segments["hook"][1], cut),
                      ("space", cut, ftl.segments["outro"][0])]}
