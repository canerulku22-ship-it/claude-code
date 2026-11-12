"""Episode timeline: when every object drops, when cracks appear, how the video is cut.

The timeline is computed from the config alone (no Blender), so the render, overlay and
audio stages always agree on timing.

Video structure (video frames, 0-based)::

    intro     title, empty target, "Guess in the comments"
    build     objects drop one by one, faster and faster, cracks at crack_stages
    shatter   the final impact and a slow-motion shatter (main camera)
    replay    the break again in slow motion from a low side camera (optional)
    aftermath back to the main camera while the debris settles
    outro     freeze-frame of the result with the final counters

Fitting the duration: the config's drop intervals set the *shape* of the acceleration.
The replay and aftermath stretch first. If that isn't enough, every drop interval is
scaled by the same factor so the episode lands exactly on ``duration_s``.
``Timeline.interval_scale`` reports that factor (1.0 means the intervals were used as
written).

Scene frames (Blender's timeline) equal video frames for the continuous main-camera
part. The replay re-uses scene frames around the break, and the outro holds the last
aftermath frame.
"""

from dataclasses import dataclass, field

from . import FPS

FALL_S = 0.38           # how long each object takes to fall into view and land (snappy)
CLOSEUP_PRE_F = 4       # crack-stage close-ups start this many frames before the impact
CLOSEUP_S = 1.15        # and last this long
REPLAY_PREROLL_S = 0.7  # the replay starts this long before the final impact
REPLAY_RANGE_S = (3.0, 5.0)
AFTERMATH_RANGE_S = (1.5, 4.0)
MIN_GAP_FRAMES = 4      # never let two impacts land closer than this


@dataclass
class Drop:
    n: int              # pile count once this object has landed (1-based)
    release_f: int      # scene frame the object starts falling
    impact_f: int       # scene frame it lands
    crack_stage: int    # crack stage reached at this impact (0 = none)
    final: bool         # True for the object that breaks the target


@dataclass
class Shot:
    camera: str         # "main" or "replay"
    video_start: int    # first video frame (inclusive)
    video_end: int      # last video frame (exclusive)
    scene_start: int    # scene frame shown at video_start
    hold: bool = False  # True = freeze scene_start for the whole shot


@dataclass
class Timeline:
    fps: int
    total_frames: int
    drops: list
    break_f: int
    segments: dict
    shots: list
    scene_end_f: int
    interval_scale: float
    slowmo: dict
    crack_frames: list = field(default_factory=list)

    def shot_at(self, video_f):
        for shot in self.shots:
            if shot.video_start <= video_f < shot.video_end:
                return shot
        return self.shots[-1]

    def scene_frame(self, video_f):
        """Scene frame and camera name to render for a video frame."""
        shot = self.shot_at(video_f)
        if shot.hold:
            return shot.scene_start, shot.camera
        return shot.scene_start + (video_f - shot.video_start), shot.camera

    def segment_at(self, video_f):
        for name, (a, b) in self.segments.items():
            if a <= video_f < b:
                return name
        return "outro"

    def count_at(self, video_f):
        """Objects on the target as shown on the counter at a video frame."""
        if video_f >= self.segments["shatter"][0]:
            return len(self.drops)
        count = 0
        for d in self.drops:
            if d.impact_f <= video_f:
                count = d.n
        return count


def _base_gaps(cfg):
    """Gaps between consecutive impacts before fitting, accelerating start -> end."""
    n = cfg["break_at"]
    a, b = float(cfg["drop_interval_start_s"]), float(cfg["drop_interval_end_s"])
    if n == 2:
        return [a]
    # Slightly front-loaded so the speed-up is noticeable early on.
    return [a + (b - a) * (i / (n - 2)) ** 0.9 for i in range(n - 1)]


def _extra_gaps(cfg):
    """Fixed pauses: a beat after each crack stage and suspense before the last drop."""
    n = cfg["break_at"]
    stages = set(cfg["crack_stages"])
    extras = []
    for i in range(1, n):          # gap after impact i
        extra = cfg["crack_beat_s"] if i in stages else 0.0
        if i == n - 1:
            extra += cfg["suspense_s"]
        extras.append(extra)
    return extras


def build_timeline(cfg, fps=FPS):
    """Compute the full episode timeline from a resolved config."""
    duration = float(cfg["duration_s"])
    base = _base_gaps(cfg)
    extras = _extra_gaps(cfg)
    first_impact_s = cfg["intro_s"] + FALL_S

    shatter_s, outro_s = cfg["shatter_s"], cfg["outro_s"]
    replay_lo, replay_hi = REPLAY_RANGE_S if cfg["replay"] else (0.0, 0.0)
    post_lo = replay_lo + AFTERMATH_RANGE_S[0]
    post_hi = replay_hi + AFTERMATH_RANGE_S[1]

    natural = first_impact_s + sum(base) + sum(extras) + shatter_s + outro_s
    flex = duration - natural
    k = 1.0
    if flex < post_lo:
        k = (sum(base) - (post_lo - flex)) / sum(base)
        post = post_lo
    elif flex > post_hi:
        k = (sum(base) + (flex - post_hi)) / sum(base)
        post = post_hi
    else:
        post = flex
    if k < 0.3:
        raise ValueError(
            "break_at=%d doesn't fit in %ss with these intervals; raise duration_s or lower the intervals"
            % (cfg["break_at"], duration))

    if cfg["replay"]:
        replay_s = min(replay_hi, max(replay_lo, post * 0.55))
        aftermath_s = post - replay_s
        if aftermath_s < AFTERMATH_RANGE_S[0]:
            aftermath_s = AFTERMATH_RANGE_S[0]
            replay_s = post - aftermath_s
    else:
        replay_s, aftermath_s = 0.0, post

    # --- Drops -------------------------------------------------------------
    stage_of = {n: i + 1 for i, n in enumerate(cfg["crack_stages"])}
    fall_f = int(round(FALL_S * fps))
    drops = []
    t = first_impact_s
    last_impact = -999
    for i in range(cfg["break_at"]):
        n = i + 1
        impact_f = max(int(round(t * fps)), last_impact + MIN_GAP_FRAMES)
        drops.append(Drop(n=n, release_f=impact_f - fall_f, impact_f=impact_f,
                          crack_stage=stage_of.get(n, 0), final=(n == cfg["break_at"])))
        last_impact = impact_f
        if i < len(base):
            t += base[i] * k + extras[i]

    total = int(round(duration * fps))
    break_f = drops[-1].impact_f
    shatter_f = int(round(shatter_s * fps))
    replay_f = int(round(replay_s * fps))
    outro_f = int(round(outro_s * fps))
    aftermath_f = total - (break_f + shatter_f + replay_f + outro_f)

    v_shatter = break_f
    v_replay = v_shatter + shatter_f
    v_after = v_replay + replay_f
    v_outro = v_after + aftermath_f
    intro_end = int(round(cfg["intro_s"] * fps))
    segments = {
        "intro": (0, intro_end),
        "build": (intro_end, v_shatter),
        "shatter": (v_shatter, v_replay),
        "replay": (v_replay, v_after),
        "aftermath": (v_after, v_outro),
        "outro": (v_outro, total),
    }

    scene_after = break_f + shatter_f            # aftermath continues the main sim
    scene_end = scene_after + aftermath_f - 1    # last simulated frame (frozen in the outro)
    replay_scene_start = break_f - int(round(REPLAY_PREROLL_S * fps))
    # Main camera, with quick cuts to a close-up of the target at each crack stage.
    shots = []
    cursor = 0
    stage_drops = [d for d in drops if d.crack_stage and not d.final]
    for i, d in enumerate(stage_drops):
        a = d.impact_f - CLOSEUP_PRE_F
        b = d.impact_f + int(round(CLOSEUP_S * fps))
        nxt = stage_drops[i + 1].impact_f - CLOSEUP_PRE_F if i + 1 < len(stage_drops) else break_f - 12
        b = min(b, nxt - 6)
        if a <= cursor or b - a < 10:
            continue
        shots.append(Shot("main", cursor, a, cursor))
        shots.append(Shot("close", a, b, a))
        cursor = b
    shots.append(Shot("main", cursor, v_replay, cursor))
    if replay_f > 0:
        shots.append(Shot("replay", v_replay, v_after, replay_scene_start))
    shots.append(Shot("main", v_after, v_outro, scene_after))
    shots.append(Shot("main", v_outro, total, scene_end, hold=True))

    # Physics time scale: real time until the impact, slow motion through most of the
    # shatter, then back to real time so the debris settles before the freeze.
    slowmo = {
        "start_f": break_f,
        "hold_end_f": break_f + int(shatter_f * 0.75),
        "ramp_end_f": break_f + shatter_f + 4,
        "factor": float(cfg["slowmo_factor"]),
    }

    return Timeline(
        fps=fps, total_frames=total, drops=drops, break_f=break_f, segments=segments,
        shots=shots, scene_end_f=scene_end, interval_scale=k, slowmo=slowmo,
        crack_frames=[d.impact_f for d in drops if d.crack_stage],
    )


def time_scale_at(timeline, scene_f):
    """Physics speed (1 = real time) at a scene frame, matching the keyframes in Blender."""
    s = timeline.slowmo
    if scene_f <= s["start_f"]:
        return 1.0
    if scene_f <= s["start_f"] + 2:
        u = (scene_f - s["start_f"]) / 2.0
        return 1.0 + (s["factor"] - 1.0) * u
    if scene_f <= s["hold_end_f"]:
        return s["factor"]
    if scene_f <= s["ramp_end_f"]:
        u = (scene_f - s["hold_end_f"]) / float(s["ramp_end_f"] - s["hold_end_f"])
        return s["factor"] + (1.0 - s["factor"]) * u
    return 1.0


def describe(cfg, tl):
    """Human-readable summary printed at the start of a render."""
    lines = []
    fps = tl.fps
    lines.append("Duration %.1fs (%d frames). Break at %.2fs (drop #%d)."
                 % (tl.total_frames / fps, tl.total_frames, tl.break_f / fps, len(tl.drops)))
    if abs(tl.interval_scale - 1.0) > 0.01:
        gaps = _base_gaps(cfg)
        lines.append("Drop intervals scaled x%.2f to fit the duration: %.2fs -> %.2fs."
                     % (tl.interval_scale, gaps[0] * tl.interval_scale, gaps[-1] * tl.interval_scale))
    for name, (a, b) in tl.segments.items():
        lines.append("  %-9s %6.2fs - %6.2fs" % (name, a / fps, b / fps))
    return "\n".join(lines)
