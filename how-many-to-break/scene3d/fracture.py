"""Scripted Voronoi fracture (no add-on needed).

Each shard is the source mesh clipped by the bisector planes between its seed point and
every other seed. Cut faces get the "interior" material (green glass edge, raw wood,
yolk...). A ``metric`` stretches the distance per axis. For example (0.3, 1, 1) makes
cells long along X, which gives wood its splinters, and the bisectors stay planes.

Crack UVs are recomputed on every shard from the same projection as the intact object,
so cracks line up perfectly at the moment of the swap.
"""

import math

import bmesh
import bpy
from mathutils import Vector

from .cracks import set_crack_uv
from .util import new_object


def radial_seeds(rng, count, center, radius, z=0.0, bias=1.6, z_jitter=0.0):
    """Seeds clustered towards ``center`` (``bias`` > 1 gives smaller shards in the middle)."""
    seeds = []
    for _ in range(count):
        r = radius * (rng.random() ** bias)
        a = rng.uniform(0, 6.283185307)
        seeds.append(Vector((center[0] + r * math.cos(a),
                             center[1] + r * math.sin(a),
                             z + rng.uniform(-z_jitter, z_jitter))))
    return seeds


def box_seeds(rng, count, lo, hi):
    return [Vector((rng.uniform(lo[0], hi[0]), rng.uniform(lo[1], hi[1]), rng.uniform(lo[2], hi[2])))
            for _ in range(count)]


def fracture(obj, seeds, interior_index, name, uv_func=None, metric=(1.0, 1.0, 1.0),
             deform=None, min_verts=4):
    """Split ``obj`` into Voronoi shards. Returns a list of (shard_object, volume_m3).

    ``seeds`` are in the object's local space. ``deform(bm)`` optionally edits the source
    mesh first (used to fracture the trampoline mat in its sagged shape). The source
    object must have no rotation or scale.
    """
    src = bmesh.new()
    src.from_mesh(obj.data)
    if deform is not None:
        deform(src)
    src_me = bpy.data.meshes.new(name + "_src")
    src.to_mesh(src_me)
    src.free()

    m2 = Vector((metric[0] ** 2, metric[1] ** 2, metric[2] ** 2))
    shards = []
    for i, si in enumerate(seeds):
        bm = bmesh.new()
        bm.from_mesh(src_me)
        for j, sj in enumerate(seeds):
            if i == j or not bm.verts:
                continue
            d = sj - si
            normal = Vector((d.x * m2.x, d.y * m2.y, d.z * m2.z))
            if normal.length < 1e-9:
                continue
            mid = (si + sj) * 0.5
            # Skip planes that don't touch the current cell.
            if max((v.co - mid).dot(normal) for v in bm.verts) <= 1e-9:
                continue
            geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-7, plane_co=mid, plane_no=normal,
                                   clear_outer=True)
            boundary = [e for e in bm.edges if e.is_boundary]
            if boundary:
                res = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
                for f in res["faces"]:
                    f.material_index = interior_index
        if len(bm.verts) < min_verts:
            bm.free()
            continue
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        volume = abs(bm.calc_volume(signed=False))
        if volume < 1e-9:
            bm.free()
            continue
        me = bpy.data.meshes.new("%s_%02d" % (name, i))
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        if uv_func is not None:
            set_crack_uv(me, uv_func)
        # Move the origin to the shard's centre so it tumbles naturally.
        centre = sum((v.co for v in me.vertices), Vector()) / len(me.vertices)
        for v in me.vertices:
            v.co -= centre
        for p in me.polygons:
            p.use_smooth = False
        shard = new_object(me.name, me)
        shard.location = obj.matrix_world @ centre
        shards.append((shard, volume))
    bpy.data.meshes.remove(src_me)
    return shards
