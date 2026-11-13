"""'Kaiju' episodes: an original pizza monster rampages through a city (no Blender here).

The config holds the voiceover script (line text + start time) and the beat times. This
module turns them into frames, so the 3D animation, captions and sound all line up:

    hook      establishing shot, breaking-news banner, Big Ben bongs
    erupt     the river bubbles, a cheese geyser erupts
    rise      the monster rises from the river and roars; name card
    bridge    it stomps across Westminster Bridge, buses go flying
    bite      it bites the top off Big Ben
    eye       a ground-shaking stomp sends the London Eye rolling like a pizza cutter
    pineapple pineapples rain down; it gags and dives back into the river
    end       end card over a calm (frozen) shot
"""

from dataclasses import dataclass, field

from . import FPS
from .timeline import Shot

KAIJU_DEFAULTS = {
    "duration_s": 53.0,
    "voice": "en_GB-alan-medium",
    "voice_speed": 1.08,
    "samples": 16,
    "preview_samples": 6,
    "seed": 3,
    "slug": None,
}

BEATS = ("hook", "erupt", "rise", "bridge", "bite", "eye", "pineapple", "end")


def resolve_kaiju(raw, source_path=None):
    import os
    cfg = dict(KAIJU_DEFAULTS)
    cfg.update(raw)
    for key in ("title", "monster_name", "beats_s", "voiceover"):
        if key not in cfg:
            raise ValueError("Kaiju config is missing %r" % key)
    starts = [cfg["beats_s"][b] for b in BEATS]
    if starts != sorted(starts) or starts[0] != 0:
        raise ValueError("beats_s must start at 0 and be in order: %s" % ", ".join(BEATS))
    if cfg["duration_s"] <= starts[-1]:
        raise ValueError("duration_s must be after the 'end' beat")
    if cfg["slug"] is None:
        cfg["slug"] = os.path.splitext(os.path.basename(source_path or "kaiju_episode"))[0]
    cfg["_warnings"] = []
    return cfg


@dataclass
class KaijuTimeline:
    fps: int
    total_frames: int
    segments: dict
    shots: list
    hold_f: int
    moments: dict = field(default_factory=dict)    # named frames: roar, bite, kick, pineapples, dive...

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


def build_kaiju_timeline(cfg, fps=FPS):
    total = int(round(cfg["duration_s"] * fps))
    starts = [int(round(cfg["beats_s"][b] * fps)) for b in BEATS] + [total]
    segments = {b: (starts[i], starts[i + 1]) for i, b in enumerate(BEATS)}
    m = {k: int(round(v * fps)) for k, v in cfg.get("moments_s", {}).items()}
    hold = segments["end"][0] + int(1.0 * fps)
    shots = [Shot(b, segments[b][0], segments[b][1], segments[b][0]) for b in BEATS]
    # The end card holds a calm frame (saves rendering the last seconds).
    shots[-1] = Shot("end", segments["end"][0], hold, segments["end"][0])
    shots.append(Shot("end", hold, total, hold - 1, hold=True))
    return KaijuTimeline(fps=fps, total_frames=total, segments=segments, shots=shots, hold_f=hold - 1, moments=m)


def caption_words(cfg, durations):
    """Word-by-word caption timing: [(start_s, end_s, word, line_index)].

    Each line's speaking time is split between its words in proportion to their
    length, which is close enough for karaoke-style highlighting. A line's optional
    "caption" is shown instead of its spoken "text" (e.g. "8:14 PM" for "Eight fourteen p.m.").
    """
    out = []
    for i, line in enumerate(cfg["voiceover"]):
        words = line.get("caption", line["text"]).split()     # caption may differ from the spoken text
        dur = max(0.3, durations[i] - 0.25)
        weights = [len(w.strip(".,?!")) + 2 for w in words]
        total = float(sum(weights))
        t = line["at_s"]
        for w, wt in zip(words, weights):
            d = dur * wt / total
            out.append((t, t + d, w, i))
            t += d
    return out
