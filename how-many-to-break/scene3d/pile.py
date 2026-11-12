"""Keyframed motion before the break: drops, bounces, settling, sag and crack growth.

Every pile object gets per-frame sampled tracks (location, rotation, scale) built from
simple analytic motions, which are then compressed into LINEAR keyframes:

* fall:   z = rest + H * (1 - u^2), gravity-like, landing exactly on its impact frame
* bounce: a small hop (bigger on a trampoline), then a tiny second hop
* rock:   damped wobble back to its resting orientation
* squash: soft objects (watermelons) squash and spring back
* sag:    everything already on the target sinks a little more with each impact, plus a
          damped "jolt" so the whole pile reacts to every hit

The objects are rigid-body "animated" (kinematic) objects, so they hand their motion to
the physics engine at the break frame. The last object keeps its falling speed.
"""

import math

import numpy as np

from .util import set_keys, set_track, set_visibility

FPS = 30.0
GRAVITY = 9.81
CARTOON_SQUASH = 0.09    # minimum landing squash for every non-round object
CARTOON_STRETCH = 0.10   # stretch along the fall just before landing


def sag_track(frames, drops, max_sag, jolt):
    """Support sink (metres, positive = down) at each frame."""
    frames = np.asarray(frames, dtype=np.float64)
    s = np.zeros_like(frames)
    n_total = len(drops)
    prev = 0.0
    for d in drops:
        level = max_sag * (d.n / float(n_total)) ** 0.75
        ds = level - prev
        prev = level
        t = frames - d.impact_f
        m = t >= 0
        tt = t[m]
        j = jolt * (1.8 if d.crack_stage else 1.0)
        s[m] += ds * (1.0 - np.exp(-tt / 4.0) * np.cos(2 * math.pi * tt / 9.0))
        s[m] += j * np.exp(-tt / 5.0) * np.sin(2 * math.pi * tt / 8.0)
    return s


def _profile(target, x, y):
    """How much of the centre sag applies at (x, y): 1 everywhere, or a bowl on a trampoline."""
    if target.sag_radius > 0:
        r = math.hypot(x - target.support["cx"], y - target.support["cy"])
        return max(0.0, 1.0 - (r / target.sag_radius) ** 2)
    return 1.0


def animate_pile(objs, positions, timeline, obj_info, target_info, target, rng, drop_height):
    """Keyframe every pile object from release to the break frame. Returns the sag track."""
    B = timeline.break_f
    all_frames = np.arange(0, B + 1)
    sag = sag_track(all_frames, timeline.drops, target_info["max_sag_m"], target.jolt_m)
    size_z = obj_info["size_m"][2]
    spherical = len(set(obj_info["size_m"])) == 1
    bounce_h = min(obj_info["bounce"] * drop_height * target_info["bounciness"], 0.3 * drop_height)
    tb = max(3.0, 2.0 * math.sqrt(2.0 * max(bounce_h, 1e-4) / GRAVITY) * FPS)
    rock = math.radians(obj_info["rock_deg"])
    # Cartoon squash and stretch. Balls are skipped: they land at random orientations,
    # and a squash along their local axis would point the wrong way.
    squash = 0.0 if spherical else max(obj_info["squash"], CARTOON_SQUASH)
    stretch = 0.0 if spherical else CARTOON_STRETCH

    # On a bowl-shaped sag (trampoline), an object resting in the pocket of four below
    # it sinks by the *average* of their sag, which for a quadratic bowl is a fixed
    # amount less than the bowl depth at its own position, per layer.
    layer_relief = 0.0
    if target.sag_radius > 0 and obj_info["shape"] == "ellipsoid":
        ax = obj_info["size_m"][0] + obj_info["gap_m"]
        ay = obj_info["size_m"][1] + obj_info["gap_m"]
        layer_relief = (ax * ax + ay * ay) / (4.0 * target.sag_radius ** 2)

    for obj, pos, d in zip(objs, positions, timeline.drops):
        f0 = d.release_f - 1
        fr = np.arange(f0, B + 1)
        n = len(fr)
        p = max(0.0, _profile(target, pos["x"], pos["y"]) - layer_relief * pos.get("layer", 0))
        sink = sag[np.clip(fr, 0, B)] * p
        fall_len = float(d.impact_f - d.release_f)

        # Resting orientation: balls land any way round, everything else keeps its yaw.
        if spherical:
            rest = (rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi), pos["yaw"])
        elif obj_info.get("flip", False) and rng.random() < 0.5:
            rest = (math.pi, 0.0, pos["yaw"])     # face-down, coloured back up
        else:
            rest = (0.0, 0.0, pos["yaw"])
        spin = rng.uniform(-1.2, 1.2)
        tilt0 = (rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)) if not spherical else (0.0, 0.0)
        drift = (rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04))
        rock_axis = rng.choice((0, 1))
        rock_sign = rng.choice((-1.0, 1.0))

        loc = np.zeros((n, 3))
        rot = np.zeros((n, 3))
        scl = np.ones((n, 3))
        u = np.clip((fr - d.release_f) / fall_len, 0.0, 1.0)
        falling = fr < d.impact_f
        t = np.maximum(fr - d.impact_f, 0).astype(np.float64)

        # Fall
        rem = 1.0 - u
        loc[:, 0] = pos["x"] + drift[0] * rem
        loc[:, 1] = pos["y"] + drift[1] * rem
        loc[:, 2] = pos["z"] - sink + drop_height * (1.0 - u * u)
        rot[:, 0] = rest[0] + tilt0[0] * rem
        rot[:, 1] = rest[1] + tilt0[1] * rem
        rot[:, 2] = rest[2] + spin * rem

        # Bounce (after impact)
        hop = np.where(t < tb, bounce_h * np.sin(np.pi * t / tb), 0.0)
        t2 = t - tb
        hop += np.where((t2 >= 0) & (t2 < 0.55 * tb), 0.22 * bounce_h * np.sin(np.pi * t2 / (0.55 * tb)), 0.0)
        hop[falling] = 0.0
        loc[:, 2] += hop

        # Rock back to rest
        if rock > 0:
            wobble = rock * rock_sign * np.exp(-t / 7.0) * np.sin(2 * np.pi * t / 11.0)
            wobble[falling] = 0.0
            rot[:, rock_axis] += wobble

        # Squash and stretch: stretch as it speeds up, squash on landing, spring back.
        if squash > 0:
            q = squash * np.exp(-t / 3.0) * np.cos(2 * np.pi * t / 9.0)
            q[falling | (t > 24)] = 0.0
            q -= np.where(falling, stretch * u ** 3, 0.0)     # negative q = stretch
            if d.final:
                q[~falling] = 0.0   # physics takes over on this frame: hand it over unsquashed
            scl[:, 2] = 1.0 - q
            scl[:, 0] = 1.0 + q * 0.5
            scl[:, 1] = 1.0 + q * 0.5
            loc[:, 2] -= np.where(falling, 0.0, q * size_z / 2.0)

        for axis in range(3):
            set_track(obj, "location", fr, loc[:, axis], index=axis)
            set_track(obj, "rotation_euler", fr, rot[:, axis], index=axis)
            if squash > 0:
                set_track(obj, "scale", fr, scl[:, axis], index=axis)
        set_visibility(obj, [(d.release_f, 10 ** 7)])
    return sag


def animate_support(target, sag, break_f):
    """Sink the support with the load: rigid parts move down, a trampoline mat bends,
    and a squashy target (the egg) squashes with its bottom planted."""
    frames = np.arange(0, break_f + 1)
    for obj in target.sag_move:
        z0 = obj.location.z
        set_track(obj, "location", frames, z0 - sag, index=2)
    for obj, height in target.sag_squash:
        z0 = obj.location.z
        k = sag / height
        set_track(obj, "location", frames, z0 - sag / 2.0, index=2)
        set_track(obj, "scale", frames, 1.0 - k, index=2)
        for axis in (0, 1):
            set_track(obj, "scale", frames, 1.0 + 0.5 * k, index=axis)
    for obj in target.sag_shape:
        key = obj.data.shape_keys.key_blocks["Sag"]
        set_track(key, "value", frames, np.clip(sag, 0.0, 1.0))


def animate_cracks(level_nodes, timeline, grow_frames=8):
    """Grow each crack stage outward over ``grow_frames`` from its impact."""
    keys = {0: 0.0}
    level = 0.0
    stage_drops = [d for d in timeline.drops if d.crack_stage]
    for i_d, d in enumerate(stage_drops):
        f = d.impact_f
        # Finish growing before the next stage starts, however close together they are.
        nxt = stage_drops[i_d + 1].impact_f if i_d + 1 < len(stage_drops) else f + 10 ** 6
        grow = max(1, min(grow_frames, nxt - f - 2))
        keys[f - 1] = level
        for i in range(grow + 1):
            e = 1.0 - (1.0 - i / float(grow)) ** 2
            keys[f + i] = d.crack_stage + e
        level = d.crack_stage + 1.0
    frames = sorted(keys)
    values = [keys[f] for f in frames]
    for node in level_nodes:
        set_keys(node.outputs[0], "default_value", frames, values, interpolation="LINEAR")


def animate_extras(target, break_f):
    """Effects that appear at the break, e.g. the yolk splat spreading under an egg."""
    for obj, kind in target.extras:
        if kind == "grow_after_break":
            frames = [break_f, break_f + 2, break_f + 50]
            for axis in range(3):
                vals = [0.001, 0.15, 1.0] if axis < 2 else [0.001, 0.5, 1.0]
                set_keys(obj, "scale", frames, vals, index=axis, interpolation="BEZIER")
            set_visibility(obj, [(break_f + 1, 10 ** 7)])
