"""Rigid-body shatter: physics takes over from the keyframes at the break frame.

Before the break, the pile objects are "animated" rigid bodies (they follow their
keyframes). Pre-fractured shards wait hidden in place of the intact target. On the break
frame the intact target disappears, the shards appear, and everything turns dynamic
together. The last object keeps its falling speed and smashes through. The world's time
scale is keyframed for the slow motion, so the cache needs no retiming.

After baking, every body's motion is scanned for sudden stops. Those become "debris"
sound events in the events log.
"""

import bmesh
import bpy
import numpy as np

from hmtb.timeline import time_scale_at

from .util import box_bmesh, mesh_from_bmesh, new_object, set_keys, set_visibility


def _add_body(obj, kind, shape, mass=1.0, friction=0.6, restitution=0.15, margin=0.0015):
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.rigidbody.object_add(type=kind)
    rb = obj.rigid_body
    rb.collision_shape = shape
    rb.friction = friction
    rb.restitution = restitution
    rb.use_margin = True
    rb.collision_margin = margin
    if kind == "ACTIVE":
        rb.mass = max(mass, 0.002)
        # Fairly high damping stands in for rolling friction, which Bullet lacks here,
        # so round objects come to rest near the target instead of rolling off-screen.
        rb.linear_damping = 0.15
        rb.angular_damping = 0.6
    if shape == "MESH":
        rb.mesh_source = "BASE"
    return rb


def _kinematic_until(obj, frame):
    """Follow keyframes up to ``frame - 1``, simulate from ``frame`` on."""
    set_keys(obj.rigid_body, "kinematic", [frame - 1, frame], [1.0, 0.0], interpolation="CONSTANT",
             id_data=obj)


def setup(scene, timeline, pile_objs, obj_info, cfg, target, shards, cache_pad=2):
    """Create the rigid-body world and all bodies. Returns the list of dynamic bodies."""
    B = timeline.break_f
    with bpy.context.temp_override(scene=scene):
        bpy.ops.rigidbody.world_add()
    rbw = scene.rigidbody_world
    for attr, value in (("substeps_per_frame", 12), ("steps_per_second", 360), ("solver_iterations", 25)):
        if hasattr(rbw, attr):
            setattr(rbw, attr, value)
    rbw.point_cache.frame_start = B - cache_pad
    rbw.point_cache.frame_end = timeline.scene_end_f + 1

    # Slow motion: physics time scale keyed per frame through the shatter.
    frames = list(range(B - cache_pad, timeline.scene_end_f + 2))
    values = [time_scale_at(timeline, f) for f in frames]
    set_keys(rbw, "time_scale", frames, values, interpolation="LINEAR", id_data=scene)

    # Ground: an invisible box under the floor, plus the test pad.
    ground = new_object("GroundCollider", mesh_from_bmesh("GroundCollider", box_bmesh(40, 40, 1.0)),
                        location=(0, 0, -0.5))
    ground.hide_render = True
    _add_body(ground, "PASSIVE", "BOX", friction=0.8, restitution=0.2)
    pad = bpy.data.objects.get("TestPad")
    if pad is not None:
        _add_body(pad, "PASSIVE", "CONVEX_HULL", friction=0.8, restitution=0.2, margin=0.001)

    for obj in target.passive_after:
        _add_body(obj, "PASSIVE", "MESH", friction=0.7, restitution=0.1, margin=0.001)

    dynamic = []
    mass = float(cfg["drop_mass_kg"])
    shape = obj_info["collision"]
    small = min(obj_info["size_m"])
    for obj in pile_objs:
        _add_body(obj, "ACTIVE", shape, mass=mass, friction=0.55, restitution=0.2,
                  margin=min(0.002, small * 0.08))
        _kinematic_until(obj, B)
        dynamic.append((obj, mass, "object"))

    for obj in target.dynamic_after:
        vol = _volume(obj)
        _add_body(obj, "ACTIVE", "CONVEX_HULL", mass=vol * 900.0, friction=0.6, restitution=0.1)
        _kinematic_until(obj, B)
        dynamic.append((obj, vol * 900.0, "part"))

    for shard, vol, density in shards:
        m = vol * density
        _add_body(shard, "ACTIVE", "CONVEX_HULL", mass=m, friction=0.6, restitution=0.12, margin=0.0008)
        _kinematic_until(shard, B)
        set_visibility(shard, [(B, 10 ** 7)])
        dynamic.append((shard, m, "shard"))
    return dynamic


def _volume(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    v = abs(bm.calc_volume())
    bm.free()
    return max(v, 1e-6)


def bake(scene):
    with bpy.context.temp_override(scene=scene):
        bpy.ops.ptcache.bake_all(bake=True)


def debris_events(scene, timeline, dynamic, max_events=70):
    """Scan the baked sim for impacts. Returns [(scene_frame, intensity, kind, x)]."""
    B = timeline.break_f
    frames = list(range(B - 1, timeline.scene_end_f + 1))
    pos = np.zeros((len(frames), len(dynamic), 3))
    for i, f in enumerate(frames):
        scene.frame_set(f)
        for j, (obj, _m, _k) in enumerate(dynamic):
            pos[i, j] = obj.matrix_world.translation
    dt = np.array([time_scale_at(timeline, f) / 30.0 for f in frames[1:]])
    vel = np.diff(pos, axis=0) / np.maximum(dt[:, None, None], 1e-4)
    vz = vel[..., 2]
    speed = np.linalg.norm(vel, axis=2)
    masses = np.array([m for (_o, m, _k) in dynamic])
    events = []
    for i in range(1, len(vz)):
        drop = speed[i - 1] - speed[i]
        hit = (vz[i - 1] < -0.5) & (drop > 0.5 * np.maximum(speed[i - 1], 1e-3))
        for j in np.nonzero(hit)[0]:
            intensity = float(masses[j] * drop[j])
            events.append((frames[i + 1], intensity, dynamic[j][2], float(pos[i + 1, j, 0])))
    # Merge hits of the same kind within two frames, keep the loudest.
    events.sort()
    merged = []
    for e in events:
        if merged and merged[-1][2] == e[2] and e[0] - merged[-1][0] <= 2:
            prev = merged[-1]
            merged[-1] = (prev[0], prev[1] + e[1], prev[2], prev[3])
        else:
            merged.append(e)
    merged.sort(key=lambda e: -e[1])
    return sorted(merged[:max_events])
