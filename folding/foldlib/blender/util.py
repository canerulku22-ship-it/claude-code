"""Helpers for building meshes and shader node trees from Python.

Written against Blender 4.0 and kept tolerant of newer releases: socket and
property names that changed between versions are looked up by trying the
alternatives.
"""

import bmesh
import bpy

from ..mathutil import hex_to_linear


def safe_set(obj, attr, value):
    """Set an attribute if this Blender version has it (settings move around)."""
    if hasattr(obj, attr):
        try:
            setattr(obj, attr, value)
            return True
        except (TypeError, ValueError, AttributeError):
            pass
    return False


def link_object(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def new_object(name, data=None, parent=None):
    obj = bpy.data.objects.new(name, data)
    link_object(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def mesh_from_bmesh(name, bm, smooth=False):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.update()
    return mesh


def mesh_from_data(name, verts, faces, smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    if smooth:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.update()
    return mesh


# --- Primitive builders (all return bmesh objects, sizes in metres) ----------

def bm_box(sx, sy, sz, origin_bottom=True, offset=(0, 0, 0)):
    """Axis-aligned box sx*sy*sz; origin at the bottom centre unless told otherwise."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = v.co.x * sx + offset[0]
        v.co.y = v.co.y * sy + offset[1]
        v.co.z = v.co.z * sz + (sz / 2 if origin_bottom else 0) + offset[2]
    return bm


def add_box(bm, sx, sy, sz, cx=0.0, cy=0.0, z0=0.0):
    """Append a box (bottom at z0) to an existing bmesh."""
    tmp = bm_box(sx, sy, sz, True, (cx, cy, z0))
    _merge(bm, tmp)


def add_cylinder(bm, r_bottom, r_top, height, cx=0.0, cy=0.0, z0=0.0, segments=24,
                 rotate_z=0.0):
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=r_bottom, radius2=r_top, depth=height)
    import math
    c, s = math.cos(rotate_z), math.sin(rotate_z)
    for v in tmp.verts:
        x, y = v.co.x, v.co.y
        v.co.x = x * c - y * s + cx
        v.co.y = x * s + y * c + cy
        v.co.z = v.co.z + height / 2 + z0
    _merge(bm, tmp)


def add_sphere(bm, radius, cx=0.0, cy=0.0, cz=0.0, segments=24, rings=12, scale=(1, 1, 1)):
    tmp = bmesh.new()
    bmesh.ops.create_uvsphere(tmp, u_segments=segments, v_segments=rings, radius=radius)
    for v in tmp.verts:
        v.co.x = v.co.x * scale[0] + cx
        v.co.y = v.co.y * scale[1] + cy
        v.co.z = v.co.z * scale[2] + cz
    _merge(bm, tmp)


def _merge(dst, src):
    """Copy all geometry of bmesh `src` into `dst` (then free src)."""
    mesh = bpy.data.meshes.new("_tmp")
    src.to_mesh(mesh)
    src.free()
    dst.from_mesh(mesh)
    bpy.data.meshes.remove(mesh)


# --- Shader nodes ------------------------------------------------------------

class Nodes:
    """Tiny DSL for building node trees: arguments can be sockets or numbers."""

    def __init__(self, tree):
        self.tree = tree
        self.nodes = tree.nodes
        self.links = tree.links

    def clear(self):
        self.nodes.clear()

    def new(self, kind, name=None, **props):
        node = self.nodes.new(kind)
        if name:
            node.name = node.label = name
        for k, v in props.items():
            setattr(node, k, v)
        return node

    def feed(self, socket, value):
        if isinstance(value, bpy.types.NodeSocket):
            self.links.new(value, socket)
        elif value is not None:
            socket.default_value = value

    def value(self, v, name):
        node = self.new("ShaderNodeValue", name)
        node.outputs[0].default_value = v
        return node.outputs[0]

    def rgb(self, colour, name):
        node = self.new("ShaderNodeRGB", name)
        node.outputs[0].default_value = colour if len(colour) == 4 else tuple(colour) + (1.0,)
        return node.outputs[0]

    def math(self, op, a, b=None, clamp=False):
        node = self.new("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.feed(node.inputs[0], a)
        if b is not None:
            self.feed(node.inputs[1], b)
        return node.outputs[0]

    def map_range(self, x, a, b, c=0.0, d=1.0, smooth=True):
        node = self.new("ShaderNodeMapRange")
        node.interpolation_type = "SMOOTHSTEP" if smooth else "LINEAR"
        node.clamp = True
        for i, v in enumerate((x, a, b, c, d)):
            self.feed(node.inputs[i], v)
        return node.outputs[0]

    def mix(self, fac, a, b):
        """Colour mix (factor 0 -> a, 1 -> b)."""
        node = self.new("ShaderNodeMix")
        node.data_type = "RGBA"
        node.clamp_factor = True
        self.feed(node.inputs[0], fac)
        self.feed(node.inputs[6], a)
        self.feed(node.inputs[7], b)
        return node.outputs[2]

    def separate(self, vec):
        node = self.new("ShaderNodeSeparateXYZ")
        self.feed(node.inputs[0], vec)
        return node.outputs

    def link(self, a, b):
        self.links.new(a, b)


def set_input(node, names, value):
    """Set the first input that exists out of several possible names."""
    for name in names if isinstance(names, (list, tuple)) else (names,):
        if name in node.inputs:
            sock = node.inputs[name]
            if isinstance(value, bpy.types.NodeSocket):
                node.id_data.links.new(value, sock)
            else:
                sock.default_value = value
            return sock
    return None


def principled_material(name, colour_hex=None, roughness=0.6, metallic=0.0, specular=0.4,
                        emission_hex=None, emission_strength=0.0, colour=None):
    """A plain Principled BSDF material; returns (material, Nodes, bsdf node)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nb = Nodes(mat.node_tree)
    nb.clear()
    out = nb.new("ShaderNodeOutputMaterial")
    bsdf = nb.new("ShaderNodeBsdfPrincipled")
    nb.link(bsdf.outputs[0], out.inputs["Surface"])
    base = colour if colour is not None else hex_to_linear(colour_hex or "#cccccc")
    set_input(bsdf, "Base Color", tuple(base[:3]) + (1.0,))
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, ["Specular IOR Level", "Specular"], specular)
    if emission_hex:
        set_input(bsdf, ["Emission Color", "Emission"], hex_to_linear(emission_hex, 1.0))
        set_input(bsdf, "Emission Strength", emission_strength)
    return mat, nb, bsdf


def set_blend_mode(mat, mode):
    """'OPAQUE', 'BLEND' (alpha) or 'ADD'-like via blend; tolerant of 4.2+ API."""
    if mode == "BLEND":
        safe_set(mat, "blend_method", "BLEND")
        safe_set(mat, "surface_render_method", "BLENDED")
        safe_set(mat, "shadow_method", "NONE")
        safe_set(mat, "show_transparent_back", False)
    else:
        safe_set(mat, "blend_method", "OPAQUE")


def assign(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
