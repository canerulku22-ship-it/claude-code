"""Procedural materials. Every look is built from shader nodes, with no image files.

``principled()`` makes a basic material; the named functions below build the specific
looks used by the assets and studio. Materials are cached by name, so building the same
asset twice reuses them.
"""

import bpy

# Principled BSDF input names changed slightly between Blender versions; the first name
# that exists is used.
_ALIASES = {
    "specular": ("Specular IOR Level", "Specular"),
    "coat": ("Coat Weight", "Clearcoat"),
    "coat_roughness": ("Coat Roughness", "Clearcoat Roughness"),
    "transmission": ("Transmission Weight", "Transmission"),
    "emission": ("Emission Color", "Emission"),
    "subsurface": ("Subsurface Weight", "Subsurface"),
    "sheen": ("Sheen Weight", "Sheen"),
}


def _input(node, key):
    for name in _ALIASES.get(key, (key,)):
        if name in node.inputs:
            return node.inputs[name]
    return None


def _set(node, key, value):
    sock = _input(node, key)
    if sock is not None:
        sock.default_value = value


def new_material(name):
    """Fresh node material with an empty tree (Principled + Output removed)."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat, False
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    return mat, True


def principled(name, color=(0.8, 0.8, 0.8), roughness=0.5, metallic=0.0, specular=0.5,
               coat=0.0, coat_roughness=0.03, transmission=0.0, alpha=1.0, emission=None,
               emission_strength=0.0, ior=1.45):
    mat, fresh = new_material(name)
    if not fresh:
        return mat
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["IOR"].default_value = ior
    _set(bsdf, "specular", specular)
    _set(bsdf, "coat", coat)
    _set(bsdf, "coat_roughness", coat_roughness)
    _set(bsdf, "transmission", transmission)
    bsdf.inputs["Alpha"].default_value = alpha
    if emission is not None:
        _set(bsdf, "emission", (*emission[:3], 1.0))
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    mat.diffuse_color = (*color[:3], 1.0)
    return mat


def bsdf_of(mat):
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def set_blended(mat):
    """Alpha-blended transparency (Eevee). Works for Eevee 'Next' (4.2+) and older Eevee.

    Blended objects don't cast shadows (see ``studio.no_transparent_shadows``): transparent shadows
    roughly halve render speed on CPU, and glass shadows are faint anyway.
    """
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    else:
        mat.blend_method = "BLEND"
    if hasattr(mat, "use_transparent_shadow"):
        mat.use_transparent_shadow = False
    if hasattr(mat, "show_transparent_back"):
        mat.show_transparent_back = True
    if hasattr(mat, "use_transparency_overlap"):
        mat.use_transparency_overlap = True


def _ramp(nt, stops, interpolation="LINEAR"):
    """Color Ramp node from [(position, (r, g, b)), ...]."""
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = interpolation
    els = ramp.color_ramp.elements
    while len(els) > len(stops):
        els.remove(els[-1])
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, col) in zip(els, stops):
        el.position = pos
        el.color = (*col[:3], 1.0)
    return ramp


def _math(nt, op, a=None, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n


def _mix_color(nt, fac, a, b):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    for sock, v in ((n.inputs["Factor"], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, tuple):
            sock.default_value = (*v[:3], 1.0)
        else:
            nt.links.new(v, sock)
    return n


def _principled_tree(mat):
    nt = mat.node_tree
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return nt, bsdf


# ---------------------------------------------------------------------------
# Drop-object materials
# ---------------------------------------------------------------------------

def bowling_ball():
    """Glossy marbled resin; each ball picks its colour from a palette (Object Info random)."""
    mat, fresh = new_material("BowlingBall")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    info = nt.nodes.new("ShaderNodeObjectInfo")
    palette = _ramp(nt, [
        (0.00, (0.03, 0.10, 0.55)),   # cobalt
        (0.17, (0.55, 0.03, 0.30)),   # magenta
        (0.34, (0.02, 0.38, 0.36)),   # teal
        (0.51, (0.80, 0.25, 0.02)),   # orange
        (0.68, (0.25, 0.04, 0.50)),   # violet
        (0.85, (0.60, 0.02, 0.04)),   # red
    ], interpolation="CONSTANT")
    nt.links.new(info.outputs["Random"], palette.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Distortion"].default_value = 4.0
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    swirl = _ramp(nt, [(0.30, (0, 0, 0)), (0.52, (1, 1, 1)), (0.60, (0.35, 0.35, 0.35)), (0.75, (1, 1, 1))])
    nt.links.new(noise.outputs["Fac"], swirl.inputs[0])
    dark = _mix_color(nt, 0.75, palette.outputs[0], (0.0, 0.0, 0.0))
    col = _mix_color(nt, swirl.outputs[0], dark.outputs[2], palette.outputs[0])
    light = _mix_color(nt, 0.35, palette.outputs[0], (1.0, 1.0, 1.0))
    streak = _math(nt, "GREATER_THAN", noise.outputs["Fac"], 0.66)
    col2 = _mix_color(nt, streak.outputs[0], col.outputs[2], light.outputs[2])
    nt.links.new(col2.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.18
    _set(bsdf, "coat", 1.0)
    _set(bsdf, "coat_roughness", 0.04)
    mat.diffuse_color = (0.2, 0.1, 0.5, 1.0)
    return mat


def watermelon():
    mat, fresh = new_material("Watermelon")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    tex = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 2.2
    wave.inputs["Distortion"].default_value = 7.0
    wave.inputs["Detail"].default_value = 4.0
    wave.inputs["Detail Scale"].default_value = 1.5
    # Stripes run along the long (X) axis: drive the bands by the angle around X.
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Object"], sep.inputs[0])
    ang = _math(nt, "ARCTAN2", sep.outputs[2], sep.outputs[1])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(ang.outputs[0], comb.inputs[1])
    nt.links.new(sep.outputs[0], comb.inputs[0])
    nt.links.new(comb.outputs[0], wave.inputs["Vector"])
    ramp = _ramp(nt, [(0.35, (0.02, 0.12, 0.02)), (0.55, (0.20, 0.42, 0.08))])
    nt.links.new(wave.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.38
    _set(bsdf, "coat", 0.4)
    mat.diffuse_color = (0.1, 0.3, 0.05, 1.0)
    return mat


def brick():
    mat, fresh = new_material("Brick")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    info = nt.nodes.new("ShaderNodeObjectInfo")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 60.0
    noise.inputs["Detail"].default_value = 8.0
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    tone = _ramp(nt, [(0.0, (0.45, 0.12, 0.05)), (0.5, (0.62, 0.20, 0.08)), (1.0, (0.55, 0.26, 0.14))])
    nt.links.new(info.outputs["Random"], tone.inputs[0])
    speck = _ramp(nt, [(0.30, (0.25, 0.08, 0.04)), (0.55, (1, 1, 1))])
    nt.links.new(noise.outputs["Fac"], speck.inputs[0])
    mul = _mix_color(nt, 1.0, tone.outputs[0], speck.outputs[0])
    mul.blend_type = "MULTIPLY"
    nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
    rough = _math(nt, "MULTIPLY_ADD", noise.outputs["Fac"], 0.3)
    rough.inputs[2].default_value = 0.65
    nt.links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    mat.diffuse_color = (0.6, 0.2, 0.08, 1.0)
    return mat


def iron():
    mat, fresh = new_material("ForgedIron")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 10.0
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    ramp = _ramp(nt, [(0.35, (0.05, 0.055, 0.065)), (0.65, (0.16, 0.17, 0.19))])
    nt.links.new(noise.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = 1.0
    r = _math(nt, "MULTIPLY_ADD", noise.outputs["Fac"], 0.35)
    r.inputs[2].default_value = 0.22
    nt.links.new(r.outputs[0], bsdf.inputs["Roughness"])
    mat.diffuse_color = (0.1, 0.1, 0.12, 1.0)
    return mat


def phone_back():
    """Frosted-glass phone back; colour varies per phone."""
    mat, fresh = new_material("PhoneBack")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    info = nt.nodes.new("ShaderNodeObjectInfo")
    palette = _ramp(nt, [
        (0.00, (0.05, 0.05, 0.06)),   # graphite
        (0.25, (0.78, 0.78, 0.80)),   # silver
        (0.50, (0.10, 0.22, 0.45)),   # blue
        (0.75, (0.55, 0.40, 0.60)),   # lilac
    ], interpolation="CONSTANT")
    nt.links.new(info.outputs["Random"], palette.inputs[0])
    nt.links.new(palette.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.35
    _set(bsdf, "coat", 0.6)
    mat.diffuse_color = (0.3, 0.3, 0.35, 1.0)
    return mat


def phone_screen():
    """Glossy black glass with a faint lock-screen gradient glow."""
    mat, fresh = new_material("PhoneScreen")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    tex = nt.nodes.new("ShaderNodeTexCoord")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    nt.links.new(tex.outputs["Generated"], grad.inputs[0])
    ramp = _ramp(nt, [(0.0, (0.05, 0.02, 0.20)), (1.0, (0.00, 0.20, 0.30))])
    nt.links.new(grad.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], _input(bsdf, "emission"))
    bsdf.inputs["Emission Strength"].default_value = 0.6
    bsdf.inputs["Base Color"].default_value = (0.005, 0.005, 0.008, 1)
    bsdf.inputs["Roughness"].default_value = 0.05
    _set(bsdf, "coat", 1.0)
    return mat


# ---------------------------------------------------------------------------
# Target materials
# ---------------------------------------------------------------------------

def wood(name="Wood", light=(0.55, 0.33, 0.16), dark=(0.30, 0.15, 0.06), scale=1.0):
    """Warm wood: rings from a wave texture along X, plus fibre noise."""
    mat, fresh = new_material(name)
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    tex = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.6 * scale, 6.0 * scale, 6.0 * scale)
    nt.links.new(tex.outputs["Object"], mapping.inputs[0])
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "RINGS"
    wave.rings_direction = "X"
    wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 3.0
    nt.links.new(mapping.outputs[0], wave.inputs["Vector"])
    ramp = _ramp(nt, [(0.2, dark), (0.8, light)])
    nt.links.new(wave.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    _set(bsdf, "coat", 0.25)
    mat.diffuse_color = (*light, 1.0)
    return mat


def raw_wood():
    """Pale splintered interior of broken wood."""
    return principled("RawWood", color=(0.78, 0.60, 0.38), roughness=0.85)


def glass():
    """Slightly green, alpha-blended glass: cheap in Eevee, and it reads clearly on camera."""
    mat = principled("Glass", color=(0.62, 0.88, 0.86), roughness=0.03, specular=1.0,
                     coat=1.0, coat_roughness=0.0, alpha=0.26, ior=1.5)
    set_blended(mat)
    return mat


def glass_edge():
    """The green cut edge of float glass (shard interiors and the slab's sides)."""
    mat = principled("GlassEdge", color=(0.20, 0.62, 0.50), roughness=0.05, specular=1.0,
                     coat=1.0, alpha=0.9, ior=1.5)
    set_blended(mat)
    return mat


def chrome():
    return principled("Chrome", color=(0.85, 0.86, 0.88), roughness=0.12, metallic=1.0)


def black_metal():
    return principled("BlackMetal", color=(0.02, 0.02, 0.025), roughness=0.35, metallic=0.9)


def plastic(name, color, roughness=0.4):
    return principled(name, color=color, roughness=roughness, specular=0.5)


def eggshell():
    mat, fresh = new_material("EggShell")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 90.0
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    ramp = _ramp(nt, [(0.35, (0.80, 0.55, 0.36)), (0.7, (0.90, 0.68, 0.48))])
    nt.links.new(noise.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    _set(bsdf, "subsurface", 0.15)
    mat.diffuse_color = (0.88, 0.65, 0.45, 1.0)
    return mat


def yolk():
    return principled("Yolk", color=(1.0, 0.55, 0.02), roughness=0.15, specular=0.6, coat=0.8)


def egg_white():
    mat = principled("EggWhite", color=(0.95, 0.95, 0.9), roughness=0.05, coat=1.0, alpha=0.55)
    set_blended(mat)
    return mat


def trampoline_mat():
    """Woven black jumping mat with a subtle weave texture."""
    mat, fresh = new_material("JumpMat")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    tex = nt.nodes.new("ShaderNodeTexCoord")
    checker = nt.nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = 260.0
    checker.inputs["Color1"].default_value = (0.012, 0.012, 0.014, 1)
    checker.inputs["Color2"].default_value = (0.03, 0.03, 0.035, 1)
    nt.links.new(tex.outputs["Object"], checker.inputs["Vector"])
    nt.links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.7
    _set(bsdf, "sheen", 0.4)
    return mat


# ---------------------------------------------------------------------------
# Studio materials
# ---------------------------------------------------------------------------

def floor():
    """Dark slate lab floor with a faint 25 cm measurement grid."""
    mat, fresh = new_material("LabFloor")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Object"], sep.inputs[0])
    lines = []
    for axis in (0, 1):
        m = _math(nt, "MULTIPLY", sep.outputs[axis], 4.0)
        p = _math(nt, "PINGPONG", m.outputs[0], 0.5)
        lines.append(p)
    mn = _math(nt, "MINIMUM", lines[0].outputs[0], lines[1].outputs[0])
    line = _math(nt, "LESS_THAN", mn.outputs[0], 0.012)
    col = _mix_color(nt, line.outputs[0], (0.026, 0.028, 0.042), (0.06, 0.065, 0.095))
    nt.links.new(col.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    _set(bsdf, "specular", 0.3)
    mat.diffuse_color = (0.06, 0.06, 0.09, 1.0)
    return mat


def backdrop():
    """Cyclorama wall: fades from the floor colour up into deep indigo."""
    mat, fresh = new_material("Backdrop")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Object"], sep.inputs[0])
    norm = _math(nt, "DIVIDE", sep.outputs[2], 4.0, clamp=True)
    ramp = _ramp(nt, [(0.0, (0.026, 0.028, 0.042)), (0.25, (0.04, 0.04, 0.10)), (1.0, (0.012, 0.010, 0.035))])
    nt.links.new(norm.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    _set(bsdf, "specular", 0.2)
    return mat


def pad_top():
    return principled("PadTop", color=(0.075, 0.08, 0.095), roughness=0.5)


def hazard():
    """Yellow/black diagonal hazard stripes around the test pad's rim (signature look)."""
    mat, fresh = new_material("Hazard")
    if not fresh:
        return mat
    nt, bsdf = _principled_tree(mat)
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex.outputs["Object"], sep.inputs[0])
    ang = _math(nt, "ARCTAN2", sep.outputs[1], sep.outputs[0])
    a = _math(nt, "MULTIPLY", ang.outputs[0], 14.0)
    z = _math(nt, "MULTIPLY", sep.outputs[2], 60.0)
    s = _math(nt, "ADD", a.outputs[0], z.outputs[0])
    p = _math(nt, "PINGPONG", s.outputs[0], 1.0)
    stripe = _math(nt, "GREATER_THAN", p.outputs[0], 0.5)
    col = _mix_color(nt, stripe.outputs[0], (0.015, 0.015, 0.015), (1.0, 0.72, 0.02))
    nt.links.new(col.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.35
    return mat
