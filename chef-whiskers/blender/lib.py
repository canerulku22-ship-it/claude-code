"""Procedural Blender toolkit for the 3D chicken burger film: studio, materials, food, particles, labels.

Every object is built from code, and every shot animates by setting state from the time `t`
(seconds) before each frame is rendered, so any frame can be rendered on its own.
Works with Blender 4.2+ and the `bpy` Python module (tested with 5.2).
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector, noise

FPS = 30


# ---------------------------------------------------------------- maths and easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def seg(t, a, b):
    return clamp((t - a) / (b - a)) if b != a else float(t >= b)


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    return 1 - (1 - clamp(t)) ** 3


def ease_in(t):
    return clamp(t) ** 3


def ease_io(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def back_out(t, c=1.7):
    t = clamp(t)
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def wob(t, t0, f=26.0, decay=9.0):
    return 0.0 if t < t0 else math.exp(-(t - t0) * decay) * math.sin((t - t0) * f)


def vlerp(a, b, t):
    return Vector(a).lerp(Vector(b), t)


def arc(a, b, t, h):
    p = vlerp(a, b, t)
    p.z += math.sin(math.pi * clamp(t)) * h
    return p


def srgb(r, g, b, a=1.0):
    """Colour picker values (sRGB) to the linear values Blender's shaders use."""
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (f(r), f(g), f(b), a)


# ---------------------------------------------------------------- scene and render
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def setup_render(scene, scale=100, samples=24, preview=False):
    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = 1080, 1920
    r.resolution_percentage = 25 if preview else scale
    r.fps = FPS
    r.use_persistent_data = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    c = scene.cycles
    c.device = "CPU"
    c.samples = 6 if preview else samples
    c.denoiser = "OPENIMAGEDENOISE"
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.06
    c.use_denoising = True
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 5, 2, 2
    c.transmission_bounces, c.transparent_max_bounces, c.volume_bounces = 4, 8, 0
    c.caustics_reflective = c.caustics_refractive = False
    c.blur_glossy = 1.0
    c.use_light_tree = True
    vs = scene.view_settings
    vs.view_transform = "AgX"
    for look in ("AgX - Punchy", "AgX - Medium High Contrast", "None"):
        try:
            vs.look = look
            break
        except TypeError:
            continue
    vs.exposure = -0.3
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = srgb(0.08, 0.055, 0.04)
    bg.inputs["Strength"].default_value = 0.25
    scene.world = world


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def new_obj(name, mesh, mat=None, smooth_shade=True):
    obj = link(bpy.data.objects.new(name, mesh))
    if smooth_shade:
        for p in mesh.polygons:
            p.use_smooth = True
    if mat:
        mesh.materials.append(mat)
    return obj


def hide_render(obj):
    obj.hide_render = True
    obj.hide_viewport = True
    return obj


# ---------------------------------------------------------------- materials
def _mix_rgba(nt, fac, a, b):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    ins = [s for s in m.inputs if s.enabled]
    outs = [s for s in m.outputs if s.enabled]
    _set(nt, ins[0], fac)
    _set(nt, ins[1], a)
    _set(nt, ins[2], b)
    return outs[0]


def _set(nt, socket, value):
    if hasattr(value, "is_output"):
        nt.links.new(value, socket)
    else:
        socket.default_value = value


def principled(name, base=(0.8, 0.8, 0.8, 1), rough=0.5, coat=0.0, coat_rough=0.1, sss=0.0, sss_radius=(1.0, 0.5, 0.25), sss_scale=0.005,
               metal=0.0, trans=0.0, ior=1.45, emit=None, emit_strength=0.0, spec=0.5, sheen=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    vals = {"Roughness": rough, "Coat Weight": coat, "Coat Roughness": coat_rough, "Subsurface Weight": sss, "Subsurface Radius": sss_radius,
            "Subsurface Scale": sss_scale, "Metallic": metal, "Transmission Weight": trans, "IOR": ior, "Specular IOR Level": spec, "Sheen Weight": sheen}
    for k, v in vals.items():
        if k in b.inputs:
            b.inputs[k].default_value = v
    if hasattr(b, "subsurface_method"):
        b.subsurface_method = "BURLEY"
    _set(nt, b.inputs["Base Color"], base)
    if emit is not None:
        b.inputs["Emission Color"].default_value = emit
        b.inputs["Emission Strength"].default_value = emit_strength
    return m, nt, b


def tex_coord(nt, kind="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return tc.outputs[kind]


def noise_tex(nt, vec, scale, detail=6.0, rough=0.6, distortion=0.0):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    if "Distortion" in n.inputs:
        n.inputs["Distortion"].default_value = distortion
    nt.links.new(vec, n.inputs["Vector"])
    return n


def bump(nt, b, height, strength=0.1, distance=0.001):
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    bp.inputs["Distance"].default_value = distance
    nt.links.new(height, bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return bp


def ramp(nt, fac, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    els[0].position, els[0].color = stops[0]
    els[1].position, els[1].color = stops[-1]
    for pos, col in stops[1:-1]:
        e = els.new(pos)
        e.color = col
    nt.links.new(fac, r.inputs["Fac"])
    return r.outputs["Color"]


def value_node(nt, name, v=0.0):
    n = nt.nodes.new("ShaderNodeValue")
    n.name = name
    n.outputs[0].default_value = v
    return n


def set_value(mat, name, v):
    mat.node_tree.nodes[name].outputs[0].default_value = v


class Materials:
    """All shared materials, built once per shot."""

    def __init__(self):
        self.bun_top = self._bun_top()
        self.bun_side = self._bun_side()
        self.crumb = self._crumb()
        self.chicken = self._chicken("chicken")
        self.flake = self._flake()
        self.lettuce = self._lettuce()
        self.cheese = principled("cheese", srgb(0.98, 0.62, 0.08), rough=0.33, coat=0.3, sss=0.3, sss_radius=(1.0, 0.55, 0.2), sss_scale=0.004)[0]
        self.sauce = principled("sauce", srgb(0.96, 0.52, 0.27), rough=0.14, coat=0.9, coat_rough=0.05, sss=0.35, sss_scale=0.003)[0]
        self.milk = principled("buttermilk", srgb(0.97, 0.96, 0.91), rough=0.1, coat=0.6, sss=0.7, sss_radius=(1, 0.9, 0.8), sss_scale=0.01)[0]
        self.flour = self._flour()
        self.oil = principled("oil", srgb(0.45, 0.24, 0.04), rough=0.03, coat=0.8, coat_rough=0.02, ior=1.47, spec=0.8, emit=srgb(0.8, 0.42, 0.05), emit_strength=0.05)[0]
        self.bubble = principled("bubble", srgb(1.0, 0.93, 0.75), rough=0.05, coat=1.0, spec=0.8)[0]
        self.pot = principled("pot", srgb(0.06, 0.06, 0.065), rough=0.38, metal=0.5, coat=0.4)[0]
        self.ceramic = principled("ceramic", srgb(0.95, 0.94, 0.91), rough=0.12, coat=1.0)[0]
        self.ceramic_sage = principled("ceramic_sage", srgb(0.56, 0.68, 0.55), rough=0.14, coat=1.0)[0]
        self.ceramic_dark = principled("ceramic_dark", srgb(0.15, 0.13, 0.12), rough=0.2, coat=1.0)[0]
        self.slate = self._slate()
        self.backdrop = principled("backdrop", srgb(0.07, 0.05, 0.04), rough=0.85)[0]
        self.paprika = principled("paprika", srgb(0.78, 0.2, 0.06), rough=0.8)[0]
        self.pepper = principled("pepper", srgb(0.09, 0.07, 0.06), rough=0.7)[0]
        self.garlic = principled("garlic", srgb(0.93, 0.84, 0.62), rough=0.85)[0]
        self.salt = principled("salt", srgb(0.98, 0.98, 0.98), rough=0.25, trans=0.4)[0]
        self.label = principled("label", srgb(0.98, 0.47, 0.1), rough=0.35, coat=0.6)[0]
        self.label_dark = principled("label_dark", srgb(0.1, 0.07, 0.05), rough=0.4, coat=0.6)[0]
        self.text = principled("text", srgb(1, 1, 1), rough=0.3, emit=srgb(1, 1, 1), emit_strength=0.8)[0]
        self.gold = principled("gold", srgb(1.0, 0.8, 0.25), rough=0.3, metal=0.2, coat=0.5, emit=srgb(1.0, 0.76, 0.2), emit_strength=1.6)[0]
        self.dust = principled("dust", srgb(1, 0.8, 0.5), emit=srgb(1.0, 0.72, 0.4), emit_strength=6.0)[0]
        self.glow = self._glow()
        self.bottle = principled("bottle", srgb(0.88, 0.2, 0.12), rough=0.25, coat=0.8)[0]
        self.cap = principled("cap", srgb(0.97, 0.97, 0.95), rough=0.3)[0]
        self.thermo = principled("thermo", srgb(0.9, 0.9, 0.92), rough=0.2, metal=1.0)[0]

    def _bun_top(self):
        m, nt, b = principled("bun_top", rough=0.36, coat=0.65, coat_rough=0.1, sss=0.1, sss_scale=0.004)
        z = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tex_coord(nt, "Generated"), z.inputs[0])
        n = noise_tex(nt, tex_coord(nt, "Object"), 90.0, 8.0, 0.55)
        col = ramp(nt, z.outputs["Z"], [(0.0, srgb(0.93, 0.74, 0.45)), (0.22, srgb(0.84, 0.5, 0.17)), (0.55, srgb(0.56, 0.24, 0.06)), (1.0, srgb(0.43, 0.16, 0.035))])
        dark = _mix_rgba(nt, 0.25, col, srgb(0.3, 0.1, 0.02))
        nt.links.new(_mix_rgba(nt, n.outputs["Fac"], col, dark), b.inputs["Base Color"])
        bump(nt, b, noise_tex(nt, tex_coord(nt, "Object"), 400.0, 4.0).outputs["Fac"], 0.06, 0.0004)
        return m

    def _bun_side(self):
        m, nt, b = principled("bun_side", rough=0.45, coat=0.3, sss=0.1, sss_scale=0.004)
        z = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tex_coord(nt, "Generated"), z.inputs[0])
        col = ramp(nt, z.outputs["Z"], [(0.0, srgb(0.86, 0.58, 0.27)), (0.6, srgb(0.92, 0.72, 0.42)), (1.0, srgb(0.78, 0.47, 0.18))])
        nt.links.new(col, b.inputs["Base Color"])
        bump(nt, b, noise_tex(nt, tex_coord(nt, "Object"), 350.0, 4.0).outputs["Fac"], 0.05, 0.0004)
        return m

    def _crumb(self):
        m, nt, b = principled("crumb", rough=0.8, sss=0.15, sss_scale=0.003)
        v = nt.nodes.new("ShaderNodeTexVoronoi")
        v.inputs["Scale"].default_value = 260.0
        nt.links.new(tex_coord(nt, "Object"), v.inputs["Vector"])
        n = noise_tex(nt, tex_coord(nt, "Object"), 40.0, 4.0)
        col = _mix_rgba(nt, n.outputs["Fac"], srgb(0.93, 0.74, 0.45), srgb(0.76, 0.45, 0.16))
        nt.links.new(col, b.inputs["Base Color"])
        bump(nt, b, v.outputs["Distance"], 0.35, 0.0006)
        return m

    def _chicken(self, name):
        """raw (wet when dipped) -> floured -> fried, mixed by the 'wet', 'coat' and 'fry' values."""
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        out = nt.nodes["Material Output"]
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        crag = nt.nodes.new("ShaderNodeAttribute")
        crag.attribute_name = "crag"
        wet, coat, fry = value_node(nt, "wet"), value_node(nt, "coat"), value_node(nt, "fry")
        n = noise_tex(nt, tex_coord(nt, "Object"), 260.0, 6.0, 0.6)
        vor = nt.nodes.new("ShaderNodeTexVoronoi")  # crumbly, crunchy surface detail for the coating
        vor.inputs["Scale"].default_value = 520.0
        nt.links.new(tex_coord(nt, "Object"), vor.inputs["Vector"])
        grit = noise_tex(nt, tex_coord(nt, "Object"), 1500.0, 4.0, 0.7)
        crunchy = nt.nodes.new("ShaderNodeMath"); crunchy.operation = "MULTIPLY_ADD"
        nt.links.new(vor.outputs["Distance"], crunchy.inputs[0]); crunchy.inputs[1].default_value = 0.8
        nt.links.new(grit.outputs["Fac"], crunchy.inputs[2])
        def bsdf(color, rough, coatw, sss, rough_bump=False):
            b = nt.nodes.new("ShaderNodeBsdfPrincipled")
            _set(nt, b.inputs["Base Color"], color)
            b.inputs["Roughness"].default_value = rough
            b.inputs["Coat Weight"].default_value = coatw
            b.inputs["Subsurface Weight"].default_value = sss
            b.inputs["Subsurface Scale"].default_value = 0.004
            if hasattr(b, "subsurface_method"):
                b.subsurface_method = "BURLEY"
            bp = nt.nodes.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = 0.55 if rough_bump else 0.12
            bp.inputs["Distance"].default_value = 0.0012 if rough_bump else 0.0004
            nt.links.new((crunchy if rough_bump else n).outputs[0 if rough_bump else "Fac"], bp.inputs["Height"])
            nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
            return b
        raw_col = _mix_rgba(nt, n.outputs["Fac"], srgb(0.93, 0.66, 0.6), srgb(0.84, 0.5, 0.47))
        raw_col = _mix_rgba(nt, wet.outputs[0], raw_col, srgb(0.95, 0.92, 0.86))
        flour_col = _mix_rgba(nt, crag.outputs["Fac"], srgb(0.96, 0.93, 0.86), srgb(0.84, 0.78, 0.66))
        fried_col = ramp(nt, crag.outputs["Fac"], [(0.0, srgb(0.72, 0.38, 0.09)), (0.45, srgb(0.9, 0.58, 0.2)), (0.8, srgb(0.8, 0.46, 0.13)), (1.0, srgb(0.5, 0.24, 0.06))])
        fried_col = _mix_rgba(nt, n.outputs["Fac"], fried_col, srgb(0.66, 0.34, 0.08))
        raw, flour, fried = bsdf(raw_col, 0.22, 0.5, 0.35), bsdf(flour_col, 0.95, 0.0, 0.0, True), bsdf(fried_col, 0.5, 0.06, 0.0, True)
        m1 = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(coat.outputs[0], m1.inputs[0]); nt.links.new(raw.outputs[0], m1.inputs[1]); nt.links.new(flour.outputs[0], m1.inputs[2])
        m2 = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(fry.outputs[0], m2.inputs[0]); nt.links.new(m1.outputs[0], m2.inputs[1]); nt.links.new(fried.outputs[0], m2.inputs[2])
        nt.links.new(m2.outputs[0], out.inputs["Surface"])
        return m

    def _flake(self):
        m, nt, b = principled("flake", rough=0.9, sss=0.0)
        fry = value_node(nt, "fry")
        nt.links.new(_mix_rgba(nt, fry.outputs[0], srgb(0.97, 0.94, 0.87), srgb(0.84, 0.5, 0.14)), b.inputs["Base Color"])
        return m

    def _lettuce(self):
        m, nt, b = principled("lettuce", rough=0.42, coat=0.3, sss=0.35, sss_radius=(0.5, 1.0, 0.3), sss_scale=0.003)
        g = nt.nodes.new("ShaderNodeTexGradient")
        g.gradient_type = "SPHERICAL"
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (15.0, 15.0, 15.0)
        nt.links.new(tex_coord(nt, "Object"), mp.inputs["Vector"])
        nt.links.new(mp.outputs[0], g.inputs["Vector"])
        col = ramp(nt, g.outputs["Fac"], [(0.0, srgb(0.3, 0.6, 0.14)), (0.6, srgb(0.55, 0.78, 0.3)), (1.0, srgb(0.82, 0.92, 0.6))])
        nt.links.new(col, b.inputs["Base Color"])
        bump(nt, b, noise_tex(nt, tex_coord(nt, "Object"), 120.0, 3.0).outputs["Fac"], 0.08, 0.0005)
        return m

    def _flour(self):
        m, nt, b = principled("flour", srgb(0.97, 0.95, 0.91), rough=1.0, sss=0.1, sss_scale=0.002)
        bump(nt, b, noise_tex(nt, tex_coord(nt, "Object"), 160.0, 5.0).outputs["Fac"], 0.2, 0.0006)
        return m

    def _slate(self):
        m, nt, b = principled("slate", rough=0.62, spec=0.4)
        n = noise_tex(nt, tex_coord(nt, "Object"), 6.0, 8.0, 0.7)
        nt.links.new(_mix_rgba(nt, n.outputs["Fac"], srgb(0.1, 0.1, 0.11), srgb(0.17, 0.165, 0.16)), b.inputs["Base Color"])
        bump(nt, b, noise_tex(nt, tex_coord(nt, "Object"), 40.0, 6.0).outputs["Fac"], 0.15, 0.002)
        return m

    def _glow(self):
        m = bpy.data.materials.new("glow")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        g = nt.nodes.new("ShaderNodeTexGradient")
        g.gradient_type = "SPHERICAL"
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (2.2, 2.2, 2.2)
        nt.links.new(tex_coord(nt, "Object"), mp.inputs["Vector"])
        nt.links.new(mp.outputs[0], g.inputs["Vector"])
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = srgb(1.0, 0.55, 0.22)
        p = nt.nodes.new("ShaderNodeMath")
        p.operation = "POWER"
        nt.links.new(g.outputs["Fac"], p.inputs[0])
        p.inputs[1].default_value = 2.2
        s = nt.nodes.new("ShaderNodeMath")
        s.operation = "MULTIPLY"
        nt.links.new(p.outputs[0], s.inputs[0])
        s.inputs[1].default_value = 0.9
        s.name = "glow_strength"
        nt.links.new(s.outputs[0], em.inputs["Strength"])
        nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
        return m


# ---------------------------------------------------------------- studio: backdrop, counter, lights, camera
def studio(M, counter=True, glow=True, glow_at=(0, 0.9, 0.25)):
    # a curved cyclorama: floor running into a back wall, so there is no horizon line
    pts = [(-2.0, 0.0), (0.5, 0.0)] + [(0.5 + 0.3 * math.sin(a), 0.3 - 0.3 * math.cos(a)) for a in [i * math.pi / 16 for i in range(1, 9)]] + [(0.8, 1.8)]
    pts = [(y, z - 0.04) for y, z in pts]
    cyc = bpy.data.meshes.new("cyclorama")
    vs, fs = [], []
    for i, (y, z) in enumerate(pts):
        vs += [(-3.0, y, z), (3.0, y, z)]
        if i:
            a = 2 * (i - 1)
            fs.append((a, a + 1, a + 3, a + 2))
    cyc.from_pydata(vs, [], fs)
    new_obj("cyclorama", cyc, M.backdrop)
    if counter:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.02))
        c = bpy.context.object
        c.name = "counter"
        c.scale = (1.6, 1.2, 0.04)
        c.data.materials.append(M.slate)
        bev = c.modifiers.new("bevel", "BEVEL")
        bev.width, bev.segments = 0.006, 3
    if glow:
        bpy.ops.mesh.primitive_plane_add(size=0.9, location=glow_at, rotation=(math.radians(90), 0, 0))
        g = bpy.context.object
        g.name = "glow"
        g.data.materials.append(M.glow)
        g.visible_shadow = False
        g.visible_diffuse = False
        g.visible_glossy = True


def area_light(name, loc, target, power, size, color=(1, 1, 1), shape="RECTANGLE", size_y=None, spread=None):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color[:3]
    data.shape = shape
    data.size = size
    if size_y is not None:
        data.size_y = size_y
    if spread is not None:
        data.spread = spread
    obj = link(bpy.data.objects.new(name, data))
    obj.location = loc
    aim(obj, target)
    return obj


def aim(obj, target):
    d = Vector(target) - Vector(obj.location)
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def lights(target=(0, 0, 0.05), warm=1.0):
    t = Vector(target)
    area_light("key", t + Vector((-0.55, -0.6, 0.75)), t, 30 * warm, 0.55, (1.0, 0.86, 0.72))
    area_light("fill", t + Vector((0.7, -0.55, 0.25)), t, 7, 0.8, (0.85, 0.9, 1.0))
    area_light("rim_l", t + Vector((-0.45, 0.55, 0.35)), t, 26, 0.06, (1.0, 0.62, 0.3), size_y=0.7)
    area_light("rim_r", t + Vector((0.5, 0.5, 0.3)), t, 20, 0.06, (1.0, 0.95, 0.9), size_y=0.7)
    area_light("top", t + Vector((0, 0.05, 0.9)), t, 12, 0.5, (1.0, 0.92, 0.85))


def camera(lens=60, fstop=2.8):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = lens
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_height = 24
    cam_data.clip_start = 0.005
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = fstop
    cam = link(bpy.data.objects.new("cam", cam_data))
    tgt = link(bpy.data.objects.new("cam_target", None))
    con = cam.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    cam_data.dof.focus_object = tgt
    bpy.context.scene.camera = cam
    return cam, tgt


def shoot(cam, tgt, pos, target, lens=None, fstop=None, roll=0.0, focus=None):
    cam.location = pos
    tgt.location = target
    if lens:
        cam.data.lens = lens
    if fstop:
        cam.data.dof.aperture_fstop = fstop
    cam.data.dof.focus_object = None if focus is not None else tgt
    if focus is not None:
        cam.data.dof.focus_distance = (Vector(pos) - Vector(focus)).length
    cam.constraints[0].influence = 1.0
    cam.rotation_euler = (0, 0, 0)
    cam.delta_rotation_euler = (0, 0, roll)


# ---------------------------------------------------------------- geometry helpers
def lathe(name, profile, steps=96, mat=None):
    """Revolve (r, z) points around Z."""
    bm = bmesh.new()
    verts = [bm.verts.new((max(r, 0.0), 0.0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=steps, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return new_obj(name, me, mat)


def disc(name, radius, z=0.0, segments=96, rings=24, mat=None, up=True):
    bm = bmesh.new()
    center = bm.verts.new((0, 0, z))
    rings_v = []
    for j in range(1, rings + 1):
        r = radius * j / rings
        rings_v.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in [i / segments * 2 * math.pi for i in range(segments)]])
    for i in range(segments):
        a, b2 = rings_v[0][i], rings_v[0][(i + 1) % segments]
        bm.faces.new((center, a, b2) if up else (center, b2, a))
    for j in range(rings - 1):
        for i in range(segments):
            a, b2 = rings_v[j][i], rings_v[j][(i + 1) % segments]
            c, d = rings_v[j + 1][(i + 1) % segments], rings_v[j + 1][i]
            bm.faces.new((a, d, c, b2) if up else (a, b2, c, d))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return new_obj(name, me, mat)


def group(name, *children, loc=(0, 0, 0)):
    g = link(bpy.data.objects.new(name, None))
    g.location = loc
    for c in children:
        c.parent = g
    return g


# ---------------------------------------------------------------- food
def bun_top(M, name="bun_top", R=0.059, H=0.036):
    prof = [(0.0, H), (0.2 * R, H * 0.99), (0.45 * R, H * 0.93), (0.66 * R, H * 0.8), (0.83 * R, H * 0.6), (0.95 * R, H * 0.36), (1.0 * R, H * 0.16), (0.985 * R, H * 0.05), (0.95 * R, 0.0)]
    top = lathe(name + "_dome", prof, 112, M.bun_top)
    top.modifiers.new("sub", "SUBSURF").levels = 1
    cut = disc(name + "_cut", 0.95 * R, 0.0, 112, 16, M.crumb, up=False)
    return group(name, top, cut)


def bun_bottom(M, name="bun_bottom", R=0.059, H=0.022):
    prof = [(0.0, 0.0), (0.8 * R, 0.0), (0.95 * R, H * 0.12), (1.0 * R, H * 0.45), (0.99 * R, H * 0.8), (0.95 * R, H)]
    side = lathe(name + "_side", prof, 112, M.bun_side)
    side.modifiers.new("sub", "SUBSURF").levels = 1
    cut = disc(name + "_cut", 0.95 * R, H, 112, 16, M.crumb)
    return group(name, side, cut)


def chicken(M, name="chicken", seed=3, R=(0.07, 0.052, 0.017)):
    """Irregular boneless thigh fillet. Shape key 'crust' adds the craggy fried coating; colour attribute
    'crag' (0..1) marks the crests for the material."""
    rnd = random.Random(seed)
    off = Vector((rnd.random() * 50, rnd.random() * 50, rnd.random() * 50))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=176, v_segments=88, radius=1.0)
    for v in bm.verts:
        p = v.co.copy()
        lobe = 1 + 0.3 * noise.noise(p * 1.4 + off) + 0.1 * noise.noise(p * 3.5 + off * 2)
        xy = math.sqrt(p.x * p.x + p.y * p.y)
        thick = (0.85 + 0.3 * noise.noise(p * 2.0 + off * 3)) * (0.6 + 0.4 * math.sqrt(max(0.0, 1 - xy * xy * 0.7)))
        v.co = Vector((p.x * R[0] * lobe, p.y * R[1] * lobe, p.z * R[2] * thick))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = new_obj(name, me, M.chicken)
    basis = obj.shape_key_add(name="Basis")
    crust = obj.shape_key_add(name="crust", from_mix=False)
    me.update()
    normals = [v.normal.copy() for v in me.vertices]
    amounts = []
    for i, v in enumerate(me.vertices):
        p = v.co * 330.0 + off  # mesh is in metres: ~3 mm crags, 1.5 mm chunks, fine grit
        ridge = noise.ridged_multi_fractal(p, 0.9, 2.2, 4, 1.0, 2.2, noise_basis="PERLIN_ORIGINAL")
        chunk = noise.noise(v.co * 650.0 + off * 1.7)
        fine = noise.noise(v.co * 1600.0 + off)
        amounts.append(ridge * 0.55 + 0.3 * (chunk * 0.5 + 0.5) + 0.15 * (fine * 0.5 + 0.5))
    lo, hi = min(amounts), max(amounts)
    attr = me.color_attributes.new("crag", "FLOAT_COLOR", "POINT")
    for i, v in enumerate(me.vertices):
        a = (amounts[i] - lo) / (hi - lo + 1e-9)
        crust.data[i].co = v.co + normals[i] * (0.0012 + 0.0062 * a ** 1.15)
        attr.data[i].color = (a, a, a, 1.0)
    obj.data.shape_keys.key_blocks["crust"].value = 0.0
    sub = obj.modifiers.new("sub", "SUBSURF")
    sub.levels, sub.render_levels = 0, 1
    return obj


def surface_samples(obj, count, seed=1, min_nz=-2.0):
    """Random points on the mesh's crust surface (local coords) with normals."""
    me = obj.data
    rnd = random.Random(seed)
    crust = me.shape_keys.key_blocks["crust"].data if me.shape_keys else None
    verts = [i for i, v in enumerate(me.vertices) if v.normal.z >= min_nz]
    out = []
    for _ in range(count):
        i = rnd.choice(verts)
        co = (crust[i].co if crust else me.vertices[i].co).copy()
        out.append((co, me.vertices[i].normal.copy()))
    return out


def lettuce(M, name="lettuce", R=0.066, seed=5):
    obj = disc(name, R, 0.0, 120, 26, M.lettuce)
    rnd = random.Random(seed)
    off = Vector((rnd.random() * 40, rnd.random() * 40, 0))
    for v in obj.data.vertices:
        x, y = v.co.x, v.co.y
        r, a = math.hypot(x, y), math.atan2(y, x)
        edge = (r / R) ** 2
        wave = 0.0045 * math.sin(a * 7 + 2.5 * noise.noise(Vector((x, y, 0)) * 30 + off)) * edge
        fold = 0.003 * noise.noise(Vector((x, y, 0)) * 25 + off) + 0.009 * edge
        rr = 1 + 0.08 * noise.noise(Vector((math.cos(a), math.sin(a), 0)) * 3 + off)
        v.co = Vector((x * rr, y * rr, wave + fold))
    obj.modifiers.new("solid", "SOLIDIFY").thickness = 0.0012
    obj.modifiers.new("sub", "SUBSURF").levels = 1
    return obj


def cheese(M, name="cheese", S=0.088, dome=(0.062, 0.017)):
    """Square slice; shape key 'melt' drapes it over a domed patty of radius dome[0]."""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=48, y_subdivisions=48, size=S, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.z = math.radians(45)
    obj.data.materials.append(M.cheese)
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.shape_key_add(name="Basis")
    melt = obj.shape_key_add(name="melt", from_mix=False)
    R, h = dome
    for i, v in enumerate(obj.data.vertices):
        x, y = v.co.x, v.co.y
        r = math.hypot(x, y) + 1e-9
        u = min(r / R, 1.0)
        z = -h * 0.6 * u * u
        over = max(0.0, r - R * 0.92)
        k = (min(r, R * 0.92) + over * 0.55) / r
        z -= over * 0.9 + over * over * 30 + 0.004 * max(0.0, math.sin(math.atan2(y, x) * 5)) * min(1.0, over * 60)
        melt.data[i].co = Vector((x * k, y * k, z))
    obj.modifiers.new("solid", "SOLIDIFY").thickness = 0.0022
    return obj


def sauce_swirl(M, name="sauce", R=0.045, turns=2.6, z=0.0):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0032
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    n = 220
    sp.points.add(n - 1)
    for i in range(n):
        u = i / (n - 1)
        a = u * turns * 2 * math.pi
        r = R * (1 - u * 0.92)
        sp.points[i].co = (r * math.cos(a), r * math.sin(a), z + 0.0025 + 0.003 * u, 1)
    obj = link(bpy.data.objects.new(name, cu))
    cu.materials.append(M.sauce)
    cu.bevel_factor_end = 1.0
    return obj


def bowl(M, name, mat, R=0.075, H=0.05):
    prof = [(0.0, 0.0), (0.55 * R, 0.0), (0.8 * R, 0.12 * H), (0.96 * R, 0.55 * H), (1.0 * R, H), (0.94 * R, H), (0.9 * R, 0.55 * H), (0.74 * R, 0.16 * H), (0.5 * R, 0.08 * H), (0.0, 0.08 * H)]
    b = lathe(name, prof, 96, mat)
    b.modifiers.new("sub", "SUBSURF").levels = 1
    return b


def pot(M, name="pot", R=0.11, H=0.1):
    prof = [(0.0, 0.0), (0.95 * R, 0.0), (R, 0.04 * H), (1.02 * R, 0.96 * H), (1.04 * R, H), (0.97 * R, H), (0.96 * R, 0.08 * H), (0.9 * R, 0.05 * H), (0.0, 0.05 * H)]
    p = lathe(name, prof, 112, M.pot)
    p.modifiers.new("sub", "SUBSURF").levels = 1
    for s in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.018, minor_radius=0.005, location=(s * (R + 0.012), 0, 0.82 * H), rotation=(math.radians(90), 0, 0))
        h = bpy.context.object
        h.data.materials.append(M.pot)
        h.parent = p
    return p


def liquid(M, name, R, mat, waves=True):
    s = disc(name, R, 0.0, 120, 30, mat)
    if waves:
        w = s.modifiers.new("wave", "WAVE")
        w.use_normal = False
        w.height, w.width, w.speed, w.narrowness = 0.0, 0.012, 0.25, 1.5
    return s


def set_wave(obj, height, start_frame, x=0.0, y=0.0):
    w = obj.modifiers["wave"]
    w.height = height
    w.time_offset = start_frame
    w.start_position_x, w.start_position_y = x, y


def label(M, text, size=0.012, plate=True, dark=False, font=None):
    cu = bpy.data.curves.new("label_" + text, "FONT")
    cu.body = text
    cu.size = size
    cu.extrude = size * 0.08
    cu.bevel_depth = size * 0.02
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    f = font_file()
    if f:
        cu.font = f
    t = link(bpy.data.objects.new("label_" + text, cu))
    cu.materials.append(M.text)
    parts = [t]
    if plate:
        bpy.context.view_layer.update()
        w = max(t.dimensions.x, size * 2) + size * 1.1
        h = size * 1.55
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -size * 0.06))
        p = bpy.context.object
        p.scale = (w, h, size * 0.12)
        p.data.materials.append(M.label_dark if dark else M.label)
        bev = p.modifiers.new("bevel", "BEVEL")
        bev.width, bev.segments = h * 0.48, 6
        bev.affect = "EDGES"
        bpy.ops.object.transform_apply(scale=True)
        parts.append(p)
        t.location.z = size * 0.04
    g = group("tag_" + text, *parts)
    return g


_FONT = []


def font_file():
    if not _FONT:
        for path in ("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                     "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
            if os.path.exists(path):
                _FONT.append(bpy.data.fonts.load(path))
                break
        else:
            _FONT.append(None)
    return _FONT[0]


def face_camera(obj, cam, tilt=0.0):
    """Turn a label to face the camera."""
    here = Vector(obj.location) if obj.parent is None else obj.matrix_world.translation
    d = Vector(cam.location) - here
    q = d.to_track_quat("Z", "Y")
    obj.rotation_euler = (q @ Euler((tilt, 0, 0)).to_quaternion()).to_euler()


def leader(M, name="leader"):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0007
    sp = cu.splines.new("POLY")
    sp.points.add(1)
    obj = link(bpy.data.objects.new(name, cu))
    cu.materials.append(M.text)
    return obj


def set_leader(obj, a, b, grow=1.0):
    sp = obj.data.splines[0]
    sp.points[0].co = (*a, 1)
    sp.points[1].co = (*b, 1)
    obj.data.bevel_factor_end = clamp(grow)
    obj.hide_render = grow <= 0.001


# ---------------------------------------------------------------- particles (instanced points driven from Python)
class Points:
    """A cloud of instances whose positions, scales and rotations are set each frame."""

    def __init__(self, name, count, instance, parent=None):
        self.count = count
        me = bpy.data.meshes.new(name)
        me.vertices.add(count)
        me.attributes.new("pscale", "FLOAT", "POINT")
        me.attributes.new("prot", "FLOAT_VECTOR", "POINT")
        self.obj = link(bpy.data.objects.new(name, me))
        if parent:
            self.obj.parent = parent
        ng = bpy.data.node_groups.new(name + "_gn", "GeometryNodeTree")
        ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        gi, go = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
        inst = ng.nodes.new("GeometryNodeInstanceOnPoints")
        oi = ng.nodes.new("GeometryNodeObjectInfo")
        oi.inputs["Object"].default_value = instance
        ns = ng.nodes.new("GeometryNodeInputNamedAttribute"); ns.data_type = "FLOAT"; ns.inputs["Name"].default_value = "pscale"
        nr = ng.nodes.new("GeometryNodeInputNamedAttribute"); nr.data_type = "FLOAT_VECTOR"; nr.inputs["Name"].default_value = "prot"
        ng.links.new(gi.outputs[0], inst.inputs["Points"])
        ng.links.new(oi.outputs["Geometry"], inst.inputs["Instance"])
        ng.links.new(ns.outputs["Attribute"], inst.inputs["Scale"])
        ng.links.new(nr.outputs["Attribute"], inst.inputs["Rotation"])
        ng.links.new(inst.outputs["Instances"], go.inputs[0])
        self.obj.modifiers.new("inst", "NODES").node_group = ng
        hide_render(instance)

    def set(self, cos, scales, rots=None):
        me = self.obj.data
        flat = [c for p in cos for c in p]
        me.vertices.foreach_set("co", flat)
        me.attributes["pscale"].data.foreach_set("value", list(scales))
        if rots is not None:
            me.attributes["prot"].data.foreach_set("vector", [c for r in rots for c in r])
        me.update()


def blob(name, mat, r=1.0, subdiv=1, squash=(1, 1, 1), jitter=0.25, seed=0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r)
    obj = bpy.context.object
    obj.name = name
    rnd = random.Random(seed)
    for v in obj.data.vertices:
        v.co = Vector((v.co.x * squash[0], v.co.y * squash[1], v.co.z * squash[2])) * (1 + jitter * (rnd.random() - 0.5))
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.materials.append(mat)
    return obj


def sprite_mat(name, color=(1, 1, 1, 1), strength=0.4):
    """Soft, noisy, partly transparent card for steam and flour clouds; opacity via value 'alpha'."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    a = value_node(nt, "alpha", 0.0)
    g = nt.nodes.new("ShaderNodeTexGradient")
    g.gradient_type = "SPHERICAL"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-0.5, -0.5, 0)
    mp.inputs["Scale"].default_value = (2.0, 2.0, 2.0)
    nt.links.new(tex_coord(nt, "Generated"), mp.inputs["Vector"])
    nt.links.new(mp.outputs[0], g.inputs["Vector"])
    n = noise_tex(nt, tex_coord(nt, "Generated"), 3.0, 4.0, 0.6, 1.2)
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    nt.links.new(g.outputs["Fac"], mul.inputs[0]); nt.links.new(n.outputs["Fac"], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath"); mul2.operation = "MULTIPLY"; mul2.use_clamp = True
    nt.links.new(mul.outputs[0], mul2.inputs[0]); nt.links.new(a.outputs[0], mul2.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    pr = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pr.inputs["Base Color"].default_value = color
    pr.inputs["Roughness"].default_value = 1.0
    pr.inputs["Emission Color"].default_value = color
    pr.inputs["Emission Strength"].default_value = strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mul2.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(pr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


class Sprites:
    """Camera-facing soft cards (steam, flour clouds)."""

    def __init__(self, name, count, color=(1, 1, 1, 1), strength=0.4, seed=1):
        self.items = []
        rnd = random.Random(seed)
        for i in range(count):
            bpy.ops.mesh.primitive_plane_add(size=1)
            p = bpy.context.object
            p.name = f"{name}_{i}"
            m = sprite_mat(f"{name}_m{i}", color, strength)
            p.data.materials.append(m)
            p.visible_shadow = False
            self.items.append((p, m, [rnd.random() for _ in range(6)]))

    def hide(self):
        for p, m, _ in self.items:
            p.hide_render = True

    def rise(self, t, cam, origin, amount=1.0, rate=0.6, height=0.12, spread=0.05, size=0.06, life=1.6):
        for p, m, r in self.items:
            age = ((t * rate / life) + r[0]) % 1.0
            p.hide_render = amount <= 0.001
            p.location = Vector(origin) + Vector(((r[1] - 0.5) * spread * (0.6 + age), (r[2] - 0.5) * spread * 0.6, age * height))
            s = size * (0.5 + age * 1.6) * (0.7 + r[3] * 0.6)
            p.scale = (s, s, s)
            face_camera(p, cam, 0)
            p.rotation_euler.rotate_axis("Z", r[4] * 6 + age)
            set_value(m, "alpha", amount * 0.55 * math.sin(math.pi * age) * (0.5 + 0.5 * r[5]))

    def burst(self, t, t0, cam, origin, amount=1.0, spread=0.12, up=0.08, size=0.07, life=0.9):
        for p, m, r in self.items:
            dt = t - t0 - r[0] * 0.08
            if dt < 0 or dt > life:
                p.hide_render = True
                continue
            p.hide_render = False
            k = ease_out(dt / life)
            ang = r[1] * 2 * math.pi
            p.location = Vector(origin) + Vector((math.cos(ang) * spread * k * (0.4 + r[2]), math.sin(ang) * spread * 0.7 * k * (0.4 + r[2]), 0.005 + up * k * (0.5 + r[3])))
            s = size * (0.5 + k * 1.8) * (0.7 + r[4] * 0.6)
            p.scale = (s, s, s)
            face_camera(p, cam, 0)
            set_value(m, "alpha", amount * 0.9 * (1 - dt / life) * min(1.0, dt * 14))


def ballistic(n, seed, t, t0, origin, power=1.0, life=0.8, spread=1.0, up=1.0, size=0.002, floor=-1.0, gravity=2.4, slow=1.0, drift=(0, 0, 0)):
    """Positions/scales for a burst of bits (droplets, crumbs)."""
    rnd = random.Random(seed)
    cos, scales, rots = [], [], []
    for i in range(n):
        a, b, c, e, f, g = (rnd.random() for _ in range(6))
        dt = (t - t0 - a * 0.05) * slow
        o = Vector(origin)
        s = 0.0
        if 0 < dt < life:
            ang = b * 2 * math.pi
            sp = (0.2 + c * 0.6) * power * spread
            o = o + Vector((math.cos(ang) * sp * dt + drift[0] * dt, math.sin(ang) * sp * dt * 0.8 + drift[1] * dt, (0.45 + e * 0.9) * power * up * dt - gravity * dt * dt + drift[2] * dt))
            s = 0.0 if o.z < origin[2] + floor else size * (0.5 + f) * (1 - dt / life * 0.4)
        cos.append(o)
        scales.append(s)
        rots.append((g * 6, a * 6 + dt * 4, c * 6))
    return cos, scales, rots


def floaters(n, seed, t, center, box=(0.12, 0.12, 0.16), size=0.0018, speed=0.02):
    """Slowly drifting bits around a point (crumbs, dust)."""
    rnd = random.Random(seed)
    cos, scales, rots = [], [], []
    for i in range(n):
        p = Vector(((rnd.random() - 0.5) * box[0], (rnd.random() - 0.5) * box[1], (rnd.random() - 0.5) * box[2]))
        ph = rnd.random() * 6.28
        p += Vector((math.sin(t * 0.7 + ph) * 0.006, math.cos(t * 0.6 + ph) * 0.006, ((t * speed + rnd.random()) % 1.0 - 0.5) * 0.03))
        cos.append(Vector(center) + p)
        scales.append(size * (0.5 + rnd.random()))
        rots.append((t * (rnd.random() - 0.5) * 2 + ph, ph * 2, t * 0.5))
    return cos, scales, rots
