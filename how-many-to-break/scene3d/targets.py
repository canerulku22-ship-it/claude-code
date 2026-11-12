"""Procedural targets.

Each builder models the target standing on the test pad and returns a ``Target`` that
tells the rest of the pipeline how it behaves:

* ``support``       where the pile stacks (see hmtb/stacking.py)
* ``crack_parts``   surfaces that get growing cracks: (object, style, origin_uv)
* ``breakables``    what shatters at the break (Voronoi pieces) and what's inside
* ``passive_after`` parts that stay put after the break (legs, frames)
* ``dynamic_after`` parts that fall in one piece (a load plate, a chair back)
* ``visual_only``   parts that never collide (guide rods)
* ``sag_shape``     objects with a "Sag" shape key (value = metres at the centre)
* ``sag_move``      objects that sink rigidly with the load (a glass top, a seat)

To add a target: write ``def build_<key>(rng):`` returning a Target, then add ``<key>``
to the catalogue in hmtb/catalog.py.
"""

import math
from dataclasses import dataclass, field

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import materials as M
from .cracks import set_crack_uv
from .fracture import box_seeds, radial_seeds
from .studio import PAD_HEIGHT
from .util import apply_modifiers, box_bmesh, cylinder_bmesh, join_meshes, mesh_from_bmesh, new_object


@dataclass
class Breakable:
    obj: object
    seeds: list
    interior_index: int
    density: float
    metric: tuple = (1.0, 1.0, 1.0)
    uv_func: object = None
    sag_radius: float = 0.0       # fracture the sagged shape (trampoline mat)


@dataclass
class Target:
    key: str
    support: dict
    focus: Vector
    pad_radius: float
    sag_radius: float = 0.0
    crack_parts: list = field(default_factory=list)
    breakables: list = field(default_factory=list)
    passive_after: list = field(default_factory=list)
    dynamic_after: list = field(default_factory=list)
    visual_only: list = field(default_factory=list)
    sag_shape: list = field(default_factory=list)
    sag_move: list = field(default_factory=list)
    sag_squash: list = field(default_factory=list)   # (object, height): squashes under the load
    frame_objects: list = field(default_factory=list)
    extras: list = field(default_factory=list)   # (object, "grow_after_break")
    jolt_m: float = 0.002
    tight_box: tuple = None   # (lo, hi) the camera pushes in on; None = support + pile
    close_box: tuple = None   # (lo, hi) for the crack-stage close-ups; None = crack surfaces
    close_yaw: float = 34.0   # close-up camera angle (degrees from the front)
    crack_width: float = 1.0  # multiplier for crack line width (small targets need more)


def _obj(name, bm, mats, location=(0, 0, 0), smooth=False):
    me = mesh_from_bmesh(name, bm, smooth=smooth)
    for m in mats:
        me.materials.append(m)
    return new_object(name, me, location=location)


def _cracked_copy(mat, name):
    """Materials with cracks are per-target copies, so the cracks don't leak elsewhere."""
    c = mat.copy()
    c.name = name
    return c


def ring_bmesh(r_in, r_out, z0, z1, segments=96, bm=None):
    """Flat ring (annulus) with a rectangular cross-section."""
    bm = bm or bmesh.new()
    loops = []
    for k in range(segments):
        a = 2 * math.pi * k / segments
        c, s = math.cos(a), math.sin(a)
        loops.append([bm.verts.new((r * c, r * s, z)) for (r, z) in
                      ((r_in, z0), (r_out, z0), (r_out, z1), (r_in, z1))])
    for k in range(segments):
        a, b = loops[k], loops[(k + 1) % segments]
        for q in range(4):
            bm.faces.new((a[q], b[q], b[(q + 1) % 4], a[(q + 1) % 4]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm


# ---------------------------------------------------------------------------
# Glass table
# ---------------------------------------------------------------------------

def build_glass_table(rng):
    size, thick, height = 1.1, 0.012, 0.45
    z_top = PAD_HEIGHT + height

    bm = box_bmesh(size, size, thick)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.0025, segments=1, affect="EDGES")
    glass = _obj("GlassTop", bm, [_cracked_copy(M.glass(), "GlassCracked"), M.glass_edge()],
                 location=(0, 0, z_top - thick / 2))
    for p in glass.data.polygons:
        p.material_index = 0 if abs(p.normal.z) > 0.5 else 1

    def uv(c):
        return c.x / size + 0.5, c.y / size + 0.5
    set_crack_uv(glass.data, uv)

    # Black steel frame: four legs and an apron the glass rests on.
    inset, leg = 0.07, 0.035
    fb = bmesh.new()
    leg_h = height - thick
    for sx in (-1, 1):
        for sy in (-1, 1):
            box_bmesh(leg, leg, leg_h, center=(sx * (size / 2 - inset), sy * (size / 2 - inset),
                                               PAD_HEIGHT + leg_h / 2), bm=fb)
    rail_z = z_top - thick - 0.02
    span = size - 2 * inset + leg
    for s in (-1, 1):
        box_bmesh(span, 0.025, 0.04, center=(0, s * (size / 2 - inset), rail_z), bm=fb)
        box_bmesh(0.025, span, 0.04, center=(s * (size / 2 - inset), 0, rail_z), bm=fb)
    frame = _obj("TableFrame", fb, [M.black_metal()])

    origin = (0.5 + rng.uniform(-0.05, 0.05), 0.5 + rng.uniform(-0.05, 0.05))
    seeds = radial_seeds(rng, 64, ((origin[0] - 0.5) * size, (origin[1] - 0.5) * size), 0.80, bias=1.8)
    return Target(
        key="glass_table",
        support={"shape": "rect", "cx": 0.0, "cy": 0.0, "z": z_top, "sx": size, "sy": size},
        focus=Vector((0, 0, z_top)),
        pad_radius=size * 0.9,
        crack_parts=[(glass, "glass", origin)],
        breakables=[Breakable(glass, seeds, 1, 2500.0, uv_func=uv)],
        passive_after=[frame],
        sag_move=[glass],
        frame_objects=[glass, frame],
        jolt_m=0.0015,
    )


# ---------------------------------------------------------------------------
# Trampoline (a round 1.4 m kids' trampoline)
# ---------------------------------------------------------------------------

def build_trampoline(rng):
    r_mat, leg_h = 0.75, 0.30
    z_frame = PAD_HEIGHT + leg_h
    z_mat = z_frame + 0.012

    # Mat: a square grid squeezed into a disc, then given thickness.
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=56, y_segments=56, size=1.0)
    ext = max(abs(v.co.x) for v in bm.verts)
    for v in bm.verts:
        x, y = v.co.x / ext, v.co.y / ext
        v.co.x = x * math.sqrt(max(0.0, 1 - y * y / 2)) * r_mat
        v.co.y = y * math.sqrt(max(0.0, 1 - x * x / 2)) * r_mat
        v.co.z = 0.0
    res = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    bmesh.ops.translate(bm, vec=(0, 0, -0.008), verts=[g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    mat_obj = _obj("JumpMat", bm, [_cracked_copy(M.trampoline_mat(), "JumpMatTorn"), M.trampoline_mat()],
                   location=(0, 0, z_mat))
    for p in mat_obj.data.polygons:
        p.material_index = 0 if p.normal.z > 0.5 else 1

    def uv(c):
        return c.x / (2 * r_mat) + 0.5, c.y / (2 * r_mat) + 0.5
    set_crack_uv(mat_obj.data, uv)
    # "Sag" shape key: value 1 = the centre sinks 1 m, the rim stays put.
    mat_obj.shape_key_add(name="Basis")
    sag = mat_obj.shape_key_add(name="Sag")
    sag.slider_min, sag.slider_max = 0.0, 1.0
    for i, v in enumerate(mat_obj.data.vertices):
        r = math.hypot(v.co.x, v.co.y)
        sag.data[i].co = v.co + Vector((0, 0, -max(0.0, 1.0 - (r / r_mat) ** 2)))

    # Padded safety ring over the springs and frame.
    pad = _obj("SafetyPad", ring_bmesh(r_mat - 0.03, r_mat + 0.19, z_frame, z_frame + 0.038),
               [M.plastic("PadBlue", (0.02, 0.22, 0.85), roughness=0.45)])
    bevel = pad.modifiers.new("soft", "BEVEL")
    bevel.width = 0.012
    bevel.segments = 3
    lb = bmesh.new()
    for k in range(6):
        a = 2 * math.pi * k / 6 + math.pi / 6
        cylinder_bmesh(0.02, leg_h, segments=16,
                       center=(0.85 * math.cos(a), 0.85 * math.sin(a), PAD_HEIGHT + leg_h / 2), bm=lb)
    ring = ring_bmesh(r_mat + 0.02, r_mat + 0.12, z_frame - 0.03, z_frame, segments=72)
    tmp_me = bpy.data.meshes.new("tmp")
    ring.to_mesh(tmp_me)
    ring.free()
    lb.from_mesh(tmp_me)
    bpy.data.meshes.remove(tmp_me)
    legs = _obj("TrampolineFrame", lb, [M.black_metal()])

    origin = (0.5 + rng.uniform(-0.04, 0.04), 0.5 + rng.uniform(-0.04, 0.04))
    seeds = radial_seeds(rng, 24, (0.0, 0.0), r_mat * 1.05, z=-0.004, bias=1.2)
    return Target(
        key="trampoline",
        # Object centres stay ~17 cm inside the padded rim, so nothing rests on (or in) it.
        support={"shape": "circle", "cx": 0.0, "cy": 0.0, "z": z_mat, "r": r_mat - 0.20},
        focus=Vector((0, 0, z_mat)),
        pad_radius=1.15,
        sag_radius=r_mat,
        crack_parts=[(mat_obj, "fabric", origin)],
        breakables=[Breakable(mat_obj, seeds, 1, 900.0, uv_func=uv, sag_radius=r_mat)],
        passive_after=[pad, legs],
        sag_shape=[mat_obj],
        frame_objects=[pad, legs],
        jolt_m=0.03,
    )


# ---------------------------------------------------------------------------
# Egg (in a little test rig with a clear load plate)
# ---------------------------------------------------------------------------

def _egg_bmesh(height=0.06, width=0.045):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=1.0)
    for v in bm.verts:
        z = v.co.z
        k = 1.0 - 0.14 * z            # narrower at the top
        v.co.x *= k * width / 2
        v.co.y *= k * width / 2
        v.co.z = z * height / 2
    return bm


def build_egg(rng):
    base_t, base_s, rod = 0.02, 0.36, 0.13
    z_base = PAD_HEIGHT + base_t
    egg_h, egg_w = 0.096, 0.072    # 1.6x life size: a real egg is lost under the load plate
    z_egg = z_base + 0.004 + egg_h / 2

    base = _obj("RigBase", box_bmesh(base_s, base_s, base_t, center=(0, 0, PAD_HEIGHT + base_t / 2)),
                [M.black_metal()])
    rb = bmesh.new()
    rod_h = 0.50
    for sx in (-1, 1):
        for sy in (-1, 1):
            cylinder_bmesh(0.0055, rod_h, segments=16, center=(sx * rod, sy * rod, z_base + rod_h / 2), bm=rb)
    rods = _obj("GuideRods", rb, [M.chrome()])
    cup = _obj("EggCup", ring_bmesh(0.019, 0.028, z_base, z_base + 0.008, segments=48), [M.chrome()])

    egg = _obj("Egg", _egg_bmesh(egg_h, egg_w), [_cracked_copy(M.eggshell(), "EggShellCracked"), M.yolk()],
               location=(0, 0, z_egg), smooth=True)

    def uv(c):
        return c.x / egg_h + 0.5, c.z / egg_h + 0.5
    set_crack_uv(egg.data, uv)

    plate_s, plate_t = 0.30, 0.01
    z_plate = z_egg + egg_h / 2 + plate_t / 2
    acrylic = M.principled("Acrylic", color=(0.55, 0.80, 1.0), roughness=0.03, specular=0.8,
                           coat=1.0, alpha=0.12)
    M.set_blended(acrylic)
    pb = box_bmesh(plate_s, plate_s, plate_t)
    bmesh.ops.bevel(pb, geom=list(pb.edges), offset=0.002, segments=1, affect="EDGES")
    plate = _obj("LoadPlate", pb, [acrylic], location=(0, 0, z_plate))

    # Yolk splat that spreads on the base after the break.
    splat_b = cylinder_bmesh(0.11, 0.003, segments=48, center=(0, 0, 0))
    splat = _obj("EggWhiteSplat", splat_b, [M.egg_white()], location=(0.01, -0.005, z_base + 0.0016))
    yb = bmesh.new()
    bmesh.ops.create_uvsphere(yb, u_segments=32, v_segments=16, radius=1.0)
    bmesh.ops.scale(yb, vec=(0.03, 0.03, 0.009), verts=yb.verts)
    yolk = _obj("YolkSplat", yb, [M.yolk()], location=(0.012, -0.004, z_base + 0.004), smooth=True)

    seeds = box_seeds(rng, 16, (-0.03, -0.03, -0.03), (0.03, 0.03, 0.045))
    return Target(
        key="egg",
        support={"shape": "rect", "cx": 0.0, "cy": 0.0, "z": z_plate + plate_t / 2, "sx": plate_s, "sy": plate_s},
        focus=Vector((0, 0, z_egg)),
        pad_radius=0.36,
        crack_parts=[(egg, "shell", (0.5, 0.97))],
        crack_width=2.6,     # the egg is small: thicker lines in texture space
        breakables=[Breakable(egg, seeds, 1, 1030.0, uv_func=uv)],
        passive_after=[base, cup],
        dynamic_after=[plate],
        visual_only=[rods],
        sag_move=[plate],
        sag_squash=[(egg, egg_h)],
        frame_objects=[base, rods, egg],
        extras=[(splat, "grow_after_break"), (yolk, "grow_after_break")],
        jolt_m=0.0018,
        close_box=([-0.09, -0.09, z_base - 0.005], [0.09, 0.09, z_plate + 0.07]),
        close_yaw=12.0,      # between the front guide rods
        tight_box=([-0.17, -0.17, z_base], [0.17, 0.17, z_plate + 0.16]),
    )


# ---------------------------------------------------------------------------
# Wooden chair
# ---------------------------------------------------------------------------

def build_wooden_chair(rng):
    seat_w, seat_d, seat_t, seat_h = 0.44, 0.42, 0.035, 0.46
    z0 = PAD_HEIGHT
    z_seat = z0 + seat_h - seat_t / 2
    wood = M.wood("ChairWood")
    leg, lx, ly = 0.036, 0.18, 0.17
    # The seat stops at the front face of the rear legs so no two parts overlap; overlapping
    # rigid bodies fly apart violently when physics starts.
    seat_back = ly - leg / 2 - 0.001
    seat_d = seat_back + 0.21
    seat = _obj("Seat", box_bmesh(seat_w, seat_d, seat_t),
                [_cracked_copy(M.wood("SeatWood"), "SeatWoodCracked"), M.raw_wood()],
                location=(0, seat_back - seat_d / 2, z_seat))
    bevel = seat.modifiers.new("bevel", "BEVEL")
    bevel.width = 0.004
    apply_modifiers(seat)
    for p in seat.data.polygons:
        p.material_index = 0

    def uv(c):
        return c.x / seat_w + 0.5, c.y / seat_w + 0.5
    set_crack_uv(seat.data, uv)

    leg_h = seat_h - seat_t
    front_legs = []
    for sx in (-1, 1):
        o = _obj("FrontLeg", box_bmesh(leg, leg, leg_h), [wood, M.raw_wood()],
                 location=(sx * lx, -ly, z0 + leg_h / 2))
        front_legs.append(o)
    back_parts = []
    back_h = 0.95
    for sx in (-1, 1):
        back_parts.append(_obj("RearLeg", box_bmesh(leg, leg, back_h, center=(sx * lx, ly, z0 + back_h / 2)), [wood]))
    for z, h in ((0.62, 0.05), (0.74, 0.05), (0.88, 0.075)):
        back_parts.append(_obj("Slat", box_bmesh(2 * lx, 0.02, h, center=(0, ly, z0 + z)), [wood]))
    back = join_meshes("ChairBack", back_parts)
    stretchers = []
    for sx in (-1, 1):   # side rails, ending at the legs' faces
        stretchers.append(_obj("Stretcher", box_bmesh(0.022, 2 * ly - leg - 0.002, 0.022), [wood],
                               location=(sx * lx, 0, z0 + 0.16)))
    stretchers.append(_obj("Stretcher", box_bmesh(2 * lx - leg - 0.002, 0.022, 0.022), [wood],
                           location=(0, -ly, z0 + 0.12)))

    breakables = [Breakable(seat, box_seeds(rng, 9, (-0.2, -0.17, -0.01), (0.2, 0.17, 0.01)), 1, 650.0,
                            metric=(0.3, 1.0, 1.0), uv_func=uv)]
    for fl in front_legs:
        cut = rng.uniform(-0.08, 0.08)
        seeds = [Vector((rng.uniform(-0.01, 0.01), rng.uniform(-0.01, 0.01), cut - 0.1)),
                 Vector((rng.uniform(-0.01, 0.01), rng.uniform(-0.01, 0.01), cut + 0.1))]
        breakables.append(Breakable(fl, seeds, 1, 650.0))

    origin = (0.5 + rng.uniform(-0.06, 0.06), 0.5 + rng.uniform(-0.04, 0.04))
    return Target(
        key="wooden_chair",
        support={"shape": "rect", "cx": 0.0, "cy": seat_back - seat_d / 2 - 0.01, "z": z0 + seat_h,
                 "sx": 0.42, "sy": seat_d - 0.06},
        focus=Vector((0, 0, z0 + seat_h)),
        pad_radius=0.55,
        crack_parts=[(seat, "wood", origin)],
        breakables=breakables,
        dynamic_after=[back] + stretchers,
        sag_move=[seat],
        frame_objects=[seat, back] + front_legs,
        jolt_m=0.003,
    )


BUILDERS = {
    "glass_table": build_glass_table,
    "trampoline": build_trampoline,
    "egg": build_egg,
    "wooden_chair": build_wooden_chair,
}


def build(key, rng):
    if key not in BUILDERS:
        raise KeyError("No builder for target %r in scene3d/targets.py" % key)
    return BUILDERS[key](rng)
