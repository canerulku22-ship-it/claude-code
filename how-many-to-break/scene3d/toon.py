"""Cartoon outlines (the "inverted hull" trick), cheap enough for Eevee on a CPU.

Each outlined object gets a Solidify modifier that grows a slightly larger shell with
flipped normals and a flat ink material. With backface culling, only the rim of the
shell peeks out around the object, which draws a clean outline that follows motion and
squash. The shell isn't part of any physics collision shape.
"""

import bpy

INK = (0.012, 0.012, 0.022)


def ink_material():
    mat = bpy.data.materials.get("OutlineInk")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("OutlineInk")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*INK, 1.0)
    em.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    mat.use_backface_culling = True
    if hasattr(mat, "use_backface_culling_shadow"):
        mat.use_backface_culling_shadow = True
    mat.diffuse_color = (*INK, 1.0)
    return mat


def add_outline(obj, thickness):
    """Outline one mesh object. Linked duplicates share the material slot."""
    if obj.type != "MESH" or obj.modifiers.get("Outline"):
        return
    me = obj.data
    ink = ink_material()
    if ink.name not in [m.name for m in me.materials if m]:
        me.materials.append(ink)
    idx = [m.name if m else "" for m in me.materials].index(ink.name)
    dims = sorted(obj.dimensions)
    t = min(thickness, 0.3 * dims[0]) if dims[0] > 0 else thickness
    mod = obj.modifiers.new("Outline", "SOLIDIFY")
    mod.thickness = t
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_even_offset = True
    mod.use_rim = False
    # Shell faces get index + idx; the ink is the last slot, so everything clamps to it.
    mod.material_offset = idx


def outline_scene(objects, scene_size):
    """Outline every given object with a thickness that reads the same at any scale."""
    thickness = 0.0032 * scene_size
    for obj in objects:
        add_outline(obj, thickness)
