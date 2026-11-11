"""Cameras: automatic framing, the tension push-in, impact shake and the replay angle.

Framing is solved numerically: for a view direction, the camera distance and lens shift
are adjusted until the subject's bounding box projects into a target box on screen. That
box is the band between the top and bottom counters, left of TikTok's right-hand
buttons, so the action never sits under the UI or the counters, whatever the target's
size.
"""

import math

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from .util import fcurves_of, link

# Screen box for the subject, as fractions of the frame (x from left, y from bottom).
# The top counter ends ~22% down, the bottom counter starts ~69% down, and TikTok's
# buttons cover the right ~17%.
SUBJECT_BOX = (0.07, 0.80, 0.33, 0.755)


def make_camera(name, lens=50.0):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_fit = "AUTO"
    data.sensor_width = 36.0
    data.clip_start = 0.01
    data.clip_end = 200.0
    obj = bpy.data.objects.new(name, data)
    link(obj)
    return obj


def _corners(lo, hi):
    return [Vector((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]


def solve_framing(scene, cam, lo, hi, yaw_deg, pitch_deg, fill=1.0, box=SUBJECT_BOX):
    """Return (location, rotation, shift_x, shift_y) framing the box lo..hi.

    ``fill`` < 1 leaves breathing room (the subject uses ``fill`` of the screen box).
    """
    pts = _corners(lo, hi)
    center = (Vector(lo) + Vector(hi)) * 0.5
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    direction = Vector((math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch)))
    bx0, bx1, by0, by1 = box
    bw, bh = (bx1 - bx0) * fill, (by1 - by0) * fill
    bcx, bcy = (bx0 + bx1) / 2, (by0 + by1) / 2
    rx, ry = scene.render.resolution_x, scene.render.resolution_y
    big = float(max(rx, ry))
    dist = (Vector(hi) - Vector(lo)).length * 2.5
    cam.data.shift_x = 0.0
    cam.data.shift_y = 0.0
    rot = direction.to_track_quat("Z", "Y").to_euler()
    for _ in range(14):
        cam.location = center + direction * dist
        cam.rotation_euler = rot
        bpy.context.view_layer.update()
        proj = [world_to_camera_view(scene, cam, p) for p in pts]
        xs = [p.x for p in proj]
        ys = [p.y for p in proj]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        scale = max(w / bw, h / bh)
        dist *= scale ** 0.9
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        cam.data.shift_x += (cx - bcx) * (rx / big)
        cam.data.shift_y += (cy - bcy) * (ry / big)
    return cam.location.copy(), cam.rotation_euler.copy(), cam.data.shift_x, cam.data.shift_y


def key_framing(cam, frame, framing, interpolation="BEZIER"):
    loc, rot, sx, sy = framing
    cam.location = loc
    cam.rotation_euler = rot
    cam.data.shift_x = sx
    cam.data.shift_y = sy
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)
    cam.data.keyframe_insert("shift_x", frame=frame)
    cam.data.keyframe_insert("shift_y", frame=frame)


def _lerp_box(a, b, t):
    lo = [a[0][i] + (b[0][i] - a[0][i]) * t for i in range(3)]
    hi = [a[1][i] + (b[1][i] - a[1][i]) * t for i in range(3)]
    return lo, hi


def add_shake(cam, start, length, strength, scale=1.6):
    """Noise on the camera position/roll, restricted to [start, start + length]."""
    for fc in fcurves_of(cam):
        if fc.data_path not in ("location", "rotation_euler"):
            continue
        if fc.data_path == "location" and fc.array_index == 1:
            continue
        if fc.data_path == "rotation_euler" and fc.array_index != 1:
            continue
        mod = fc.modifiers.new("NOISE")
        mod.scale = scale
        mod.strength = strength * (0.08 if fc.data_path == "rotation_euler" else 1.0)
        mod.phase = (start * 0.37 + fc.array_index * 11.0) % 100.0
        mod.use_restricted_range = True
        mod.frame_start = start
        mod.frame_end = start + length
        mod.blend_in = 0.0
        mod.blend_out = length * 0.8


def animate_main(scene, cam, timeline, target_box, full_box, tight_box, debris_box, size):
    """Close on the empty target for the hook, ease out to fit the coming pile, push in
    at each crack stage, then pull back after the break to show the wreckage."""
    tl = timeline
    B = tl.break_f
    yaw0, yaw_b = -30.0, -18.0
    pitch = 17.0

    def yaw_at(f):
        return yaw0 + (yaw_b - yaw0) * min(1.0, f / float(B))

    first_impact = tl.drops[0].impact_f
    keys = [(0, target_box, 0.97), (tl.segments["intro"][1], target_box, 1.0),
            (first_impact + 45, full_box, 0.92)]
    stage_drops = [d for d in tl.drops if d.crack_stage]
    n_st = max(1, len(stage_drops))
    for d in stage_drops:
        t = d.crack_stage / float(n_st)
        keys.append((d.impact_f + 18, _lerp_box(full_box, tight_box, 0.55 * t), 0.93 + 0.07 * t))
    keys.append((B, _lerp_box(full_box, tight_box, 0.65), 1.0))
    for f, box, fill in keys:
        if f > B:
            continue
        key_framing(cam, f, solve_framing(scene, cam, box[0], box[1], yaw_at(f), pitch, fill))
    shatter_end = B + (tl.segments["shatter"][1] - tl.segments["shatter"][0])
    key_framing(cam, shatter_end, solve_framing(scene, cam, debris_box[0], debris_box[1], -14.0, 15.0, 0.92))
    key_framing(cam, tl.scene_end_f, solve_framing(scene, cam, debris_box[0], debris_box[1], -9.0, 15.5, 0.90))
    # Shakes: a big one at the break, small thumps at each crack stage.
    add_shake(cam, B, 26, 0.022 * size, scale=1.4)
    for d in stage_drops:
        add_shake(cam, d.impact_f, 9, 0.004 * size * (1 + d.crack_stage / n_st), scale=1.2)


def animate_replay(scene, cam, timeline, replay_box):
    """Low, side-on slow-motion angle of the break with a gentle dolly-in."""
    shot = next((s for s in timeline.shots if s.camera == "replay"), None)
    if shot is None:
        return
    start = shot.scene_start
    end = start + (shot.video_end - shot.video_start)
    cam.data.lens = 32.0
    key_framing(cam, start, solve_framing(scene, cam, replay_box[0], replay_box[1], 50.0, 5.0, 0.90))
    key_framing(cam, end, solve_framing(scene, cam, replay_box[0], replay_box[1], 42.0, 6.0, 1.0))
