"""Builds the static parts of the scene once; animate.py drives them per frame.

Scale trick: the story spans 0.1 mm to ~440,000 km, far beyond what 32-bit
floats can hold in one scene. So the camera never moves away. Instead every
frame the whole world is scaled about the foot of the stack so the view is
always K units tall (scaling about that point is exactly equivalent to a
camera pull-back). Visible objects therefore always have sane coordinates.
"""

import math

import bmesh
import bpy

from .. import style
from ..mathutil import hex_to_linear
from .util import (Nodes, assign, mesh_from_bmesh, mesh_from_data, new_object,
                   principled_material, safe_set, set_blend_mode, set_input)

K = 10.0                     # view height in scene units, at the subject
FLAP_SEGMENTS = 32           # resolution of the bending flap


class SceneRefs:
    """Handles to everything animate.py changes each frame."""


def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.curves, bpy.data.worlds):
        for block in list(coll):
            coll.remove(block)


def configure_render(scene, width, height, fps, samples):
    engines = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.render.film_transparent = False
    safe_set(scene.render, "filter_size", 1.3)
    img = scene.render.image_settings
    img.file_format = "PNG"
    img.color_mode = "RGB"
    img.color_depth = "8"
    img.compression = 15

    ee = scene.eevee
    safe_set(ee, "taa_render_samples", samples)
    safe_set(ee, "use_gtao", True)
    safe_set(ee, "gtao_distance", 0.8)
    safe_set(ee, "gtao_factor", 1.2)
    safe_set(ee, "use_soft_shadows", True)
    safe_set(ee, "shadow_cascade_size", "2048")
    safe_set(ee, "shadow_cube_size", "1024")
    safe_set(ee, "use_shadow_high_bitdepth", True)
    safe_set(ee, "use_bloom", True)
    safe_set(ee, "bloom_threshold", 1.4)
    safe_set(ee, "bloom_intensity", 0.035)
    safe_set(ee, "bloom_radius", 5.0)
    safe_set(ee, "use_ssr", False)
    safe_set(ee, "use_motion_blur", False)
    safe_set(ee, "use_shadows", True)        # EEVEE Next
    safe_set(ee, "use_raytracing", False)    # EEVEE Next

    # Colour management. These enums are dynamic (their items can't be listed
    # in background mode), so just try the preferred values in order.
    vs = scene.view_settings
    for transform in style.VIEW_TRANSFORMS + ("Filmic",):
        if safe_set(vs, "view_transform", transform):
            break
    for look in style.VIEW_LOOKS:
        if safe_set(vs, "look", look):
            break
    vs.exposure = style.VIEW_EXPOSURE
    vs.gamma = 1.0


# --- World (sky gradient, stars) ---------------------------------------------

def build_world(refs):
    world = bpy.data.worlds.new("Sky")
    bpy.context.scene.world = world
    world.use_nodes = True
    nb = Nodes(world.node_tree)
    nb.clear()
    out = nb.new("ShaderNodeOutputWorld")
    coord = nb.new("ShaderNodeTexCoord")
    direction = coord.outputs["Generated"]
    z = nb.separate(direction)[2]

    zenith = nb.rgb((0.2, 0.4, 0.7, 1), "zenith")
    horizon = nb.rgb((0.7, 0.8, 0.9, 1), "horizon")
    grad = nb.map_range(z, -0.03, 0.62)
    grad = nb.math("POWER", grad, 0.75)
    sky = nb.mix(grad, horizon, zenith)

    # Stars: tiny bright cells from a Voronoi pattern on the view direction.
    vor = nb.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "3D"
    vor.inputs["Scale"].default_value = 260.0
    nb.link(direction, vor.inputs["Vector"])
    dot = nb.map_range(vor.outputs["Distance"], 0.07, 0.0)
    pick = nb.map_range(nb.separate(vor.outputs["Color"])[0], 0.80, 0.83)
    twinkle = nb.map_range(nb.separate(vor.outputs["Color"])[1], 0.0, 1.0, 0.35, 1.0, False)
    star_strength = nb.value(0.0, "stars")
    stars = nb.math("MULTIPLY", nb.math("MULTIPLY", dot, pick), twinkle)
    stars = nb.math("MULTIPLY", stars, star_strength)
    stars = nb.math("MULTIPLY", stars, nb.map_range(z, -0.05, 0.02))
    star_col = nb.mix(stars, (0, 0, 0, 1), (2.5, 2.5, 2.6, 1))
    add = nb.new("ShaderNodeMix")
    add.data_type = "RGBA"
    add.blend_type = "ADD"
    nb.feed(add.inputs[0], 1.0)
    nb.link(sky, add.inputs[6])
    nb.link(star_col, add.inputs[7])
    visible = add.outputs[2]

    # Lighting uses a separate ambient colour so space can stay pitch black
    # on screen while objects still get a little fill.
    ambient = nb.rgb((0.5, 0.6, 0.7, 1), "ambient")
    lp = nb.new("ShaderNodeLightPath")
    colour = nb.mix(lp.outputs["Is Camera Ray"], ambient, visible)
    bg = nb.new("ShaderNodeBackground")
    nb.link(colour, bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nb.link(bg.outputs[0], out.inputs["Surface"])

    refs.world_zenith = zenith.node
    refs.world_horizon = horizon.node
    refs.world_ambient = ambient.node
    refs.world_stars = star_strength.node


# --- Lights and camera ---------------------------------------------------------

def build_lights(refs):
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 3.6
    sun.color = hex_to_linear("#FFF4E2")
    safe_set(sun, "angle", math.radians(2.5))
    safe_set(sun, "use_contact_shadow", True)
    safe_set(sun, "contact_shadow_distance", 0.3)
    safe_set(sun, "contact_shadow_thickness", 0.05)
    safe_set(sun, "shadow_cascade_max_distance", 120.0)
    safe_set(sun, "shadow_cascade_count", 4)
    safe_set(sun, "shadow_cascade_exponent", 0.85)
    safe_set(sun, "shadow_buffer_bias", 0.2)
    sun_obj = new_object("Sun", sun)
    # Key light from the upper left, a little in front: shadows fall right/back,
    # away from the landmarks that stand on the left.
    sun_obj.rotation_euler = (math.radians(42), 0.0, math.radians(-62))

    fill = bpy.data.lights.new("Fill", "SUN")
    fill.energy = 0.35
    fill.color = hex_to_linear("#BFD4FF")
    safe_set(fill, "use_shadow", False)
    fill_obj = new_object("Fill", fill)
    fill_obj.rotation_euler = (math.radians(65), 0.0, math.radians(140))
    refs.sun, refs.fill, refs.sun_obj = sun, fill, sun_obj


def build_camera(refs):
    cam = bpy.data.cameras.new("Camera")
    cam.sensor_fit = "VERTICAL"
    cam.sensor_height = 24.0
    cam.lens = 12.0 / math.tan(math.radians(style.CAMERA_FOV_DEG / 2))
    cam.clip_start = 0.5
    cam.clip_end = 3.0e5
    obj = new_object("Camera", cam)
    bpy.context.scene.camera = obj
    refs.camera = obj
    refs.camera_distance = K / (2 * math.tan(math.radians(style.CAMERA_FOV_DEG / 2)))


# --- Ground (adaptive measuring grid) -----------------------------------------

def build_ground(refs):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, cap_tris=False, segments=96, radius=900.0)
    ground = new_object("Ground", mesh_from_bmesh("Ground", bm))

    mat, nb, bsdf = principled_material("GroundMat", "#2A4352", roughness=0.92, specular=0.15)
    geo = nb.new("ShaderNodeNewGeometry")
    x, y, _ = nb.separate(geo.outputs["Position"])
    r = nb.math("SQRT", nb.math("ADD", nb.math("MULTIPLY", x, x), nb.math("MULTIPLY", y, y)))

    def grid(spacing, width, strength):
        """Line intensity for a square grid with the given spacing (scene units)."""
        def axis(c):
            f = nb.math("FRACT", nb.math("ADD", nb.math("DIVIDE", c, spacing), 0.5))
            d = nb.math("MULTIPLY", nb.math("ABSOLUTE", nb.math("SUBTRACT", f, 0.5)), spacing)
            return nb.map_range(d, width, nb.math("MULTIPLY", width, 1.8), 1.0, 0.0)
        return nb.math("MULTIPLY", nb.math("MAXIMUM", axis(x), axis(y)), strength)

    s1 = nb.value(1.0, "grid_s1")
    w1 = nb.value(0.01, "grid_w1")
    a1 = nb.value(0.5, "grid_a1")
    s2 = nb.value(10.0, "grid_s2")
    w2 = nb.value(0.02, "grid_w2")
    a2 = nb.value(1.0, "grid_a2")
    strength = nb.value(1.0, "grid_strength")
    minor = nb.math("MULTIPLY", grid(s1, w1, a1), nb.map_range(r, 8.0, 30.0, 1.0, 0.0))
    lines = nb.math("MAXIMUM", minor, grid(s2, w2, a2))
    near = nb.map_range(r, 14.0, 70.0, 1.0, 0.0)
    lines = nb.math("MULTIPLY", nb.math("MULTIPLY", lines, near), strength)

    base = nb.rgb(hex_to_linear("#2A4352", 1.0), "ground")
    line_col = nb.rgb(hex_to_linear(style.GRID_LINE, 1.0), "grid_colour")
    horizon = nb.rgb((0.7, 0.8, 0.9, 1), "horizon")
    col = nb.mix(lines, base, line_col)
    set_input(bsdf, "Base Color", col)
    # Far away the ground turns into the sky's horizon colour (unlit), so the
    # horizon is seamless whatever the lighting.
    haze = nb.math("POWER", nb.map_range(r, 20.0, 560.0, 0.0, 1.0, False), 0.6)
    emit = nb.new("ShaderNodeEmission")
    nb.link(horizon, emit.inputs["Color"])
    blend = nb.new("ShaderNodeMixShader")
    nb.link(haze, blend.inputs[0])
    nb.link(bsdf.outputs[0], blend.inputs[1])
    nb.link(emit.outputs[0], blend.inputs[2])
    out = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeOutputMaterial")
    nb.link(blend.outputs[0], out.inputs["Surface"])
    assign(ground, mat)

    refs.ground = ground
    refs.ground_nodes = {n.name: n for n in mat.node_tree.nodes}


# --- Earth -----------------------------------------------------------------------

def build_earth(refs):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=256, v_segments=256, radius=1.0)
    earth = new_object("Earth", mesh_from_bmesh("Earth", bm, smooth=True))

    mat, nb, bsdf = principled_material("EarthMat", style.EARTH_LAND, roughness=0.8, specular=0.3)
    coord = nb.new("ShaderNodeTexCoord")
    obj = coord.outputs["Object"]
    noise = nb.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.6
    noise.inputs["Detail"].default_value = 7.0
    noise.inputs["Roughness"].default_value = 0.55
    nb.link(obj, noise.inputs["Vector"])
    z = nb.separate(obj)[2]
    # Keep solid land around the north pole, where the stack stands.
    landness = nb.math("ADD", noise.outputs["Fac"], nb.map_range(z, 0.93, 0.995, 0.0, 0.5))
    land = nb.map_range(landness, 0.52, 0.535)
    dry_noise = nb.new("ShaderNodeTexNoise")
    dry_noise.inputs["Scale"].default_value = 3.0
    nb.link(obj, dry_noise.inputs["Vector"])
    dry = nb.math("MULTIPLY", nb.map_range(dry_noise.outputs["Fac"], 0.55, 0.65),
                  nb.map_range(z, 0.9, 0.8))
    land_col = nb.mix(dry, hex_to_linear(style.EARTH_LAND, 1.0), hex_to_linear(style.EARTH_LAND_DRY, 1.0))
    col = nb.mix(land, hex_to_linear(style.EARTH_OCEAN, 1.0), land_col)
    set_input(bsdf, "Base Color", col)
    set_input(bsdf, "Roughness", nb.map_range(land, 0.0, 1.0, 0.35, 0.85, False))
    assign(earth, mat)

    # Cloud shell, faded in from orbit height.
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=128, v_segments=64, radius=1.012)
    clouds = new_object("Clouds", mesh_from_bmesh("Clouds", bm, smooth=True))
    cmat = bpy.data.materials.new("CloudMat")
    cmat.use_nodes = True
    cn = Nodes(cmat.node_tree)
    cn.clear()
    out = cn.new("ShaderNodeOutputMaterial")
    coord = cn.new("ShaderNodeTexCoord")
    cnoise = cn.new("ShaderNodeTexNoise")
    cnoise.inputs["Scale"].default_value = 4.0
    cnoise.inputs["Detail"].default_value = 6.0
    cn.link(coord.outputs["Object"], cnoise.inputs["Vector"])
    opacity = cn.value(0.0, "cloud_opacity")
    alpha = cn.math("MULTIPLY", cn.map_range(cnoise.outputs["Fac"], 0.55, 0.7), opacity)
    white = cn.new("ShaderNodeBsdfDiffuse")
    white.inputs["Color"].default_value = (1, 1, 1, 1)
    clear = cn.new("ShaderNodeBsdfTransparent")
    mix = cn.new("ShaderNodeMixShader")
    cn.link(alpha, mix.inputs[0])
    cn.link(clear.outputs[0], mix.inputs[1])
    cn.link(white.outputs[0], mix.inputs[2])
    cn.link(mix.outputs[0], out.inputs["Surface"])
    set_blend_mode(cmat, "BLEND")
    assign(clouds, cmat)

    # Thin atmosphere glow on the limb.
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=128, v_segments=64, radius=1.03)
    atmo = new_object("Atmosphere", mesh_from_bmesh("Atmosphere", bm, smooth=True))
    amat = bpy.data.materials.new("AtmoMat")
    amat.use_nodes = True
    an = Nodes(amat.node_tree)
    an.clear()
    out = an.new("ShaderNodeOutputMaterial")
    lw = an.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    glow = an.value(0.0, "atmo_strength")
    alpha = an.math("MULTIPLY", an.math("POWER", lw.outputs["Facing"], 2.5), glow)
    emit = an.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = hex_to_linear("#7FB8FF", 1.0)
    emit.inputs["Strength"].default_value = 1.6
    clear = an.new("ShaderNodeBsdfTransparent")
    mix = an.new("ShaderNodeMixShader")
    an.link(alpha, mix.inputs[0])
    an.link(clear.outputs[0], mix.inputs[1])
    an.link(emit.outputs[0], mix.inputs[2])
    an.link(mix.outputs[0], out.inputs["Surface"])
    set_blend_mode(amat, "BLEND")
    assign(atmo, amat)

    refs.earth, refs.clouds, refs.atmosphere = earth, clouds, atmo
    refs.cloud_opacity = opacity.node
    refs.atmo_strength = glow.node


# --- The stack -------------------------------------------------------------------

def build_stack_material(cfg, refs):
    """Paper material with layer lines and alternating 'fold bands'.

    The mesh UV's U coordinate holds the layer index (0 at the bottom,
    2^n at the top). The shader draws:
      - a fine line between layers (only when layers are big enough to see)
      - alternating shades for each doubling (layers 2^k..2^(k+1)), so the
        newest fold always shows as a band as tall as everything below it.
    """
    base_lin = hex_to_linear(cfg["colour"])
    mat, nb, bsdf = principled_material("StackMat", colour=base_lin,
                                        roughness=cfg["roughness"], specular=0.35)
    set_input(bsdf, ["Sheen Weight", "Sheen"], cfg.get("sheen", 0.0))

    uv = nb.new("ShaderNodeUVMap")
    uv.uv_map = "Layers"
    u = nb.separate(uv.outputs["UV"])[0]
    geo = nb.new("ShaderNodeNewGeometry")
    nz = nb.separate(geo.outputs["Normal"])[2]
    side = nb.map_range(nb.math("ABSOLUTE", nz), 0.75, 0.35)

    layer_strength = nb.value(0.0, "layer_strength")
    band_strength = nb.value(0.0, "band_strength")
    layer_px = nb.value(0.0, "layer_px")
    flash = nb.value(0.0, "flash")

    f = nb.math("FRACT", u)
    dist = nb.math("MINIMUM", f, nb.math("SUBTRACT", 1.0, f))
    line = nb.map_range(dist, 0.0, 0.2, 1.0, 0.0)
    layer_term = nb.math("MULTIPLY", nb.math("MULTIPLY", line, layer_strength), side)

    log2 = nb.math("LOGARITHM", nb.math("MAXIMUM", u, 1.0), 2.0)
    band = nb.math("MODULO", nb.math("FLOOR", log2), 2.0)
    band_px = nb.math("MULTIPLY", nb.math("MULTIPLY", u, layer_px), 0.5)
    band_fade = nb.map_range(band_px, 3.0, 12.0)
    band_term = nb.math("MULTIPLY", nb.math("MULTIPLY", band, band_strength),
                        nb.math("MULTIPLY", band_fade, side))

    base = nb.rgb(tuple(base_lin) + (1.0,), "base")
    darker = tuple(c * 0.70 for c in base_lin) + (1.0,)
    banded = tuple(c * 0.76 for c in base_lin) + (1.0,)
    col = nb.mix(layer_term, base, darker)
    col = nb.mix(band_term, col, banded)
    set_input(bsdf, "Base Color", col)
    set_input(bsdf, ["Emission Color", "Emission"], tuple(base_lin) + (1.0,))
    set_input(bsdf, "Emission Strength", flash)

    refs.stack_mat = mat
    refs.stack_nodes = {n.name: n for n in mat.node_tree.nodes}
    return mat


def _box_mesh(name):
    """Unit box, origin at bottom centre, with a 'Layers' UV map."""
    verts = [(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0),
             (-0.5, -0.5, 1), (0.5, -0.5, 1), (0.5, 0.5, 1), (-0.5, 0.5, 1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh = mesh_from_data(name, verts, faces)
    mesh.uv_layers.new(name="Layers")
    return mesh


def _slab_mesh(name, segments):
    """Strip of `segments` boxes along +x; vertex coordinates are set per frame.

    Vertex index for (i along length, j across width, k through thickness):
        idx = (i * 2 + j) * 2 + k
    """
    verts = [(i, j, k) for i in range(segments + 1) for j in (0, 1) for k in (0, 1)]

    def v(i, j, k):
        return (i * 2 + j) * 2 + k

    faces = []
    for i in range(segments):
        faces.append((v(i, 0, 1), v(i + 1, 0, 1), v(i + 1, 1, 1), v(i, 1, 1)))  # k=1 face
        faces.append((v(i, 0, 0), v(i, 1, 0), v(i + 1, 1, 0), v(i + 1, 0, 0)))  # k=0 face
        faces.append((v(i, 0, 0), v(i + 1, 0, 0), v(i + 1, 0, 1), v(i, 0, 1)))  # j=0 side
        faces.append((v(i, 1, 0), v(i, 1, 1), v(i + 1, 1, 1), v(i + 1, 1, 0)))  # j=1 side
    faces.append((v(0, 0, 0), v(0, 0, 1), v(0, 1, 1), v(0, 1, 0)))              # hinge end
    s = segments
    faces.append((v(s, 0, 0), v(s, 1, 0), v(s, 1, 1), v(s, 0, 1)))              # far end
    mesh = mesh_from_data(name, verts, faces)
    mesh.uv_layers.new(name="Layers")
    return mesh


def build_stack(cfg, refs):
    mat = build_stack_material(cfg, refs)
    stack = new_object("Stack", _box_mesh("Stack"))
    flap = new_object("Flap", _slab_mesh("Flap", FLAP_SEGMENTS))
    assign(stack, mat)
    assign(flap, mat)
    def loop_vertices(obj):
        """Vertex index of each face corner (UVs are stored per corner)."""
        loops = [0] * len(obj.data.loops)
        obj.data.loops.foreach_get("vertex_index", loops)
        return loops

    refs.stack, refs.flap = stack, flap
    refs.stack_loops = loop_vertices(stack)
    refs.flap_loops = loop_vertices(flap)


def build(cfg, timeline, width, height, samples):
    reset_scene()
    scene = bpy.context.scene
    configure_render(scene, width, height, timeline.fps, samples)
    refs = SceneRefs()
    refs.width, refs.height = width, height
    build_world(refs)
    build_lights(refs)
    build_camera(refs)
    build_ground(refs)
    build_earth(refs)
    build_stack(cfg, refs)
    from .models import build_landmarks
    refs.landmarks = build_landmarks(timeline)
    return refs
