"""Small bpy helpers: scene reset, mesh/object creation, fast keyframing.

Written to work on Blender 4.2 LTS and 5.x. Blender 4.4 moved F-curves into "layered"
actions (action -> slot -> channelbag), and 5.0 removed the old ``action.fcurves``.
``fcurves_of`` hides that difference.
"""

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

def reset_scene():
    """Start from an empty factory scene (no default cube, camera or light)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def link(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def new_object(name, mesh, collection=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    return link(obj, collection)


def empty(name, location=(0, 0, 0), collection=None):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    return link(obj, collection)


def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


# ---------------------------------------------------------------------------
# Meshes
# ---------------------------------------------------------------------------

def mesh_from_bmesh(name, bm, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        set_smooth(me, True)
    return me


def set_smooth(me, smooth=True):
    values = [smooth] * len(me.polygons)
    me.polygons.foreach_set("use_smooth", values)
    me.update()


def box_bmesh(sx, sy, sz, center=(0, 0, 0), bm=None):
    """Axis-aligned box of full size sx, sy, sz added to (or creating) a bmesh."""
    bm = bm or bmesh.new()
    res = bmesh.ops.create_cube(bm, size=1.0)
    m = Matrix.Translation(Vector(center)) @ Matrix.Diagonal((sx, sy, sz, 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=res["verts"])
    return bm


def cylinder_bmesh(radius, depth, segments=32, center=(0, 0, 0), bm=None, radius2=None):
    """Z-aligned cylinder (or cone with radius2) centred at ``center``."""
    bm = bm or bmesh.new()
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                                radius1=radius, radius2=radius if radius2 is None else radius2,
                                depth=depth)
    bmesh.ops.translate(bm, vec=Vector(center), verts=res["verts"])
    return bm


def transform_verts(bm, verts, matrix):
    bmesh.ops.transform(bm, matrix=matrix, verts=verts)


def bevel_all(bm, offset, segments=2):
    bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=offset, segments=segments,
                    affect="EDGES", profile=0.5, clamp_overlap=True)


def apply_modifiers(obj):
    """Bake the object's modifier stack into its mesh without bpy.ops (works headless)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def boolean_difference(obj, cutter):
    mod = obj.modifiers.new("bool", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    apply_modifiers(obj)
    bpy.data.objects.remove(cutter, do_unlink=True)


def join_meshes(name, objects):
    """Join several mesh objects (with identity parents) into one new object."""
    bm = bmesh.new()
    materials = []
    for o in objects:
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        bmesh.ops.transform(tmp, matrix=o.matrix_world, verts=tmp.verts)
        # Remap material indices into the joined list.
        remap = {}
        for i, slot_mat in enumerate(o.data.materials):
            if slot_mat not in materials:
                materials.append(slot_mat)
            remap[i] = materials.index(slot_mat)
        for f in tmp.faces:
            f.material_index = remap.get(f.material_index, 0)
        me_tmp = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me_tmp)
        tmp.free()
        bm.from_mesh(me_tmp)
        bpy.data.meshes.remove(me_tmp)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in materials:
        me.materials.append(m)
    for o in objects:
        bpy.data.objects.remove(o, do_unlink=True)
    return new_object(name, me)


def world_bounds(objects):
    """Axis-aligned world bounds of objects (min Vector, max Vector)."""
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objects:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

def fcurves_of(id_data):
    """All F-curves of an ID's active action (layered and legacy actions)."""
    ad = id_data.animation_data
    if ad is None or ad.action is None:
        return []
    act = ad.action
    if hasattr(act, "fcurves") and not hasattr(act, "layers"):
        return list(act.fcurves)
    try:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
        return list(cb.fcurves) if cb else []
    except (ImportError, AttributeError):
        return list(getattr(act, "fcurves", []))


def find_fcurve(id_data, data_path, index=0):
    for fc in fcurves_of(id_data):
        if fc.data_path == data_path and fc.array_index == index:
            return fc
    return None


def set_keys(owner, prop, frames, values, index=-1, interpolation="LINEAR", id_data=None):
    """Write many keyframes at once.

    ``owner`` is the struct holding ``prop`` (an object, ``obj.rigid_body``, a node socket,
    ...). ``index`` is the array index for vector properties (-1 for scalars). Values are
    written with ``foreach_set``, which is far faster than one ``keyframe_insert`` per key.
    """
    frames = list(frames)
    values = list(values)
    if not frames:
        return None
    kw = {"frame": frames[0]}
    if index >= 0:
        kw["index"] = index
    owner.keyframe_insert(prop, **kw)
    id_data = id_data or owner.id_data
    path = owner.path_from_id(prop)
    fc = find_fcurve(id_data, path, max(index, 0))
    if fc is None:
        raise RuntimeError("Could not find F-curve %s[%d]" % (path, index))
    fc.keyframe_points.clear()
    fc.keyframe_points.add(len(frames))
    co = np.empty(len(frames) * 2, dtype=np.float32)
    co[0::2] = frames
    co[1::2] = values
    fc.keyframe_points.foreach_set("co", co)
    for kp in fc.keyframe_points:
        kp.interpolation = interpolation
        kp.handle_left_type = "AUTO_CLAMPED"
        kp.handle_right_type = "AUTO_CLAMPED"
    fc.update()
    return fc


def compress_track(frames, values, tol=1e-6):
    """Drop keys that LINEAR interpolation reproduces exactly (holds and straight runs)."""
    f = np.asarray(frames)
    v = np.asarray(values, dtype=np.float64)
    if len(f) <= 2:
        return f.tolist(), v.tolist()
    keep = np.ones(len(f), dtype=bool)
    prev = v[:-2]
    nxt = v[2:]
    mid = v[1:-1]
    straight = np.abs((prev + nxt) * 0.5 - mid) < tol
    keep[1:-1] = ~straight
    return f[keep].tolist(), v[keep].tolist()


def set_track(owner, prop, frames, values, index=-1):
    """Keyframe a per-frame sampled track, compressed, with LINEAR interpolation."""
    f, v = compress_track(frames, values)
    return set_keys(owner, prop, f, v, index=index, interpolation="LINEAR")


def set_visibility(obj, visible_ranges, first_frame=0):
    """Keyframe hide_render so the object renders only in the given ranges.

    ``visible_ranges`` is a list of (start, end_exclusive) scene frames. CONSTANT keys.
    Viewport visibility is left alone: hidden-in-viewport objects drop out of the
    evaluated scene, which would also remove them from the physics simulation.
    """
    frames, values = [], []
    for a, b in visible_ranges:
        if not frames or a > first_frame - 1:
            frames.append(min(first_frame - 1, a - 1))
            values.append(1.0)
        frames += [a, b]
        values += [0.0, 1.0]
    set_keys(obj, "hide_render", frames, values, interpolation="CONSTANT")
