"""Procedural drop objects.

Each builder returns one mesh object centred on its bounding box, long side along X,
up along Z. It matches ``size_m`` in hmtb/catalog.py. The pile is made of linked
duplicates of this template.

To add an object: write ``def build_<key>():`` here and add ``<key>`` to the catalogue.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import materials as M
from .util import (box_bmesh, boolean_difference, cylinder_bmesh, mesh_from_bmesh,
                   new_object, set_smooth)


def _center_on_bounds(obj):
    me = obj.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    c = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
    me.transform(Matrix.Translation(-c))
    me.update()
    return obj


def build_bowling_ball():
    r = 0.109
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=r)
    me = mesh_from_bmesh("BowlingBall", bm, smooth=True)
    ball = new_object("BowlingBallTemplate", me)
    me.materials.append(M.bowling_ball())
    me.materials.append(M.principled("BallHole", color=(0.01, 0.01, 0.012), roughness=0.6))
    # Three finger holes: a thumb hole and two finger holes near the top.
    for (ax, ay, hr) in ((0.0, -0.040, 0.0125), (-0.017, 0.030, 0.0105), (0.017, 0.030, 0.0105)):
        bmc = cylinder_bmesh(hr, 0.12, segments=20, center=(0, 0, 0))
        cme = mesh_from_bmesh("hole", bmc)
        cutter = new_object("hole", cme)
        direction = Vector((ax, ay, r)).normalized()
        cutter.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
        cutter.location = direction * r
        bpy.context.view_layer.update()
        boolean_difference(ball, cutter)
    # Faces carved by the cutters sit inside the sphere: give them the dark hole material.
    me = ball.data
    for poly in me.polygons:
        if poly.center.length < r * 0.985:
            poly.material_index = 1
    set_smooth(me, True)
    return _center_on_bounds(ball)


def build_watermelon():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.15, 0.115, 0.115), verts=bm.verts)
    # Slightly flattened underside and a little lumpiness so it isn't a perfect ellipsoid.
    for v in bm.verts:
        v.co.z *= 1.0 - 0.06 * max(0.0, -v.co.z / 0.115)
        v.co *= 1.0 + 0.015 * math.sin(v.co.x * 40.0) * math.cos(v.co.y * 35.0)
    me = mesh_from_bmesh("Watermelon", bm, smooth=True)
    obj = new_object("WatermelonTemplate", me)
    me.materials.append(M.watermelon())
    return _center_on_bounds(obj)


def build_brick():
    bm = box_bmesh(0.215, 0.1025, 0.065)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.003, segments=2, affect="EDGES")
    me = mesh_from_bmesh("Brick", bm)
    obj = new_object("BrickTemplate", me)
    me.materials.append(M.brick())
    return _center_on_bounds(obj)


def build_iphone():
    lx, ly, lz = 0.1476, 0.0716, 0.0078
    bm = box_bmesh(lx, ly, lz)
    vertical = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > lz * 0.5]
    bmesh.ops.bevel(bm, geom=vertical, offset=0.0095, segments=6, affect="EDGES")
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.is_manifold], offset=0.0011, segments=2,
                    affect="EDGES", clamp_overlap=True)
    # Camera bump on the back.
    box_bmesh(0.034, 0.034, 0.0016, center=(lx / 2 - 0.026, ly / 2 - 0.022, -lz / 2 - 0.0008), bm=bm)
    for (dx, dy) in ((-0.008, -0.008), (0.008, 0.008), (-0.008, 0.008)):
        cylinder_bmesh(0.0062, 0.0016, segments=16,
                       center=(lx / 2 - 0.026 + dx, ly / 2 - 0.022 + dy, -lz / 2 - 0.0024), bm=bm)
    me = mesh_from_bmesh("Phone", bm)
    obj = new_object("PhoneTemplate", me)
    me.materials.append(M.principled("PhoneFrame", color=(0.75, 0.75, 0.78), roughness=0.2, metallic=1.0))
    me.materials.append(M.phone_screen())
    me.materials.append(M.phone_back())
    for poly in me.polygons:
        if poly.normal.z > 0.9 and poly.center.z > lz * 0.45:
            poly.material_index = 1
        elif poly.normal.z < -0.9 and poly.center.z < -lz * 0.45:
            poly.material_index = 2
    for poly in me.polygons:
        poly.use_smooth = abs(poly.normal.z) < 0.9
    return _center_on_bounds(obj)


def build_anvil():
    bm = bmesh.new()
    # Feet / base, waist, face block, heel. Heights stack from z = 0.
    box_bmesh(0.26, 0.135, 0.045, center=(0.0, 0, 0.0225), bm=bm)
    box_bmesh(0.20, 0.11, 0.025, center=(0.0, 0, 0.057), bm=bm)
    box_bmesh(0.13, 0.075, 0.07, center=(0.0, 0, 0.104), bm=bm)
    box_bmesh(0.30, 0.12, 0.055, center=(-0.01, 0, 0.1665), bm=bm)
    # Horn: a cone along +X, flattened on top to meet the face.
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.05, radius2=0.004, depth=0.16)
    rot = Matrix.Rotation(math.radians(90), 4, "Y")
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0.22, 0, 0.17)) @ rot, verts=res["verts"])
    for v in res["verts"]:
        v.co.z = min(v.co.z, 0.194)
        v.co.y *= 0.9
    me = mesh_from_bmesh("Anvil", bm)
    obj = new_object("AnvilTemplate", me)
    me.materials.append(M.iron())
    for poly in me.polygons:
        poly.use_smooth = False
    return _center_on_bounds(obj)


BUILDERS = {
    "bowling_ball": build_bowling_ball,
    "watermelon": build_watermelon,
    "brick": build_brick,
    "iphone": build_iphone,
    "anvil": build_anvil,
}


def build(key):
    if key not in BUILDERS:
        raise KeyError("No builder for drop object %r in scene3d/drop_objects.py" % key)
    obj = BUILDERS[key]()
    obj.hide_render = True
    obj.hide_viewport = True
    return obj
