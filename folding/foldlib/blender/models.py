"""Procedural landmark models, built from primitives at real-world size (metres).

Each landmark is made of one or more *groups*. A group is an empty (the
group's root) with mesh children modelled in metres around its base point.
animate.py places and scales each root every frame. Small things that would
be invisible at the scale they appear (a plane at 11 km, the Space Station
from 1,000 km away) have a `boost_min`: they are enlarged so their size is
at least that fraction of the view height. The overlay then shows a small
"enlarged for visibility" note.
"""

import math

import bmesh
import bpy
from mathutils import noise, Vector

from .. import style
from ..mathutil import hex_to_linear
from .util import (Nodes, add_box, add_cylinder, add_sphere, assign, bm_box,
                   mesh_from_bmesh, new_object, principled_material, set_blend_mode,
                   set_input)

R_EARTH = 6_371_000.0
MOON_RADIUS = 1_737_400.0
MOON_DISTANCE = 384_400_000.0
ISS_ALTITUDE = 408_000.0

_materials = {}


def mat(name, hex_colour, roughness=0.6, metallic=0.0, emission=0.0, specular=0.4):
    key = (name, hex_colour, roughness, metallic, emission)
    if key not in _materials:
        m, _, _ = principled_material(name, hex_colour, roughness, metallic, specular,
                                      emission_hex=hex_colour if emission else None,
                                      emission_strength=emission)
        _materials[key] = m
    return _materials[key]


class Group:
    def __init__(self, name, size_m, boost_min=0.0, pos=(0.0, 0.0, 0.0), on_ground=True):
        self.name = name
        self.root = new_object(name, None)
        self.root.empty_display_size = 0.1
        self.objects = []
        self.anchors = {}
        self.size_m = size_m            # characteristic size, for boosting
        self.boost_min = boost_min      # min size as a fraction of view height
        self.pos = pos                  # base position in metres (x, y, z)
        self.on_ground = on_ground      # sink with the Earth's curvature
        self.rotation_z = 0.0
        self.rings = []                 # orbit rings (scaled separately)

    def add(self, name, bm, material, smooth=False):
        obj = new_object(name, mesh_from_bmesh(name, bm, smooth), parent=self.root)
        assign(obj, material)
        self.objects.append(obj)
        return obj


class Landmark:
    def __init__(self, lm_def, window):
        self.id = lm_def["id"]
        self.defn = lm_def
        self.window = window
        self.groups = {}


# --- Builders ---------------------------------------------------------------------

def build_notebook(lm):
    x, y = lm["pos"]
    g = Group("notebook", 0.21, pos=(x, y, 0.0))
    w, d, h = 0.148, 0.210, 0.015
    cover = mat("NotebookCover", "#C4473A", 0.55)
    pages = mat("NotebookPages", "#F2EDE2", 0.8)
    band = mat("NotebookBand", "#1D1F26", 0.4)
    g.add("nb_bottom", bm_box(w, d, 0.0012), cover)
    g.add("nb_pages", bm_box(w - 0.004, d - 0.004, h - 0.0024, offset=(0.001, 0, 0.0012)), pages)
    g.add("nb_top", bm_box(w, d, 0.0012, offset=(0, 0, h - 0.0012)), cover)
    g.add("nb_spine", bm_box(0.004, d, h, offset=(-w / 2 + 0.002, 0, 0)), cover)
    g.add("nb_band", bm_box(0.007, d + 0.001, h + 0.0012, offset=(w / 2 - 0.022, 0, -0.0006)), band)
    g.anchors["main"] = (w / 2 - 0.022, -d / 2 + 0.02, h)
    g.rotation_z = math.radians(-8)
    return [g]


def build_phone(lm):
    x, y = lm["pos"]
    g = Group("phone", 0.147, pos=(x, y, 0.0))
    w, d, h = 0.0715, 0.0078, 0.147
    body = g.add("phone_body", bm_box(w, d, h), mat("PhoneBody", "#26272C", 0.35, 0.3))
    bevel = body.modifiers.new("round", "BEVEL")
    bevel.width = 0.006
    bevel.segments = 6
    bevel.limit_method = "ANGLE"
    screen = mat("PhoneScreen", "#1E3F6E", 0.15, 0.0, emission=0.45)
    g.add("phone_screen", bm_box(w - 0.006, 0.0006, h - 0.008, offset=(0, -d / 2 - 0.0002, 0.004)), screen)
    g.add("phone_cam", bm_box(0.012, 0.0006, 0.0035, offset=(0, -d / 2 - 0.0006, h - 0.014)),
          mat("PhoneBody", "#26272C", 0.35, 0.3))
    g.anchors["main"] = (0.0, 0.0, h)
    g.face_camera = True
    return [g]


def build_person(lm):
    x, y = lm["pos"]
    g = Group("person", 1.75, pos=(x, y, 0.0))
    bm = bmesh.new()
    for side in (-1, 1):
        add_cylinder(bm, 0.072, 0.062, 0.86, cx=side * 0.095, z0=0.0, segments=16)      # legs
        add_cylinder(bm, 0.052, 0.045, 0.62, cx=side * 0.255, z0=0.80, segments=12)    # arms
        add_sphere(bm, 0.05, cx=side * 0.255, cz=0.80, segments=12, rings=6)           # hands
        add_sphere(bm, 0.06, cx=side * 0.24, cz=1.40, segments=12, rings=6)            # shoulders
    add_cylinder(bm, 0.17, 0.215, 0.60, z0=0.82, segments=20)                          # torso
    add_cylinder(bm, 0.05, 0.05, 0.12, z0=1.40, segments=12)                           # neck
    add_sphere(bm, 0.115, cz=1.635, segments=20, rings=12)                             # head
    # Flatten front-to-back a little so it reads as a figure, not a pillar.
    for v in bm.verts:
        v.co.y *= 0.62
    g.add("person_body", bm, mat("Person", "#E2725B", 0.6), smooth=True)
    g.anchors["main"] = (0.0, 0.0, 1.75)
    g.face_camera = True
    return [g]


def build_big_ben(lm):
    x, y = lm["pos"]
    g = Group("big_ben", 96.0, pos=(x, y, 0.0))
    stone = mat("Sandstone", "#D5BC8A", 0.75)
    trim = mat("Gold", "#D9A93A", 0.35, 0.6)
    slate = mat("Slate", "#3D4B5B", 0.6)
    face = mat("ClockFace", "#FFF5DA", 0.5, emission=0.35)
    dark = mat("ClockHands", "#20242B", 0.5)

    bm = bmesh.new()
    add_box(bm, 12, 12, 55)                                     # shaft
    for sx in (-1, 1):                                          # corner buttresses
        for sy in (-1, 1):
            add_box(bm, 1.4, 1.4, 69, cx=sx * 6.0, cy=sy * 6.0)
    add_box(bm, 13.6, 13.6, 14, z0=55)                          # clock stage
    add_box(bm, 11.2, 11.2, 7.5, z0=70)                         # belfry
    g.add("bb_stone", bm, stone)

    bm = bmesh.new()
    add_box(bm, 14.4, 14.4, 1.0, z0=69)                         # gold band
    for sx in (-1, 1):
        for sy in (-1, 1):
            add_cylinder(bm, 0.9, 0.0, 6.0, cx=sx * 6.4, cy=sy * 6.4, z0=70, segments=8)
    add_cylinder(bm, 1.0, 0.0, 6.0, z0=90, segments=8)          # spire tip
    g.add("bb_trim", bm, trim)

    bm = bmesh.new()
    add_cylinder(bm, 8.2, 0.9, 13.0, z0=77.5, segments=4, rotate_z=math.pi / 4)  # roof
    g.add("bb_roof", bm, slate)

    bm_face, bm_hands = bmesh.new(), bmesh.new()
    for ang in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        c, s = math.cos(ang), math.sin(ang)
        _add_disc(bm_face, 3.6, 0.3, (c * 6.85, s * 6.85, 62.0), (c, s))
        _add_hand(bm_hands, (c * 7.05, s * 7.05, 62.0), (c, s), 2.8, 0.35, math.radians(60))
        _add_hand(bm_hands, (c * 7.08, s * 7.08, 62.0), (c, s), 2.0, 0.45, math.radians(-100))
    g.add("bb_faces", bm_face, face)
    g.add("bb_hands", bm_hands, dark)
    g.anchors["main"] = (0.0, 0.0, 96.0)
    return [g]


def _add_disc(bm, radius, depth, centre, normal):
    """A cylinder disc whose axis points along the horizontal `normal`."""
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, segments=32, radius1=radius, radius2=radius, depth=depth)
    ang = math.atan2(normal[1], normal[0])
    for v in tmp.verts:
        # cone axis is z: rotate z->x, then spin around z to face `normal`
        px, py, pz = v.co.z, v.co.y, -v.co.x
        v.co.x = px * math.cos(ang) - py * math.sin(ang) + centre[0]
        v.co.y = px * math.sin(ang) + py * math.cos(ang) + centre[1]
        v.co.z = pz + centre[2]
    _merge_into(bm, tmp)


def _add_hand(bm, centre, normal, length, width, angle):
    tmp = bm_box(0.2, width, length)
    ang = math.atan2(normal[1], normal[0])
    for v in tmp.verts:
        # rotate the hand around the face normal, then orient to the face
        y, z = v.co.y, v.co.z
        y2 = y * math.cos(angle) - z * math.sin(angle)
        z2 = y * math.sin(angle) + z * math.cos(angle)
        px, py = v.co.x, y2
        v.co.x = px * math.cos(ang) - py * math.sin(ang) + centre[0]
        v.co.y = px * math.sin(ang) + py * math.cos(ang) + centre[1]
        v.co.z = z2 + centre[2]
    _merge_into(bm, tmp)


def _merge_into(dst, src):
    from .util import _merge
    _merge(dst, src)


def build_burj(lm):
    x, y = lm["pos"]
    g = Group("burj_khalifa", 828.0, pos=(x, y, 0.0))
    glass = mat("BurjGlass", "#6F8597", 0.28, 0.45)
    steel = mat("BurjSteel", "#AEB9C4", 0.3, 0.6)
    bm = bmesh.new()
    # Three wings around a core that step back as the tower rises (the
    # signature spiral setbacks), topped by a long spire.
    core_tiers = [(0, 600, 26.0, 9.0)]
    for z0, z1, r0, r1 in core_tiers:
        add_cylinder(bm, r0, r1, z1 - z0, z0=z0, segments=6)
    wing_steps = 9
    for k in range(3):
        ang = math.radians(90 + 120 * k)
        for step in range(wing_steps):
            top = 160 + step * 48 + k * 16            # each wing ends at a different height
            z0 = 0 if step == 0 else 160 + (step - 1) * 48 + k * 16
            length = 74.0 * (1 - step / (wing_steps + 1.0))
            width = 30.0 * (1 - step / (wing_steps + 3))
            cx = math.cos(ang) * length / 2
            cy = math.sin(ang) * length / 2
            tmp = bm_box(length, width, top - z0, offset=(0, 0, z0))
            for v in tmp.verts:
                vx, vy = v.co.x, v.co.y
                v.co.x = vx * math.cos(ang) - vy * math.sin(ang) + cx
                v.co.y = vx * math.sin(ang) + vy * math.cos(ang) + cy
            _merge_into(bm, tmp)
    g.add("burj_body", bm, glass)
    bm = bmesh.new()
    add_cylinder(bm, 9.0, 4.0, 110, z0=600, segments=6)
    add_cylinder(bm, 4.0, 0.6, 118, z0=710, segments=6)
    g.add("burj_spire", bm, steel)
    g.anchors["main"] = (0.0, 0.0, 828.0)
    return [g]


def build_everest_planes(lm):
    x, y = lm["pos"]
    mountain = Group("everest", 8849.0, pos=(x, y, 0.0))
    bm = bmesh.new()
    _add_mountain(bm, 8849.0, 7800.0, seed=3)
    _add_mountain(bm, 7100.0, 5200.0, seed=9, cx=-6500.0, cy=3500.0)
    _add_mountain(bm, 6300.0, 4600.0, seed=17, cx=5200.0, cy=5200.0)
    mountain.add("everest_rock", bm, _mountain_material(), smooth=True)
    mountain.anchors["main"] = (0.0, 0.0, 8849.0)

    plane = Group("plane", 70.0, boost_min=0.07, pos=(-2600.0, -2600.0, 11000.0), on_ground=False)
    plane.rotation_z = math.pi        # fly toward the column; the trail streams away from it
    white = mat("PlaneWhite", "#F2F4F7", 0.4)
    tail = mat("PlaneTail", style.ACCENT, 0.45)
    bm = bmesh.new()
    _add_fuselage(bm)
    for side in (-1, 1):
        _add_wing(bm, side, root=(-2.0, 0.0, -0.8), span=30.0, chord=9.0, sweep=11.0, thick=0.9)
        _add_wing(bm, side, root=(26.0, 0.0, 1.0), span=10.0, chord=4.5, sweep=5.0, thick=0.4)
    plane.add("plane_body", bm, white, smooth=False)
    bm = bmesh.new()
    _add_fin(bm)
    plane.add("plane_fin", bm, tail)
    plane.add("plane_trail", _contrail(), _trail_material())
    plane.anchors["plane"] = (0.0, 0.0, 14.0)
    return [mountain, plane]


def _add_mountain(bm, height, radius, seed, cx=0.0, cy=0.0, rings=28, segs=72):
    verts, faces = [], []
    tmp = bmesh.new()
    rows = []
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for i in range(rings + 1):
        r = radius * i / rings
        row = []
        for j in range(segs if i else 1):
            a = 2 * math.pi * j / segs
            p = Vector((math.cos(a) * r, math.sin(a) * r, 0))
            prof = (1 - i / rings) ** 1.6
            n = noise.noise(p / (radius * 0.35) + off) * 0.18 + noise.noise(p / (radius * 0.12) + off) * 0.07
            ridge = 0.08 * math.cos(3 * a + seed) * (i / rings)
            z = height * max(0.0, prof * (1 + n + ridge)) if i else height
            row.append(tmp.verts.new((p.x + cx, p.y + cy, z)))
        rows.append(row)
    for j in range(segs):
        tmp.faces.new((rows[0][0], rows[1][j], rows[1][(j + 1) % segs]))
    for i in range(1, rings):
        for j in range(segs):
            a, b = rows[i][j], rows[i][(j + 1) % segs]
            c, d = rows[i + 1][(j + 1) % segs], rows[i + 1][j]
            tmp.faces.new((a, d, c, b))
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    _merge_into(bm, tmp)


def _mountain_material():
    m, nb, bsdf = principled_material("Mountain", "#6E6A65", 0.85)
    coord = nb.new("ShaderNodeTexCoord")
    z = nb.separate(coord.outputs["Object"])[2]
    nz = nb.separate(nb.new("ShaderNodeNewGeometry").outputs["Normal"])[2]
    snow = nb.math("MULTIPLY", nb.map_range(z, 4600.0, 5600.0), nb.map_range(nz, 0.35, 0.6))
    low = nb.map_range(z, 300.0, 2200.0, 1.0, 0.0)
    col = nb.mix(low, hex_to_linear("#716B66", 1.0), hex_to_linear("#55684C", 1.0))
    col = nb.mix(snow, col, hex_to_linear("#F4F6F8", 1.0))
    set_input(bsdf, "Base Color", col)
    return m


def _add_fuselage(bm):
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, segments=20, radius1=3.0, radius2=3.0, depth=52.0)
    _rot_to_x(tmp, offset=(0, 0, 0))
    _merge_into(bm, tmp)
    add_sphere(bm, 3.0, cx=-26.0, segments=20, rings=10, scale=(2.0, 1.0, 1.0))      # nose
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, segments=20, radius1=3.0, radius2=0.8, depth=14.0)
    _rot_to_x(tmp, offset=(33.0, 0, 0.9))
    _merge_into(bm, tmp)
    for side in (-1, 1):                                                              # engines
        tmp = bmesh.new()
        bmesh.ops.create_cone(tmp, cap_ends=True, segments=14, radius1=1.4, radius2=1.2, depth=5.5)
        _rot_to_x(tmp, offset=(-6.0, side * 10.0, -2.6))
        _merge_into(bm, tmp)


def _rot_to_x(tmp, offset):
    for v in tmp.verts:
        x, y, z = v.co.z, v.co.y, -v.co.x
        v.co.x, v.co.y, v.co.z = x + offset[0], y + offset[1], z + offset[2]


def _add_wing(bm, side, root, span, chord, sweep, thick):
    tmp = bmesh.new()
    x0, y0, z0 = root
    tip_chord = chord * 0.35
    pts = [(x0, y0, z0), (x0 + chord, y0, z0),
           (x0 + sweep + tip_chord, y0 + side * span, z0 + 1.2), (x0 + sweep, y0 + side * span, z0 + 1.2)]
    top = [tmp.verts.new((p[0], p[1], p[2] + thick / 2)) for p in pts]
    bot = [tmp.verts.new((p[0], p[1], p[2] - thick / 2)) for p in pts]
    tmp.faces.new(top)
    tmp.faces.new(list(reversed(bot)))
    for i in range(4):
        j = (i + 1) % 4
        tmp.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    _merge_into(bm, tmp)


def _add_fin(bm):
    tmp = bmesh.new()
    pts = [(28.0, 0, 2.0), (38.5, 0, 2.0), (40.5, 0, 13.0), (35.0, 0, 13.0)]
    a = [tmp.verts.new((p[0], -0.35, p[2])) for p in pts]
    b = [tmp.verts.new((p[0], 0.35, p[2])) for p in pts]
    tmp.faces.new(a)
    tmp.faces.new(list(reversed(b)))
    for i in range(4):
        j = (i + 1) % 4
        tmp.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    _merge_into(bm, tmp)


def _contrail():
    bm = bmesh.new()
    for side in (-1, 1):
        tmp = bmesh.new()
        bmesh.ops.create_cone(tmp, cap_ends=False, segments=10, radius1=1.0, radius2=3.2, depth=520.0)
        _rot_to_x(tmp, offset=(262.0, side * 10.0, -2.6))
        _merge_into(bm, tmp)
    return bm


def _trail_material():
    m = bpy.data.materials.new("Contrail")
    m.use_nodes = True
    nb = Nodes(m.node_tree)
    nb.clear()
    out = nb.new("ShaderNodeOutputMaterial")
    coord = nb.new("ShaderNodeTexCoord")
    x = nb.separate(coord.outputs["Object"])[0]
    alpha = nb.math("MULTIPLY", nb.map_range(x, 4.0, 40.0), nb.map_range(x, 200.0, 520.0, 1.0, 0.0))
    alpha = nb.math("MULTIPLY", alpha, 0.75)
    emit = nb.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (1, 1, 1, 1)
    emit.inputs["Strength"].default_value = 1.0
    clear = nb.new("ShaderNodeBsdfTransparent")
    mix = nb.new("ShaderNodeMixShader")
    nb.link(alpha, mix.inputs[0])
    nb.link(clear.outputs[0], mix.inputs[1])
    nb.link(emit.outputs[0], mix.inputs[2])
    nb.link(mix.outputs[0], out.inputs["Surface"])
    set_blend_mode(m, "BLEND")
    return m


def build_space_station(lm):
    x, _ = lm["pos"]
    g = Group("space_station", 109.0, boost_min=0.085, pos=(x, 0.0, ISS_ALTITUDE), on_ground=False)
    metal = mat("IssMetal", "#E3E6EA", 0.35, 0.6)
    panel = mat("IssPanel", "#C8963A", 0.35, 0.5)
    bm = bmesh.new()
    add_box(bm, 109.0, 3.0, 3.0, z0=-1.5)                                   # main truss
    for i in range(3):                                                       # modules
        tmp = bmesh.new()
        bmesh.ops.create_cone(tmp, cap_ends=True, segments=14, radius1=2.2, radius2=2.2, depth=16.0)
        for v in tmp.verts:
            v.co.x, v.co.y, v.co.z = v.co.x, v.co.z + (i - 1) * 15.0, v.co.y
        _merge_into(bm, tmp)
    add_box(bm, 8.0, 0.4, 14.0, cx=0.0, cy=8.0, z0=-7.0)                    # radiator
    g.add("iss_body", bm, metal)
    bm = bmesh.new()
    for sx in (-48.0, -36.0, 36.0, 48.0):
        for sz in (1.0, -1.0):
            add_box(bm, 11.0, 0.25, 33.0, cx=sx, z0=1.6 if sz > 0 else -34.6)
    g.add("iss_panels", bm, panel)
    g.anchors["main"] = (0.0, 0.0, 36.0)
    ring = _orbit_ring("iss_orbit")
    g.rings.append((ring, R_EARTH + ISS_ALTITUDE))
    return [g]


def build_moon(lm):
    g = Group("moon", MOON_RADIUS, boost_min=0.014, on_ground=False)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=MOON_RADIUS)
    g.add("moon_body", bm, _moon_material(), smooth=True)
    g.anchors["main"] = (0.0, 0.0, MOON_RADIUS)
    g.centre_anchor = True
    ring = _orbit_ring("moon_orbit")
    g.rings.append((ring, MOON_DISTANCE))
    return [g]


def _moon_material():
    m, nb, bsdf = principled_material("Moon", style.MOON_COLOUR, 0.95, specular=0.1)
    coord = nb.new("ShaderNodeTexCoord")
    obj = coord.outputs["Object"]
    vor = nb.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "3D"
    vor.inputs["Scale"].default_value = 3.5e-6
    nb.link(obj, vor.inputs["Vector"])
    crater = nb.map_range(vor.outputs["Distance"], 0.12, 0.3)
    mare = nb.new("ShaderNodeTexNoise")
    mare.inputs["Scale"].default_value = 1.2e-6
    nb.link(obj, mare.inputs["Vector"])
    dark = nb.map_range(mare.outputs["Fac"], 0.5, 0.6)
    col = nb.mix(dark, hex_to_linear(style.MOON_COLOUR, 1.0), hex_to_linear("#8E8A84", 1.0))
    col = nb.mix(nb.math("SUBTRACT", 1.0, crater), col, hex_to_linear("#A7A39C", 1.0))
    set_input(bsdf, "Base Color", col)
    return m


def _orbit_ring(name):
    """Unit circle in the x-z plane (faces the camera); bevel set per frame."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    spline = curve.splines.new("NURBS")
    pts = 64
    spline.points.add(pts - 1)
    for i in range(pts):
        a = 2 * math.pi * i / pts
        spline.points[i].co = (math.cos(a), 0.0, math.sin(a), 1.0)
    spline.use_cyclic_u = True
    spline.order_u = 4
    curve.bevel_depth = 0.001
    curve.bevel_resolution = 2
    obj = new_object(name, curve)
    m = bpy.data.materials.new(name + "Mat")
    m.use_nodes = True
    nb = Nodes(m.node_tree)
    nb.clear()
    out = nb.new("ShaderNodeOutputMaterial")
    emit = nb.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (1, 1, 1, 1)
    emit.inputs["Strength"].default_value = 0.9
    clear = nb.new("ShaderNodeBsdfTransparent")
    mix = nb.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.45
    nb.link(clear.outputs[0], mix.inputs[1])
    nb.link(emit.outputs[0], mix.inputs[2])
    nb.link(mix.outputs[0], out.inputs["Surface"])
    set_blend_mode(m, "BLEND")
    obj.data.materials.append(m)
    obj["ring_alpha_node"] = mix.name
    return obj


BUILDERS = {
    "notebook": build_notebook,
    "phone": build_phone,
    "person": build_person,
    "big_ben": build_big_ben,
    "burj_khalifa": build_burj,
    "everest_planes": build_everest_planes,
    "space_station": build_space_station,
    "moon": build_moon,
}


def build_landmarks(timeline):
    """Build the models for every beat this episode reaches."""
    out = []
    for win in timeline.landmark_windows:
        lm_def = win["landmark"]   # library entry, placed for this episode
        lm = Landmark(lm_def, win)
        for group in BUILDERS[win["id"]](lm_def):
            lm.groups[group.name] = group
            for obj in group.objects:
                obj.hide_render = True
            for ring, _ in group.rings:
                ring.hide_render = True
        out.append(lm)
    return out
