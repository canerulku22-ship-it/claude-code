"""The "break lab" studio shared by every episode, plus render settings.

Signature look: a dark indigo cyclorama, a slate floor with a faint measurement grid,
and a round grey test pad with a yellow/black hazard rim. Warm key, cool rim and a soft
pool of light on the wall behind the subject. Lights scale with the subject's size, so
an egg and a table are both lit the same way.
"""

import math

import bmesh
import bpy
from mathutils import Vector

from . import materials as M
from .util import cylinder_bmesh, link, mesh_from_bmesh, new_object

PAD_HEIGHT = 0.04


def eevee_engine_id():
    items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if name in items:
            return name
    raise RuntimeError("Eevee is not available in this Blender build")


def setup_render(scene, width, height, samples, motion_blur=False):
    scene.render.engine = eevee_engine_id()
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 15
    ee = scene.eevee
    ee.taa_render_samples = samples
    # Tuned for speed on CPU-only machines: one shadow-casting light, no ray tracing.
    for attr, value in (("use_shadows", True), ("shadow_ray_count", 1), ("shadow_step_count", 3),
                        ("use_raytracing", False), ("use_fast_gi", False), ("use_gtao", True),
                        ("use_soft_shadows", True)):
        if hasattr(ee, attr):
            setattr(ee, attr, value)
    scene.render.use_motion_blur = bool(motion_blur)
    # AgX with a punchy look gives the slightly stylised, saturated finish.
    vs = scene.view_settings
    try:
        vs.view_transform = "AgX"
        for look in ("AgX - Punchy", "Punchy", "AgX - Medium High Contrast", "Medium High Contrast"):
            try:
                vs.look = look
                break
            except TypeError:
                continue
    except TypeError:
        vs.view_transform = "Filmic"
    vs.exposure = 0.0


def setup_world(scene):
    world = bpy.data.worlds.new("LabWorld")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.035, 0.04, 0.07, 1.0)
    bg.inputs["Strength"].default_value = 1.0


def build_cyclorama(size):
    """Floor that curves up into a back wall, so the camera never sees an edge."""
    depth = 6.0 * size
    radius = 1.6 * size
    height = 6.0 * size
    width = 30.0 * size
    back = 2.2 * size
    profile = []
    for i in range(9):
        profile.append((-depth + i * (depth + back) / 8.0, 0.0))   # floor, front to back
    for i in range(1, 13):                                         # quarter-circle cove
        a = (i / 12.0) * (math.pi / 2)
        profile.append((back + radius * math.sin(a), radius * (1 - math.cos(a))))
    profile.append((back + radius, height))
    bm = bmesh.new()
    rows = []
    for x in (-width / 2, width / 2):
        rows.append([bm.verts.new((x, y, z)) for (y, z) in profile])
    for k in range(len(profile) - 1):
        bm.faces.new((rows[0][k], rows[1][k], rows[1][k + 1], rows[0][k + 1]))
    me = mesh_from_bmesh("Cyclorama", bm, smooth=True)
    obj = new_object("Cyclorama", me)
    # Split materials: floor faces get the grid, the cove and wall get the gradient.
    me.materials.append(M.floor())
    me.materials.append(M.backdrop())
    for poly in me.polygons:
        poly.material_index = 0 if poly.center.z < 0.01 * size and poly.center.y < back else 1
    return obj


def build_pad(radius):
    """Round test pad: grey top, hazard-striped rim. Returns the pad object."""
    bm = cylinder_bmesh(radius, PAD_HEIGHT, segments=96, center=(0, 0, PAD_HEIGHT / 2))
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.verts[0].co.z > PAD_HEIGHT * 0.9
                              and e.verts[1].co.z > PAD_HEIGHT * 0.9],
                    offset=0.006, segments=2, affect="EDGES")
    me = mesh_from_bmesh("TestPad", bm)
    obj = new_object("TestPad", me)
    me.materials.append(M.pad_top())
    me.materials.append(M.hazard())
    for poly in me.polygons:
        poly.material_index = 0 if poly.normal.z > 0.5 else 1
    for poly in me.polygons:
        poly.use_smooth = abs(poly.normal.z) < 0.5
    return obj


def _area_light(name, location, target, size, power, color):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "DISK"
    data.size = size
    data.energy = power
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    link(obj)
    _aim(obj, target)
    return obj


def _aim(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_lights(center, size):
    """Key, rim, fill and a backdrop pool, scaled to a subject of ``size`` metres."""
    c = Vector(center)
    s = max(size, 0.25)
    lights = []

    def place(az_deg, el_deg, dist):
        az, el = math.radians(az_deg), math.radians(el_deg)
        return c + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist

    d_key, d_rim, d_fill = 3.2 * s, 3.0 * s, 3.6 * s
    lights.append(_area_light("Key", place(-55, 64, d_key), c, 1.6 * s, 260 * (d_key / 3.2) ** 2,
                              (1.0, 0.93, 0.84)))
    # The rim sits high: lower down, it mirrors in glass and glazes the floor.
    lights.append(_area_light("Rim", place(150, 56, d_rim), c, 0.7 * s, 380 * (d_rim / 3.0) ** 2,
                              (0.55, 0.80, 1.0)))
    lights.append(_area_light("Fill", place(50, 14, d_fill), c, 3.5 * s, 70 * (d_fill / 3.6) ** 2,
                              (0.80, 0.85, 1.0)))
    # Only the key casts shadows: each extra shadowed light costs a lot on CPU renders.
    # The big low fill would show up as a white blob in glass, so it gives no reflections.
    for L in lights:
        L.data.use_shadow = L.name == "Key"
        if L.name == "Fill" and hasattr(L.data, "specular_factor"):
            L.data.specular_factor = 0.0
    # Pool of light on the wall behind the subject.
    spot = bpy.data.lights.new("WallPool", "SPOT")
    spot.use_shadow = False
    spot.energy = 700 * s ** 2
    spot.spot_size = math.radians(55)
    spot.spot_blend = 1.0
    spot.color = (0.55, 0.45, 1.0)
    spot.shadow_soft_size = 0.5 * s
    obj = bpy.data.objects.new("WallPool", spot)
    obj.location = c + Vector((0.0, -1.0 * s, 2.2 * s))
    link(obj)
    _aim(obj, c + Vector((0.0, 3.4 * s, 0.6 * s)))
    lights.append(obj)
    return lights


def no_transparent_shadows():
    """Stop see-through objects (glass, acrylic, egg white) from casting shadows."""
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for mat in obj.data.materials:
            method = getattr(mat, "surface_render_method", None) or getattr(mat, "blend_method", "")
            if mat is not None and method in ("BLENDED", "BLEND"):
                obj.visible_shadow = False
                break
