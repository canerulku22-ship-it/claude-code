"""Render one episode's 3D frames with Blender (Eevee), headless.

    blender -b -P render.py -- --config episodes/bowling_balls_glass_table.json [--preview]

or, with Blender installed as the ``bpy`` Python module:

    python render.py --config episodes/bowling_balls_glass_table.json [--preview]

Writes to ``out/<slug>/`` (``out/<slug>_preview/`` with --preview):

    frames/00000.png ...   one PNG per video frame (frozen outro frames are hard links)
    events.json            timeline + sound/overlay events, read by make_episode.py

This script never needs a .blend file: the whole scene is rebuilt from the config on
every run. Already-rendered frames are kept, so an interrupted render resumes where it
stopped (use --fresh to start over).
"""

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402

from hmtb import FPS, FULL_RES, PREVIEW_RES, PREVIEW_SECONDS, catalog  # noqa: E402
from hmtb.config import load_config  # noqa: E402
from hmtb.stacking import pile_bounds, pile_positions  # noqa: E402
from hmtb.timeline import build_timeline, describe  # noqa: E402
from scene3d import camera, cracks, drop_objects, fracture, physics, pile, studio, targets, toon  # noqa: E402
from scene3d.util import reset_scene, set_visibility, world_bounds  # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True, help="episode JSON file")
    p.add_argument("--preview", action="store_true",
                   help="540x960, low samples, first %d seconds only" % PREVIEW_SECONDS)
    p.add_argument("--out", help="output folder (default out/<slug> or out/<slug>_preview)")
    p.add_argument("--samples", type=int, help="override Eevee render samples")
    p.add_argument("--scale", type=float, default=1.0,
                   help="render the 3D at this fraction of the output size (it is upscaled later)")
    p.add_argument("--frames", help="only render video frames A:B, or a list like 0,300,1575")
    p.add_argument("--fresh", action="store_true", help="delete existing frames first")
    p.add_argument("--no-render", action="store_true", help="build, bake and write events.json only")
    return p.parse_args(argv)


def build_scene(cfg, tl, width, height, samples, need_physics):
    """Build the whole episode scene. Returns a dict of the pieces render/events need."""
    scene = reset_scene()
    scene.frame_start = 0
    scene.frame_end = tl.scene_end_f
    studio.setup_render(scene, width, height, samples, cfg["motion_blur"])
    studio.setup_world(scene)
    rng = random.Random(cfg["seed"])

    obj_info = catalog.drop_object(cfg["drop_object"])
    tgt_info = catalog.target(cfg["target"])
    target = targets.build(cfg["target"], rng)

    # --- Pile ----------------------------------------------------------------
    template = drop_objects.build(cfg["drop_object"])
    n = cfg["break_at"]
    positions = pile_positions(obj_info, target.support, n, seed=cfg["seed"])
    pile_col = bpy.data.collections.new("Pile")
    scene.collection.children.link(pile_col)
    pile_objs = []
    for i in range(n):
        o = bpy.data.objects.new("%s_%02d" % (cfg["drop_object"], i + 1), template.data)
        pile_col.objects.link(o)
        pile_objs.append(o)

    # --- Sizes used for framing, lighting and drop height ---------------------
    t_lo, t_hi = world_bounds(target.frame_objects)
    p_lo, p_hi = pile_bounds(obj_info, positions)
    full_lo = [min(t_lo[i], p_lo[i]) for i in range(3)]
    full_hi = [max(t_hi[i], p_hi[i]) for i in range(3)]
    full_lo[2] = 0.0
    size = max(full_hi[0] - full_lo[0], full_hi[1] - full_lo[1], full_hi[2] - full_lo[2])
    sup = target.support
    sr = sup["r"] if sup["shape"] == "circle" else max(sup["sx"], sup["sy"]) / 2
    tight_lo = [sup["cx"] - sr, sup["cy"] - sr, sup["z"] - 0.15 * size]
    tight_hi = [sup["cx"] + sr, sup["cy"] + sr, max(p_hi[2], sup["z"] + 0.1 * size)]
    if target.tight_box:
        tight_lo, tight_hi = [list(v) for v in target.tight_box]
    spread = target.pad_radius * 0.95
    debris_lo = [-spread, -spread, 0.0]
    debris_hi = [spread, spread, max(t_hi[2], sup["z"] + 0.05)]
    replay_lo = [tight_lo[0], tight_lo[1], 0.0]
    replay_hi = tight_hi

    studio.build_cyclorama(max(size, 0.5))
    studio.build_pad(target.pad_radius)
    center = Vector(((full_lo[0] + full_hi[0]) / 2, (full_lo[1] + full_hi[1]) / 2, (full_lo[2] + full_hi[2]) / 2))
    studio.build_lights(center, size)

    # Objects fall from above the top of the frame.
    drop_height = max(1.2, 1.9 * (full_hi[2] - full_lo[2]))

    # --- Animation -----------------------------------------------------------
    sag = pile.animate_pile(pile_objs, positions, tl, obj_info, tgt_info, target, rng, drop_height)
    pile.animate_support(target, sag, tl.break_f)
    levels = []
    for obj, style, origin in target.crack_parts:
        mat = obj.data.materials[0]
        levels.append(cracks.add_crack_layer(mat, style, origin, len(cfg["crack_stages"]),
                                             seed=cfg["seed"] * 31 + 7, width_mult=target.crack_width))
    pile.animate_cracks(levels, tl)
    pile.animate_extras(target, tl.break_f)

    main_cam = camera.make_camera("MainCam", lens=50.0)
    replay_cam = camera.make_camera("ReplayCam", lens=32.0)
    close_cam = camera.make_camera("CloseCam", lens=40.0)
    scene.camera = main_cam
    target_lo = [t_lo[0], t_lo[1], 0.0]
    camera.animate_main(scene, main_cam, tl, (target_lo, list(t_hi)), (full_lo, full_hi), (tight_lo, tight_hi),
                        (debris_lo, debris_hi), size)
    camera.animate_replay(scene, replay_cam, tl, (replay_lo, replay_hi))
    if target.close_box:
        close_lo, close_hi = [list(v) for v in target.close_box]
    else:
        c_lo, c_hi = world_bounds([part for part, _style, _o in target.crack_parts])
        close_lo = [c_lo[0], c_lo[1], c_lo[2] - 0.05 * size]
        close_hi = [c_hi[0], c_hi[1], c_hi[2] + 0.25 * size]
    camera.animate_close(scene, close_cam, tl, (close_lo, close_hi), yaw=target.close_yaw)

    # Zoom punches: a small one on every impact, bigger at crack stages and the break.
    B = tl.break_f
    hits = [(d.impact_f, 0.10 if d.final else (0.06 if d.crack_stage else 0.025)) for d in tl.drops]
    camera.add_zoom_punches(main_cam, hits, (0, tl.scene_end_f))
    camera.add_zoom_punches(close_cam, [(d.impact_f, 0.08) for d in tl.drops if d.crack_stage], (0, B))
    camera.add_zoom_punches(replay_cam, [(B, 0.08)], (0, tl.scene_end_f))

    # --- Shatter ---------------------------------------------------------------
    dynamic = []
    if need_physics:
        B = tl.break_f
        sag_b = float(sag[-1])
        shards = []
        for brk in target.breakables:
            deform = None
            squash_h = dict((id(o), h) for o, h in target.sag_squash).get(id(brk.obj))
            if brk.sag_radius > 0:
                def deform(bm, r=brk.sag_radius, s=sag_b):
                    for v in bm.verts:
                        d = math.hypot(v.co.x, v.co.y)
                        v.co.z -= s * max(0.0, 1.0 - (d / r) ** 2)
            elif squash_h:
                # Fracture the egg in its squashed shape (same maths as animate_support).
                def deform(bm, h=squash_h, s=sag_b):
                    for v in bm.verts:
                        v.co.z = v.co.z * (1.0 - s / h) - s / 2.0
                        v.co.x *= 1.0 + 0.5 * s / h
                        v.co.y *= 1.0 + 0.5 * s / h
            pieces = fracture.fracture(brk.obj, brk.seeds, brk.interior_index, brk.obj.name + "_shard",
                                       uv_func=brk.uv_func, metric=brk.metric, deform=deform)
            if brk.obj in target.sag_move:
                for shard, _vol in pieces:
                    shard.location.z -= sag_b
            shards += [(shard, vol, brk.density) for shard, vol in pieces]
            set_visibility(brk.obj, [(-10, B)])
        dynamic = physics.setup(scene, tl, pile_objs, obj_info, cfg, target, shards)
        print("Baking physics (%d bodies, frames %d-%d)..." % (len(dynamic), B, tl.scene_end_f), flush=True)
        t0 = time.time()
        physics.bake(scene)
        print("  baked in %.1fs" % (time.time() - t0), flush=True)

    studio.no_transparent_shadows()    # after fracturing, so glass shards are included

    # Cartoon outlines on everything except the studio walls, colliders and splats.
    skip = {"Cyclorama", "GroundCollider"} | {o.name for o, _k in target.extras} | {template.name}
    toon.outline_scene([o for o in scene.objects if o.type == "MESH" and o.name not in skip], size)

    return {
        "scene": scene, "cams": {"main": main_cam, "replay": replay_cam, "close": close_cam},
        "pile": pile_objs, "obj_info": obj_info,
        "positions": positions, "dynamic": dynamic, "size": size, "center": center,
    }


def build_events(cfg, tl, built, preview):
    """Everything the overlay and audio stages need, in video frames."""
    obj_info = catalog.drop_object(cfg["drop_object"])
    tgt_info = catalog.target(cfg["target"])
    rng = random.Random(cfg["seed"] + 99)
    size = built["size"]
    n_total = len(tl.drops)
    first_stage = cfg["crack_stages"][0] if cfg["crack_stages"] else n_total

    def pan(x):
        return max(-0.8, min(0.8, (x - built["center"].x) / (0.6 * size)))

    # Where each impact lands on screen (for the overlay's starbursts), using whichever
    # camera is live at that moment.
    scene = built["scene"]
    half_z = obj_info["size_m"][2] / 2.0

    def screen_at(video_f, obj):
        sf, cam = tl.scene_frame(video_f)
        scene.frame_set(sf)
        w = obj.matrix_world.translation.copy()
        w.z -= half_z
        p = world_to_camera_view(scene, built["cams"][cam], w)
        return [round(p.x, 4), round(1.0 - p.y, 4)]

    scene_events = []   # in scene frames; mapped to video frames below
    for d, pos, obj in zip(tl.drops, built["positions"], built["pile"]):
        scene_events.append({"type": "whoosh", "frame": d.release_f + 3, "count": d.n,
                             "intensity": 0.5 + 0.5 * d.n / n_total})
        scene_events.append({"type": "impact", "frame": d.impact_f, "count": d.n, "sound": obj_info["sound"],
                             "intensity": 0.55 + 0.45 * d.n / n_total, "pan": pan(pos["x"]),
                             "final": d.final, "screen": screen_at(d.impact_f, obj)})
        if d.crack_stage:
            k = d.crack_stage / float(len(cfg["crack_stages"]))
            scene_events.append({"type": "crack", "frame": d.impact_f + 1, "stage": d.crack_stage,
                                 "material": tgt_info["material"], "intensity": 0.5 + 0.5 * k})
            scene_events.append({"type": "creak", "frame": d.impact_f + 4, "stage": d.crack_stage,
                                 "material": tgt_info["material"], "intensity": 0.5 + 0.5 * k})
        elif d.n > first_stage and not d.final and rng.random() < 0.4:
            scene_events.append({"type": "creak", "frame": d.impact_f + 3, "stage": 0,
                                 "material": tgt_info["material"], "intensity": 0.25})
    scene_events.append({"type": "break", "frame": tl.break_f, "material": tgt_info["material"],
                         "intensity": 1.0})
    for (f, intensity, kind, x) in built.get("debris", []):
        scene_events.append({"type": "debris", "frame": f, "kind": kind, "intensity": intensity,
                             "material": tgt_info["material"] if kind == "shard" else obj_info["sound"],
                             "pan": pan(x)})

    # Map scene frames to video frames: main-camera shots play straight through, the
    # replay re-plays scene frames around the break.
    events = []
    for shot in tl.shots:
        if shot.hold:
            continue
        s0 = shot.scene_start
        s1 = s0 + (shot.video_end - shot.video_start)
        for e in scene_events:
            if s0 <= e["frame"] < s1:
                v = dict(e)
                v["frame"] = shot.video_start + (e["frame"] - s0)
                v["time_s"] = round(v["frame"] / float(tl.fps), 4)
                v["slowmo"] = tl.slowmo["start_f"] < e["frame"] <= tl.slowmo["ramp_end_f"]
                if shot.camera == "replay":
                    v["replay"] = True
                events.append(v)
    events.append({"type": "replay_start", "frame": tl.segments["replay"][0]})
    events.append({"type": "outro_start", "frame": tl.segments["outro"][0]})
    events.sort(key=lambda e: e["frame"])

    counter = [{"frame": d.impact_f, "count": d.n, "weight_kg": round(d.n * cfg["drop_mass_kg"], 3),
                "crack_stage": d.crack_stage} for d in tl.drops]
    public_cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
    return {
        "version": 1,
        "config": public_cfg,
        "fps": tl.fps,
        "total_frames": tl.total_frames,
        "duration_s": tl.total_frames / float(tl.fps),
        "preview": preview,
        "break_frame": tl.break_f,
        "interval_scale": round(tl.interval_scale, 4),
        "segments": tl.segments,
        "counter": counter,
        "events": events,
    }


def render_frames(built, tl, frames, frames_dir, fresh):
    scene = built["scene"]
    if fresh and os.path.isdir(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir, exist_ok=True)
    todo = [f for f in frames if not os.path.exists(os.path.join(frames_dir, "%05d.png" % f))]
    print("Rendering %d of %d frames to %s" % (len(todo), len(frames), frames_dir), flush=True)
    t0 = time.time()
    done = 0
    for vf in todo:
        path = os.path.join(frames_dir, "%05d.png" % vf)
        shot = tl.shot_at(vf)
        if shot.hold and vf > shot.video_start:
            src = os.path.join(frames_dir, "%05d.png" % shot.video_start)
            if os.path.exists(src):
                os.link(src, path)
                continue
        sf, cam = tl.scene_frame(vf)
        scene.frame_set(sf)
        scene.camera = built["cams"][cam]
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        done += 1
        el = time.time() - t0
        left = len(todo) - done
        print("  frame %5d (scene %5d, %s)  %.1fs/frame  ~%dm left"
              % (vf, sf, cam, el / done, (el / done) * left / 60.0), flush=True)


def fill_events(cfg, ftl, built):
    """Events log for a 'fill' episode: counts, ruler positions and milestones per frame."""
    from hmtb import skyline
    scene = built["scene"]
    cam = built["cams"]["main"]
    a, b = ftl.segments["zoom"][1], ftl.segments["outro"][0]
    ruler = {}
    for f in range(a, b):
        scene.frame_set(f)
        pts = [world_to_camera_view(scene, cam, Vector((0.0, 0.0, z)))
               for z in (0.0, ftl.level[f], skyline.H_OCC, skyline.H_TIP)]
        ruler[f] = [round(1.0 - p.y, 4) for p in pts]
    from scene3d.skyscraper import HERO_Y
    scene.frame_set(ftl.drop_impact_f)
    p = world_to_camera_view(scene, cam, Vector((0.0, HERO_Y, 0.5)))
    events = [{"type": "drop", "frame": ftl.drop_impact_f, "count": 1,
               "screen": [round(p.x, 4), round(1.0 - p.y, 4)]}]
    events += [{"type": "milestone", "frame": m["frame"], "count": m["count"], "text": m["text"]}
               for m in ftl.milestones]
    events.append({"type": "full", "frame": ftl.segments["full"][0]})
    events.append({"type": "outro_start", "frame": ftl.segments["outro"][0]})
    public_cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
    counts = [ftl.count[ftl.scene_frame(v)[0]] for v in range(ftl.total_frames)]
    levels = [ftl.level[ftl.scene_frame(v)[0]] for v in range(ftl.total_frames)]
    return {
        "version": 1, "mode": "fill", "config": public_cfg, "fps": ftl.fps,
        "total_frames": ftl.total_frames, "duration_s": ftl.total_frames / float(ftl.fps),
        "segments": ftl.segments, "events": events,
        "count": [round(c, 1) for c in counts], "level_m": [round(lv, 2) for lv in levels],
        "ruler": {str(k): v for k, v in ruler.items()},
        "h_occ": skyline.H_OCC, "floor_height_m": cfg.get("floor_height_m", 3.59),
    }


def main_fill(args, raw):
    """Render a 'fill' episode (see hmtb/fill.py)."""
    from hmtb import skyline
    from hmtb.fill import build_fill_timeline, resolve_fill
    from scene3d import skyscraper
    cfg = resolve_fill(raw, args.config)
    ftl = build_fill_timeline(cfg, skyline.fill_fraction_table(), skyline.H_OCC)
    print("Fill episode: %.0f s. Answer: %.4g items, %.4g kg." % (cfg["duration_s"], cfg["answer"],
                                                                  cfg["answer_mass_kg"]), flush=True)
    for name, (s0, s1) in ftl.segments.items():
        print("  %-6s %6.2fs - %6.2fs" % (name, s0 / 30.0, s1 / 30.0))
    base_w, base_h = PREVIEW_RES if args.preview else FULL_RES
    width = int(round(base_w * args.scale / 2)) * 2
    height = int(round(base_h * args.scale / 2)) * 2
    samples = args.samples or (cfg["preview_samples"] if args.preview else cfg["samples"])
    frames = list(range(0, min(ftl.total_frames, int(PREVIEW_SECONDS * FPS)))) if args.preview \
        else list(range(ftl.total_frames))
    if args.frames and ":" in args.frames:
        a, b = args.frames.split(":")
        frames = [f for f in frames if int(a or 0) <= f < int(b or 10 ** 9)]
    elif args.frames:
        frames = sorted(int(f) for f in args.frames.split(","))
    out_dir = args.out or os.path.join(HERE, "out", cfg["slug"] + ("_preview" if args.preview else ""))
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    built = skyscraper.build_scene(cfg, ftl, width, height, samples)
    print("  scene built in %.1fs" % (time.time() - t0), flush=True)
    events_path = os.path.join(out_dir, "events.json")
    if not os.path.exists(events_path) or args.preview or (args.frames and args.frames.startswith("0")):
        events = fill_events(cfg, ftl, built)
        all_frames = list(range(0, int(PREVIEW_SECONDS * FPS))) if args.preview else list(range(ftl.total_frames))
        events["render"] = {"width": width, "height": height, "samples": samples,
                            "frames": [all_frames[0], all_frames[-1] + 1]}
        with open(events_path, "w") as fh:
            json.dump(events, fh)
        print("Wrote", events_path, flush=True)
    if not args.no_render:
        render_frames(built, ftl, frames, os.path.join(out_dir, "frames"), args.fresh)
    print("Done.", flush=True)


def main():
    args = parse_args()
    with open(args.config) as fh:
        raw = json.load(fh)
    if raw.get("mode") == "fill":
        return main_fill(args, raw)
    cfg = load_config(args.config)
    for w in cfg["_warnings"]:
        print("WARNING:", w)
    tl = build_timeline(cfg)
    print(describe(cfg, tl), flush=True)

    base_w, base_h = PREVIEW_RES if args.preview else FULL_RES
    width = int(round(base_w * args.scale / 2)) * 2
    height = int(round(base_h * args.scale / 2)) * 2
    samples = args.samples or (cfg["preview_samples"] if args.preview else cfg["samples"])

    if args.preview:
        frames = list(range(0, min(tl.total_frames, int(PREVIEW_SECONDS * FPS))))
    else:
        frames = list(range(tl.total_frames))
    if args.frames and ":" in args.frames:
        a, b = args.frames.split(":")
        frames = [f for f in frames if int(a or 0) <= f < int(b or 10 ** 9)]
    elif args.frames:
        frames = sorted(int(f) for f in args.frames.split(","))

    out_dir = args.out or os.path.join(HERE, "out", cfg["slug"] + ("_preview" if args.preview else ""))
    os.makedirs(out_dir, exist_ok=True)
    events_path = os.path.join(out_dir, "events.json")
    cfg_hash = hashlib.sha1(json.dumps({k: v for k, v in cfg.items() if not k.startswith("_")},
                                       sort_keys=True).encode()).hexdigest()[:12]
    existing = None
    if os.path.exists(events_path):
        with open(events_path) as fh:
            existing = json.load(fh)
        if existing.get("config_hash") != cfg_hash:
            existing = None

    # Physics is needed if a rendered frame shows the break, or once for the full events
    # log (debris sounds). Later chunks of a split render reuse that log and skip the bake.
    shows_break = any(tl.scene_frame(f)[0] >= tl.break_f - 2 for f in frames)
    full_log = existing is not None and existing.get("physics")
    need_physics = shows_break or (not args.preview and not full_log)
    print("Building scene (%dx%d, %d samples, physics %s)..." % (width, height, samples,
                                                                 "on" if need_physics else "off"), flush=True)
    t0 = time.time()
    built = build_scene(cfg, tl, width, height, samples, need_physics)
    if need_physics:
        built["debris"] = physics.debris_events(built["scene"], tl, built["dynamic"])
    print("  scene built in %.1fs" % (time.time() - t0), flush=True)

    if need_physics or existing is None:
        events = build_events(cfg, tl, built, args.preview)
        events["physics"] = need_physics
        events["config_hash"] = cfg_hash
        all_frames = list(range(0, int(PREVIEW_SECONDS * FPS))) if args.preview else list(range(tl.total_frames))
        events["render"] = {"width": width, "height": height, "samples": samples,
                            "frames": [all_frames[0], all_frames[-1] + 1]}
        with open(events_path, "w") as fh:
            json.dump(events, fh, indent=1)
        print("Wrote", events_path, flush=True)

    if not args.no_render:
        render_frames(built, tl, frames, os.path.join(out_dir, "frames"), args.fresh)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
