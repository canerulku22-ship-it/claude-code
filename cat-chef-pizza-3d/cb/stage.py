"""Scene, camera and studio lighting setup."""
import bpy
from mathutils import Vector

import config as C


def new_scene(name, nframes, world, samples=None):
    sc = bpy.data.scenes.new(name)
    sc.frame_start, sc.frame_end = 1, nframes
    r = sc.render
    r.engine = "CYCLES"
    r.fps = C.FPS
    r.resolution_x, r.resolution_y = C.RES_X, C.RES_Y
    r.resolution_percentage = int(round(C.RENDER_SCALE * 100))
    r.film_transparent = False
    r.use_persistent_data = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_depth = "16"
    r.image_settings.compression = 30
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples or C.SAMPLES
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.05
    cy.use_denoising = True
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.denoising_quality = "BALANCED"
    cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cy.max_bounces = 4
    cy.diffuse_bounces = 1
    cy.glossy_bounces = 2
    cy.transmission_bounces = 4
    # Steam is many overlapping camera-facing transparent sprites. With a low
    # limit, rays that pass through more than that many quads are terminated
    # and render as hard-edged black blocks (seen top-down over the fry pot).
    cy.transparent_max_bounces = 64
    cy.use_fast_gi = True
    cy.fast_gi_method = "REPLACE"
    cy.volume_bounces = 0
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.sample_clamp_indirect = 4.0
    cy.blur_glossy = 1.0
    # Khronos PBR Neutral keeps food colours true (AgX shifts saturated
    # yellows/oranges such as cheese, egg and fried crust towards salmon).
    sc.view_settings.view_transform = C.VIEW_TRANSFORM
    sc.view_settings.look = "None"
    sc.view_settings.exposure = C.EXPOSURE
    sc.world = world
    world.light_settings.ao_factor = 1.0      # fast-GI approximation range
    world.light_settings.distance = 1.5
    return sc


def camera(sc, name, lens=50.0, fstop=2.8):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 36.0
    cd.sensor_width = 36.0
    cd.clip_start = 0.05
    cd.clip_end = 500.0
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_blades = 7
    cd.dof.aperture_rotation = 0.3
    o = bpy.data.objects.new(name, cd)
    sc.collection.objects.link(o)
    o.rotation_mode = "QUATERNION"
    sc.camera = o
    return o


def area(sc, name, loc, target, energy, size=(2.0, 2.0), color=(1, 1, 1), spread=None, coll=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = size
    ld.energy = energy
    ld.color = color
    if spread is not None:
        ld.spread = spread
    o = bpy.data.objects.new(name, ld)
    (coll or sc.collection).objects.link(o)
    o.location = loc
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    return o


def studio_rig(sc, target=(0, 0, 0.4), k=1.0, key_side=-1, rim=1.0, top=1.0, prefix="L"):
    """Food-commercial rig: big soft warm key, cool fill, two hard-ish rim
    strips behind the subject for crispy edge highlights, soft top light."""
    t = Vector(target)
    L = {}
    L["key"] = area(sc, f"{prefix}_key", t + Vector((2.8 * key_side, -3.2, 2.6)), t, 800 * k,
                    (2.6, 2.6), (1.0, 0.93, 0.85))
    L["fill"] = area(sc, f"{prefix}_fill", t + Vector((-3.0 * key_side, -3.0, 0.6)), t, 110 * k,
                     (3.0, 3.0), (0.78, 0.86, 1.0))
    L["rimL"] = area(sc, f"{prefix}_rimL", t + Vector((-2.4, 2.6, 1.2)), t, 900 * k * rim,
                     (0.35, 3.0), (1.0, 0.74, 0.50), spread=0.9)
    L["rimR"] = area(sc, f"{prefix}_rimR", t + Vector((2.4, 2.6, 1.6)), t, 800 * k * rim,
                     (0.35, 3.0), (0.95, 0.92, 0.88), spread=0.9)
    L["top"] = area(sc, f"{prefix}_top", t + Vector((0.0, 0.6, 3.6)), t, 200 * k * top,
                    (2.0, 2.0), (1.0, 0.93, 0.85))
    return L


def collection(sc, name):
    c = bpy.data.collections.new(f"{sc.name}_{name}")
    sc.collection.children.link(c)
    return c
