"""'Fill' episodes: "How many ___ to fill ___?" (pure Python, no Blender).

The answer is plain arithmetic, computed from facts in the config:

    count  = container volume x packing / item volume
    weight = count x item mass

The video then animates that answer:

    hook      0-2.5 s    title over a low-angle shot of the container
    one       2.5-5.5 s  a single real-size item lands at its foot: "1"
    zoom      5.5-8 s    the camera rockets back to show the whole container
    fill      8 s-       the container fills from the bottom; the counter follows the
                         filled volume, with fact callouts at milestones
    full      3 s        FULL! Items spray out of the top
    outro     9 s        freeze-frame and the answer card

``FillTimeline`` exposes the same ``shots`` / ``scene_frame`` / ``shot_at`` interface
as the break timeline, so render.py renders both the same way.
"""

import bisect
import math
from dataclasses import dataclass, field

from . import FPS
from .timeline import Shot

FILL_DEFAULTS = {
    "duration_s": 52,
    "hook_s": 2.5,
    "one_s": 3.0,
    "zoom_s": 2.5,
    "full_s": 3.0,
    "outro_s": 9.0,
    "packing": 1.0,           # 1.0 = stacked neatly with no gaps
    "milestones": [],         # [{"count": 1.24e9, "text": "..."}]
    "counter_label": "PHONES",
    "end_question": "WHAT SHOULD WE FILL NEXT?",
    "samples": 16,
    "preview_samples": 6,
    "seed": 1,
    "slug": None,
}


def resolve_fill(raw, source_path=None):
    import os
    cfg = dict(FILL_DEFAULTS)
    cfg.update(raw)
    for key in ("title", "container", "container_volume_m3", "item_mass_kg"):
        if key not in cfg:
            raise ValueError("Fill config is missing %r" % key)
    if cfg["duration_s"] > 75 or cfg["duration_s"] < 30:
        raise ValueError("duration_s should be between 30 and 75 for a fill episode")
    if "item_volume_m3" not in cfg:          # boxes; round items give their own volume
        x, y, z = cfg["item_size_mm"]
        cfg["item_volume_m3"] = x * y * z * 1e-9
    cfg["answer"] = cfg["container_volume_m3"] * cfg["packing"] / cfg["item_volume_m3"]
    cfg["answer_mass_kg"] = cfg["answer"] * cfg["item_mass_kg"]
    if cfg["slug"] is None:
        cfg["slug"] = os.path.splitext(os.path.basename(source_path or "fill_episode"))[0]
    cfg["_warnings"] = []
    return cfg


SCALE_WORDS = [(1e24, "SEPTILLION"), (1e21, "SEXTILLION"), (1e18, "QUINTILLION"), (1e15, "QUADRILLION"),
               (1e12, "TRILLION"), (1e9, "BILLION"), (1e6, "MILLION")]


def big_number(n):
    """(value text, scale word) for the counter: ('13.47', 'BILLION'), ('856,342', '')."""
    for size, word in SCALE_WORDS:
        if n >= size:
            v = n / size
            return ("%.2f" % v if v < 100 else "%.1f" % v), word
    return "{:,}".format(int(round(n))), ""


def big_mass(kg):
    """'2.29 MILLION TONNES', '395 QUINTILLION TONNES', '840 TONNES', '0.8 KG'."""
    t = kg / 1000.0
    for size, word in SCALE_WORDS:
        if t >= size:
            v = t / size
            return ("%.2f" % v if v < 100 else "%.0f" % v) + " " + word + " TONNES"
    if t >= 1e3:
        return "{:,} TONNES".format(int(round(t)))
    if t >= 1:
        return "%.1f TONNES" % t
    if kg >= 1:
        return "%.1f KG" % kg
    return "%.2f KG" % kg


@dataclass
class FillTimeline:
    fps: int
    total_frames: int
    segments: dict
    shots: list
    hold_f: int                      # scene frame frozen during the outro
    drop_release_f: int
    drop_impact_f: int
    level: list = field(default_factory=list)    # fill level (m) per scene frame
    count: list = field(default_factory=list)    # items inside per scene frame
    milestones: list = field(default_factory=list)

    def shot_at(self, video_f):
        for shot in self.shots:
            if shot.video_start <= video_f < shot.video_end:
                return shot
        return self.shots[-1]

    def scene_frame(self, video_f):
        shot = self.shot_at(video_f)
        if shot.hold:
            return shot.scene_start, shot.camera
        return shot.scene_start + (video_f - shot.video_start), shot.camera


def build_fill_timeline(cfg, fraction_table, top_level, fps=FPS, bottom_level=0.0):
    """Frames for each beat, plus the fill level and count for every frame.

    With ``"count_curve": "log_intro"`` the counter first races through the scale words
    (million, billion, trillion...) at an even pace, then follows the filled volume.
    """
    total = int(round(cfg["duration_s"] * fps))
    f_hook = int(round(cfg["hook_s"] * fps))
    f_one = f_hook + int(round(cfg["one_s"] * fps))
    f_zoom = f_one + int(round(cfg["zoom_s"] * fps))
    f_outro = total - int(round(cfg["outro_s"] * fps))
    f_full = f_outro - int(round(cfg["full_s"] * fps))
    if f_full - f_zoom < 10 * fps:
        raise ValueError("duration_s is too short for the fill beat")
    segments = {"hook": (0, f_hook), "one": (f_hook, f_one), "zoom": (f_one, f_zoom),
                "fill": (f_zoom, f_full), "full": (f_full, f_outro), "outro": (f_outro, total)}

    levels = [x for x, _ in fraction_table]
    fracs = [y for _, y in fraction_table]

    def frac_at(lvl):
        i = bisect.bisect_left(levels, lvl)
        if i <= 0:
            return 0.0
        if i >= len(levels):
            return 1.0
        x0, x1, y0, y1 = levels[i - 1], levels[i], fracs[i - 1], fracs[i]
        return y0 + (y1 - y0) * (lvl - x0) / (x1 - x0)

    def level_for_fraction(fr):
        """Inverse of frac_at by bisection (the table is monotonic)."""
        lo, hi = bottom_level, top_level
        for _ in range(60):
            mid = (lo + hi) / 2
            if frac_at(mid) < fr:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    span = top_level - bottom_level
    log_intro = cfg.get("count_curve") == "log_intro"
    intro_end = f_zoom + int((f_full - f_zoom) * cfg.get("log_intro_share", 0.22))
    log_top = math.log10(cfg["answer"] * cfg.get("log_intro_until", 0.002))
    level, count = [], []
    for f in range(total):
        if f < f_zoom:
            lv, c = bottom_level, 0.0
        elif f >= f_full:
            lv, c = top_level, cfg["answer"]
        elif log_intro and f < intro_end:
            u = (f - f_zoom) / float(intro_end - f_zoom)
            c = 10 ** (u * log_top)
            lv = level_for_fraction(c / cfg["answer"])
        else:
            a0 = intro_end if log_intro else f_zoom
            u = (f - a0) / float(f_full - a0)
            if log_intro:
                fr0 = cfg.get("log_intro_until", 0.002)
                fr = fr0 + (1 - fr0) * (u ** 1.1)
                lv = level_for_fraction(fr)
            else:
                lv = bottom_level + span * (u ** 1.25)        # slow start, steady climb
            c = cfg["answer"] * frac_at(lv)
        if f_hook + 20 <= f < f_zoom:
            c = 1.0                              # the single item
        level.append(lv)
        count.append(c)

    milestones = []
    for m in cfg["milestones"]:
        f = next((i for i in range(f_zoom, f_full) if count[i] >= m["count"]), None)
        if f is not None:
            milestones.append(dict(m, frame=f))

    shots = [Shot("hook", 0, f_hook, 0), Shot("main", f_hook, f_outro, f_hook),
             Shot("main", f_outro, total, f_outro - 1, hold=True)]
    return FillTimeline(fps=fps, total_frames=total, segments=segments, shots=shots, hold_f=f_outro - 1,
                        drop_release_f=f_hook + 12, drop_impact_f=f_hook + 20, level=level, count=count,
                        milestones=milestones)
