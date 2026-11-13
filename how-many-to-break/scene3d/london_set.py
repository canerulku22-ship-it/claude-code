"""A stylised, procedural London at dusk for the kaiju episode (metres, river along X).

Layout: the Thames runs along X (banks at y = +/-130, land at z = 4). On the north bank:
the Palace of Westminster with the Victoria Tower, and Big Ben (Elizabeth Tower) at
(35, 175). Westminster Bridge crosses at x = 60. On the south bank: the London Eye at
(320, -180), and a row of buildings it slices through when it rolls east. Further out:
the Shard and Tower Bridge, plus streets of generic buildings with lit windows.

Big Ben is built in two pieces (``BigBenTop`` is what gets bitten off), and the Eye's
wheel hangs off an empty (``EyeWheel``) so it can detach and roll.
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import materials as M
from .skyscraper import city_block_material
from .util import box_bmesh, cylinder_bmesh, empty, mesh_from_bmesh, new_object

LAND_Z = 4.0
BANK_Y = 130.0
BIG_BEN = Vector((35.0, 175.0, LAND_Z))
BRIDGE_X = 60.0
EYE_HUB = Vector((320.0, -180.0, LAND_Z + 69.0))
EYE_R = 60.0
SLICE_XS = [450.0, 530.0, 610.0, 690.0, 770.0, 850.0, 930.0]
SLICE_Y = -180.0


def _obj(name, bm, mat, location=(0, 0, 0), smooth=False):
    me = mesh_from_bmesh(name, bm, smooth=smooth)
    if mat is not None:
        me.materials.append(mat)
    return new_object(name, me, location=location)


def _pyramid(bm, base, height, center):
    cx, cy, z = center
    h = base / 2
    vs = [bm.verts.new((cx + sx * h, cy + sy * h, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    apex = bm.verts.new((cx, cy, z + height))
    bm.faces.new(vs[::-1])
    for i in range(4):
        bm.faces.new((vs[i], vs[(i + 1) % 4], apex))
    return bm


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def water_material():
    mat, fresh = M.new_material("Thames")
    if not fresh:
        return mat
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.08
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Base Color"].default_value = (0.03, 0.09, 0.12, 1)
    bsdf.inputs["Roughness"].default_value = 0.18
    M._set(bsdf, "specular", 0.6)
    return mat


def stone_material(name="Limestone", color=(0.80, 0.66, 0.44)):
    """Gothic limestone with lit windows (vertical slits) for the Palace and Big Ben."""
    mat, fresh = M.new_material(name)
    if not fresh:
        return mat
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
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
    brick.inputs["Scale"].default_value = 0.22
    brick.inputs["Mortar Size"].default_value = 0.55
    brick.inputs["Brick Width"].default_value = 0.4
    brick.inputs["Row Height"].default_value = 1.6
    nt.links.new(comb.outputs[0], brick.inputs["Vector"])
    win = nt.nodes.new("ShaderNodeMath")
    win.operation = "SUBTRACT"
    win.inputs[0].default_value = 1.0
    nt.links.new(brick.outputs["Fac"], win.inputs[1])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(win.outputs[0], col.inputs["Factor"])
    col.inputs[6].default_value = (*color, 1)
    col.inputs[7].default_value = (0.25, 0.18, 0.10, 1)
    nt.links.new(col.outputs[2], bsdf.inputs["Base Color"])
    em = M._input(bsdf, "emission")
    em.default_value = (1.0, 0.72, 0.35, 1)
    lit = nt.nodes.new("ShaderNodeMath")
    lit.operation = "MULTIPLY"
    nt.links.new(win.outputs[0], lit.inputs[0])
    lit.inputs[1].default_value = 1.6
    nt.links.new(lit.outputs[0], bsdf.inputs["Emission Strength"])
    bsdf.inputs["Roughness"].default_value = 0.7
    mat.diffuse_color = (*color, 1)
    return mat


# ---------------------------------------------------------------------------
# Landmarks
# ---------------------------------------------------------------------------

def build_ground():
    river = _obj("Thames", box_bmesh(8000, 2 * BANK_Y, 1.0, center=(0, 0, -0.5)), water_material())
    grass = M.principled("Embankment", color=(0.12, 0.13, 0.12), roughness=0.85)
    north = _obj("NorthBank", box_bmesh(8000, 4000, LAND_Z + 20, center=(0, BANK_Y + 2000, LAND_Z / 2 - 10)), grass)
    south = _obj("SouthBank", box_bmesh(8000, 4000, LAND_Z + 20, center=(0, -BANK_Y - 2000, LAND_Z / 2 - 10)), grass)
    return [river, north, south]


def build_parliament():
    stone = stone_material()
    bm = bmesh.new()
    box_bmesh(400, 90, 26, center=(-180, 195, LAND_Z + 13), bm=bm)
    for x in range(-375, 20, 14):                     # pinnacles along the river front and roof
        box_bmesh(2.2, 2.2, 12, center=(x, 151, LAND_Z + 32), bm=bm)
        box_bmesh(2.2, 2.2, 8, center=(x + 7, 238, LAND_Z + 30), bm=bm)
    for x in (-330, -260, -110, -40):
        box_bmesh(14, 14, 22, center=(x, 175, LAND_Z + 37), bm=bm)
        _pyramid(bm, 14, 10, (x, 175, LAND_Z + 48))
    # Victoria Tower and the central spire.
    box_bmesh(24, 24, 98, center=(-380, 200, LAND_Z + 49), bm=bm)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box_bmesh(3, 3, 10, center=(-380 + sx * 11, 200 + sy * 11, LAND_Z + 103), bm=bm)
    cylinder_bmesh(9, 50, segments=8, center=(-180, 195, LAND_Z + 50), bm=bm)
    cylinder_bmesh(9, 30, segments=8, radius2=0.5, center=(-180, 195, LAND_Z + 90), bm=bm)
    return _obj("Parliament", bm, stone)


def build_big_ben():
    """Elizabeth Tower in two pieces: the shaft, and the top that gets bitten off."""
    stone = stone_material("BigBenStone", color=(0.82, 0.68, 0.42))
    x, y, z = BIG_BEN
    shaft = _obj("BigBenBase", box_bmesh(12, 12, 59, center=(x, y, z + 29.5)), stone)
    bm = bmesh.new()
    box_bmesh(13.5, 13.5, 9, center=(x, y, z + 63.5), bm=bm)        # clock stage
    box_bmesh(12, 12, 8, center=(x, y, z + 72), bm=bm)               # belfry
    _pyramid(bm, 12.5, 18, (x, y, z + 76))                           # roof
    cylinder_bmesh(0.6, 6, segments=8, center=(x, y, z + 96), bm=bm)  # finial
    top = _obj("BigBenTop", bm, stone)
    # Glowing clock faces with hands on all four sides.
    face_mat = M.principled("ClockFace", color=(0.95, 0.92, 0.8), roughness=0.4,
                            emission=(1.0, 0.92, 0.7), emission_strength=1.6)
    hand_mat = M.principled("ClockHands", color=(0.02, 0.02, 0.02), roughness=0.5)
    parts = []
    for ang in (0, 90, 180, 270):
        a = math.radians(ang)
        d = Vector((math.sin(a), -math.cos(a), 0))
        c = Vector((x, y, z + 63.5)) + d * 6.8
        face = _obj("ClockFace", cylinder_bmesh(3.6, 0.3, segments=32), face_mat, location=c)
        face.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        hb = bmesh.new()
        box_bmesh(0.35, 2.6, 0.2, center=(0, 1.2, 0.25), bm=hb)
        box_bmesh(0.3, 1.8, 0.2, center=(0.8, 0, 0.25), bm=hb)
        hands = _obj("ClockHands", hb, hand_mat, location=c)
        hands.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        parts += [face, hands]
    for p in parts:
        p.parent = top
        p.matrix_parent_inverse = top.matrix_world.inverted()
    return shaft, top, parts


def build_bridge():
    green = M.principled("BridgeGreen", color=(0.12, 0.40, 0.25), roughness=0.5)
    deck = M.principled("Tarmac", color=(0.08, 0.08, 0.09), roughness=0.8)
    bm = bmesh.new()
    box_bmesh(26, 2 * BANK_Y + 40, 1.5, center=(BRIDGE_X, 0, LAND_Z + 6.25), bm=bm)
    top = _obj("BridgeDeck", bm, deck)
    sb = bmesh.new()
    for sx in (-1, 1):
        box_bmesh(1.2, 2 * BANK_Y + 40, 4, center=(BRIDGE_X + sx * 13, 0, LAND_Z + 5), bm=sb)
    for py in (-95, -45, 0, 45, 95):
        box_bmesh(22, 9, LAND_Z + 6, center=(BRIDGE_X, py, (LAND_Z + 6) / 2 - 1), bm=sb)
    sides = _obj("BridgeSides", sb, green)
    return [top, sides]


def _torus(bm, major, minor, seg=96, ring=10):
    rows = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        rows.append([bm.verts.new(((major + minor * math.cos(b)) * math.cos(a), 0.0 + minor * math.sin(b),
                                   (major + minor * math.cos(b)) * math.sin(a)))
                     for b in (2 * math.pi * j / ring for j in range(ring))])
    for i in range(seg):
        for j in range(ring):
            r0, r1 = rows[i], rows[(i + 1) % seg]
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % ring], r0[(j + 1) % ring]))


def build_london_eye():
    """The wheel (rim, spokes, capsules) hangs off EyeWheel so it can roll away."""
    white = M.principled("EyeWhite", color=(0.88, 0.9, 0.93), roughness=0.3, metallic=0.4)
    glass = M.principled("Capsule", color=(0.7, 0.85, 0.95), roughness=0.1, emission=(0.6, 0.8, 1.0),
                         emission_strength=0.6)
    hub = empty("EyeWheel", location=EYE_HUB)
    bm = bmesh.new()
    _torus(bm, EYE_R, 1.1)
    _torus(bm, EYE_R - 7, 0.6)
    for k in range(32):
        a = 2 * math.pi * k / 32
        d = Vector((math.cos(a), 0, math.sin(a)))
        spoke = cylinder_bmesh(0.25, EYE_R, segments=6)
        m = Matrix.Translation(d * EYE_R / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bm2 = spoke
        bmesh.ops.transform(bm2, matrix=m, verts=bm2.verts)
        me = bpy.data.meshes.new("tmp")
        bm2.to_mesh(me)
        bm2.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    hb = cylinder_bmesh(3.0, 9.0, segments=16)
    bmesh.ops.rotate(hb, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"), verts=hb.verts)
    me = bpy.data.meshes.new("tmp")
    hb.to_mesh(me)
    hb.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    wheel = _obj("EyeRim", bm, white)
    wheel.parent = hub                  # sits at the hub's origin
    caps = bmesh.new()
    for k in range(32):
        a = 2 * math.pi * k / 32
        c = Vector((math.cos(a), 0, math.sin(a))) * (EYE_R + 3.5)
        res = bmesh.ops.create_uvsphere(caps, u_segments=12, v_segments=8, radius=1.0)
        bmesh.ops.scale(caps, vec=(2.2, 4.0, 2.2), verts=res["verts"])
        bmesh.ops.translate(caps, vec=c, verts=res["verts"])
    capsules = _obj("EyeCapsules", caps, glass, smooth=True)
    capsules.parent = hub
    # A-frame legs (stay behind when the wheel rolls away).
    lb = bmesh.new()
    for sx in (-1, 1):
        base = Vector((EYE_HUB.x + sx * 28, EYE_HUB.y - 50, LAND_Z))
        top = EYE_HUB + Vector((0, -6, 0))
        d = top - base
        leg = cylinder_bmesh(1.4, d.length, segments=8)
        m = Matrix.Translation(base + d / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.transform(leg, matrix=m, verts=leg.verts)
        me = bpy.data.meshes.new("tmp")
        leg.to_mesh(me)
        leg.free()
        lb.from_mesh(me)
        bpy.data.meshes.remove(me)
    legs = _obj("EyeLegs", lb, white)
    return hub, [wheel, capsules], legs


def build_skyline():
    glass = M.principled("ShardGlass", color=(0.55, 0.65, 0.78), roughness=0.15, metallic=0.5,
                         emission=(0.45, 0.6, 0.9), emission_strength=0.25)
    shard = _obj("Shard", _pyramid(bmesh.new(), 60, 310, (1400, -900, LAND_Z)), glass)
    stone = stone_material("TowerBridgeStone", color=(0.75, 0.70, 0.60))
    blue = M.principled("TowerBridgeBlue", color=(0.25, 0.55, 0.85), roughness=0.4)
    tb = bmesh.new()
    for sy in (-55, 55):
        box_bmesh(18, 18, 62, center=(1700, sy, LAND_Z + 27), bm=tb)
        _pyramid(tb, 16, 14, (1700, sy, LAND_Z + 58))
    towers = _obj("TowerBridge", tb, stone)
    wb = bmesh.new()
    box_bmesh(6, 92, 4, center=(1700, 0, LAND_Z + 44), bm=wb)
    box_bmesh(14, 92, 2, center=(1700, 0, LAND_Z + 9), bm=wb)
    walk = _obj("TowerBridgeWalk", wb, blue)
    return [shard, towers, walk]


def window_material(name, tone, bay=4.0, floor=3.6, win_w=0.5, win_h=0.55, lit=0.5, glow=2.4):
    """Facade with a grid of windows, about half of them lit (dusk). Object coordinates in metres.

    The horizontal coordinate is x + y, which runs along any wall of an axis-aligned box.
    Each window cell gets a random value (white noise on the cell index) to decide if it's lit.
    """
    mat, fresh = M.new_material(name)
    if not fresh:
        return mat
    nt = mat.node_tree
    L = nt.links
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    L.new(bsdf.outputs[0], out.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    L.new(tex.outputs["Object"], sep.inputs[0])
    def mth(op, a, b=None):          # math node on sockets/numbers, returns its output socket
        return M._math(nt, op, a, b).outputs[0]

    u = mth("DIVIDE", mth("ADD", sep.outputs[0], sep.outputs[1]), bay)
    v = mth("DIVIDE", sep.outputs[2], floor)

    def band(x, width):          # 1 inside the centred band of the cell
        return mth("LESS_THAN", mth("ABSOLUTE", mth("SUBTRACT", mth("FRACT", x), 0.5)), width / 2)

    window = mth("MULTIPLY", band(u, win_w), band(v, win_h))
    window = mth("MULTIPLY", window, mth("GREATER_THAN", v, 0.8))     # none at street level
    cell = nt.nodes.new("ShaderNodeCombineXYZ")
    L.new(mth("FLOOR", u), cell.inputs[0])
    L.new(mth("FLOOR", v), cell.inputs[1])
    info = nt.nodes.new("ShaderNodeObjectInfo")
    L.new(mth("MULTIPLY", info.outputs["Random"], 97.0), cell.inputs[2])
    noise = nt.nodes.new("ShaderNodeTexWhiteNoise")
    noise.noise_dimensions = "3D"
    L.new(cell.outputs[0], noise.inputs["Vector"])
    glow_mask = mth("MULTIPLY", window, mth("LESS_THAN", noise.outputs["Value"], lit))
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    L.new(window, col.inputs["Factor"])
    col.inputs[6].default_value = (*tone, 1)
    col.inputs[7].default_value = (0.05, 0.06, 0.09, 1)
    L.new(col.outputs[2], bsdf.inputs["Base Color"])
    M._input(bsdf, "emission").default_value = (1.0, 0.72, 0.38, 1)
    L.new(mth("MULTIPLY", glow_mask, glow), bsdf.inputs["Emission Strength"])
    bsdf.inputs["Roughness"].default_value = 0.7
    mat.diffuse_color = (*tone, 1)
    return mat


def build_city(rng, keep_clear=()):
    """Generic blocks on both banks, avoiding the landmarks and the Eye's path."""
    tones = [(0.42, 0.24, 0.18), (0.55, 0.50, 0.42), (0.30, 0.30, 0.34), (0.48, 0.36, 0.26)]
    mats = [window_material("LondonBlock%d" % i, t) for i, t in enumerate(tones)]
    blocks = []
    tries = 0
    while len(blocks) < 190 and tries < 8000:
        tries += 1
        x = rng.uniform(-1800, 2200)
        y = rng.uniform(BANK_Y + 30, 1600) * rng.choice((-1, 1))
        if y > 0 and -420 < x < 80 and y < 300:          # Palace of Westminster / Big Ben
            continue
        if y < 0 and 230 < x < 1000 and y > -280:         # the Eye and its rolling path
            continue
        if y < 0 and x > 1250 and x < 1550 and -1050 < y < -750:   # the Shard
            continue
        if abs(x - 1700) < 120 and abs(y) < 250:          # Tower Bridge
            continue
        if abs(x - BRIDGE_X) < 30:
            continue
        # Camera positions and sight lines: (x, y, half-size) squares or (x0, y0, x1, y1) boxes.
        if any(abs(x - z[0]) < z[2] and abs(y - z[1]) < z[2] for z in keep_clear if len(z) == 3):
            continue
        if any(z[0] < x < z[2] and z[1] < y < z[3] for z in keep_clear if len(z) == 4):
            continue
        cap = min([z[4] for z in keep_clear if len(z) == 5 and z[0] < x < z[2] and z[1] < y < z[3]] or [1e9])
        w, d = rng.uniform(25, 60), rng.uniform(25, 60)
        h = min(cap, rng.uniform(14, 40) + (rng.random() ** 4) * 70)
        o = _obj("LondonBlock", box_bmesh(w, d, h, center=(0, 0, h / 2)), rng.choice(mats),
                 location=(x, y, LAND_Z))
        o.rotation_euler.z = rng.choice((0.0, math.pi / 2)) + rng.uniform(-0.1, 0.1)
        blocks.append(o)
    return blocks


def build_slice_row(rng):
    """Buildings on the Eye's path, each in two halves that fall apart when it passes."""
    mats = [window_material("SliceBlock%d" % i, t) for i, t in enumerate(((0.45, 0.26, 0.2), (0.55, 0.5, 0.42)))]
    halves = []
    for x in SLICE_XS:
        w, h = rng.uniform(48, 62), rng.uniform(24, 42)
        mat = rng.choice(mats)
        pair = []
        for side in (-1, 1):
            o = _obj("SliceHalf", box_bmesh(w, 22, h, center=(0, side * 11, h / 2)), mat,
                     location=(x, SLICE_Y, LAND_Z))
            pair.append(o)
        halves.append(pair)
    return halves


def build_vehicles(rng):
    """Red double-deckers and black cabs on Westminster Bridge."""
    red = M.principled("BusRed", color=(0.75, 0.04, 0.04), roughness=0.35, coat=0.5)
    black = M.principled("CabBlack", color=(0.02, 0.02, 0.025), roughness=0.3, coat=0.8)
    win = M.principled("VehicleGlass", color=(0.05, 0.07, 0.1), roughness=0.1, emission=(1.0, 0.85, 0.5),
                       emission_strength=0.8)
    out = []
    lane_y = [-110, -70, -30, 15, 55, 95, -90, -10, 35, 75]
    for i, y in enumerate(lane_y):
        bus = i < 6
        lx = BRIDGE_X + (-5.5 if i % 2 else 5.5)
        if bus:
            bm = box_bmesh(2.6, 11, 4.3, center=(0, 0, 2.15 + 0.4))
            wb = box_bmesh(2.7, 10.2, 0.9, center=(0, 0, 3.4))
            box_bmesh(2.7, 10.2, 0.8, center=(0, 0, 1.8), bm=wb)
            body_mat = red
        else:
            bm = box_bmesh(1.8, 4.6, 1.5, center=(0, 0, 1.0))
            wb = box_bmesh(1.85, 2.4, 0.6, center=(0, -0.2, 1.75))
            body_mat = black
        body = _obj("Bus" if bus else "Cab", bm, body_mat, location=(lx, y, LAND_Z + 7.0))
        glass = _obj("VehicleWindows", wb, win)
        glass.parent = body                 # sits at the body's origin
        out.append(body)
    return out
