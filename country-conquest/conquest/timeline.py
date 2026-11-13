"""Choreography: turns a simulated episode into timed scenes, camera moves and an events log.

Everything here is a pure function of the plan + config, so any frame can be
rendered independently (which lets frames render in parallel), and the audio
step can place every sound from the events log alone.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import numpy as np

from .render.camera import Camera, ease_in_out_cubic, lerp_camera
from .render.text import flag_emoji
from .sim import EpisodePlan, Round
from .world import World

REF_W, REF_H = 1080, 1920


def safe_rect(cfg: dict) -> tuple[float, float, float, float]:
    s = cfg["safe_area"]
    return (REF_W * s["left"], REF_H * s["top"], REF_W * (1 - s["right"]), REF_H * (1 - s["bottom"]))


@dataclass
class CamMove:
    t0: float
    t1: float
    a: Camera
    b: Camera


@dataclass
class RoundTimes:
    """All the moments of one round (absolute seconds)."""
    plan: Round
    spin: tuple[float, float]
    land: float
    ticks: list[tuple[float, str]]          # (time, highlighted country) for the roulette
    wheel: dict | None                      # wheel-spinner parameters
    battle: tuple[float, float]
    clash: float
    exchanges: list[dict]                   # per exchange: start, impact, ...
    ko: float
    takeover: tuple[float, float]
    paint: tuple[float, float]
    plant: float
    paint_origin: tuple[float, float]       # projected metres
    paint_radius_m: float
    paint_targets: list[str]


@dataclass
class Timeline:
    cfg: dict
    plan: EpisodePlan
    duration: float
    fps: int
    intro: tuple[float, float]
    outro: tuple[float, float]
    rounds: list[RoundTimes]
    camera_moves: list[CamMove]
    events: list[dict] = field(default_factory=list)
    texts: dict = field(default_factory=dict)

    # ---- queries used by the renderer ---------------------------------------
    def scene_at(self, t: float):
        """('intro'|'spin'|'battle'|'takeover'|'outro', RoundTimes|None, local t)."""
        if t < self.intro[1]:
            return "intro", None, t - self.intro[0]
        for rt in self.rounds:
            if t < rt.spin[1]:
                return "spin", rt, t - rt.spin[0]
            if t < rt.battle[1]:
                return "battle", rt, t - rt.battle[0]
            if t < rt.takeover[1]:
                return "takeover", rt, t - rt.takeover[0]
        return "outro", None, t - self.outro[0]

    def camera_at(self, t: float) -> Camera:
        cam = self.camera_moves[0].a
        for mv in self.camera_moves:
            if t < mv.t0:
                break
            if t <= mv.t1:
                u = (t - mv.t0) / max(mv.t1 - mv.t0, 1e-6)
                return lerp_camera(mv.a, mv.b, ease_in_out_cubic(u))
            cam = mv.b
        return cam

    def holdings_at(self, t: float) -> dict:
        """Champion / territory / streak as shown on screen at time ``t``."""
        champion, territory, streak = self.plan.start["champion"], list(self.plan.start["territory"]), \
            self.plan.start["streak"]
        color = self.rounds[0].plan.champion_color if self.rounds else tuple(self.plan.end["color"])
        for rt in self.rounds:
            if t >= rt.plant:
                p = rt.plan
                champion, territory, streak, color = p.champion_after, p.territory_after, p.streak_after, \
                    p.color_after
        return {"champion": champion, "territory": territory, "streak": streak, "color": tuple(color)}


# ---------------------------------------------------------------------------

def _ticks(t0: float, t1: float, first: float = 0.055, last: float = 0.42) -> list[float]:
    """Decelerating tick times between t0 and t1 (the last tick lands at t1)."""
    span = t1 - t0
    best = None
    for n in range(4, 60):
        r = (last / first) ** (1 / (n - 1))
        total = sum(first * r ** k for k in range(n))
        if best is None or abs(total - span) < abs(best[1] - span):
            best = (n, total, r)
    n, total, r = best
    scale = span / total
    times, t = [], t0
    for k in range(n):
        t += first * r ** k * scale
        times.append(t)
    times[-1] = t1
    return times


def _roulette_sequence(rng: random.Random, candidates: list[str], opponent: str, n: int) -> list[str]:
    if len(candidates) == 1:
        return [opponent] * n
    seq, prev = [], None
    for i in range(n - 1):
        options = [c for c in candidates if c != prev and not (i == n - 2 and c == opponent)]
        prev = rng.choice(options or candidates)
        seq.append(prev)
    seq.append(opponent)
    return seq


def _country_points(world: World, codes, max_points: int = 1500) -> np.ndarray:
    lod = world.lods[2]
    idx = {world.index[c] for c in codes}
    parts = [lod.verts[s:s + n] for s, n, c, h in zip(lod.starts, lod.lengths, lod.country, lod.hole)
             if c in idx and not h]
    pts = np.concatenate(parts)
    if len(pts) > max_points:
        pts = pts[:: math.ceil(len(pts) / max_points)]
    return pts


def _paint_origin(world: World, targets: list[str], source: list[str]) -> tuple[tuple[float, float], float]:
    """Point of the painted area closest to the painter, and the farthest distance to cover."""
    tp = _country_points(world, targets)
    sp = _country_points(world, source, 800)
    best_d, best_i = None, 0
    for i in range(0, len(tp), 256):
        d = ((tp[i:i + 256, None, :] - sp[None, :, :]) ** 2).sum(-1).min(axis=1)
        j = int(d.argmin())
        if best_d is None or d[j] < best_d:
            best_d, best_i = d[j], i + j
    origin = tp[best_i]
    radius = float(np.sqrt(((tp - origin) ** 2).sum(-1)).max())
    return (float(origin[0]), float(origin[1])), radius


def _name(world: World, cfg: dict, code: str) -> str:
    return cfg.get("names", {}).get(code, world[code].name).upper()


def build_timeline(world: World, cfg: dict, plan: EpisodePlan) -> Timeline:
    video, timing = cfg["video"], cfg["timing"]
    T = video["target_duration"]
    intro_d, outro_d = timing["intro"], timing["outro"]
    round_len = (T - intro_d - outro_d) / cfg["rounds"]
    spin_d = round_len * timing["spin_share"]
    take_d = round_len * timing["takeover_share"]
    battle_d = round_len - spin_d - take_d

    sx0, sy0, sx1, sy1 = safe_rect(cfg)
    map_focus = (sx0, sy0 + 220, sx1, sy1 - 40)
    intro_focus = (sx0, sy0 + 560, sx1, sy1 - 30)
    outro_focus = (sx0, sy0 + 230, sx1, sy1 - 300)

    events: list[dict] = []
    moves: list[CamMove] = []
    seed = plan.seed

    # ---- intro ---------------------------------------------------------------
    start_terr = plan.start["territory"]
    intro_bbox = world.bbox_of(start_terr)
    cam_intro_a = Camera.fit(intro_bbox, intro_focus, pad=0.10, min_span_m=700_000).zoomed(1.35)
    cam_intro_b = Camera.fit(intro_bbox, intro_focus, pad=0.16, min_span_m=900_000)
    moves.append(CamMove(0.0, intro_d, cam_intro_a, cam_intro_b))
    events += [{"t": 0.0, "type": "intro"}, {"t": 0.30, "type": "plant"}, {"t": 0.15, "type": "title"}]
    cam = cam_intro_b

    t = intro_d
    rounds: list[RoundTimes] = []
    for rp in plan.rounds:
        fx = random.Random(f"{seed}:fx:{rp.number}")
        # ---- spin -------------------------------------------------------------
        s0, s1 = t, t + spin_d
        land = s1 - 0.75
        spin_bbox = world.bbox_of(rp.territory + rp.candidates)
        cam_spin = Camera.fit(spin_bbox, map_focus, pad=0.08, min_span_m=2_000_000)
        both_bbox = world.bbox_of(rp.territory + [rp.opponent])
        cam_both = Camera.fit(both_bbox, map_focus, pad=0.14, min_span_m=1_600_000)
        moves.append(CamMove(s0, s0 + 0.5, cam, cam_spin))
        events.append({"t": s0 + 0.05, "type": "spin_start", "round": rp.number})

        wheel = None
        if cfg["spinner_style"] == "wheel":
            wheel = _wheel_params(fx, rp, s0 + 0.35, land)
            tick_times = wheel["tick_times"]
            ticks = [(tt, rp.opponent) for tt in tick_times]
            moves.append(CamMove(land + 0.35, s1, cam_spin, cam_both))
        else:
            tick_times = _ticks(s0 + 0.40, land)
            seq = _roulette_sequence(fx, rp.candidates, rp.opponent, len(tick_times))
            ticks = list(zip(tick_times, seq))
            moves.append(CamMove(land + 0.12, s1, cam_spin, cam_both))
        events += [{"t": round(tt, 4), "type": "tick", "i": i, "n": len(tick_times)}
                   for i, tt in enumerate(tick_times[:-1])]
        events.append({"t": land, "type": "ding", "country": rp.opponent})
        cam = cam_both

        # ---- battle ------------------------------------------------------------
        b0, b1 = s1, s1 + battle_d
        clash = b0 + 0.42
        ex_list = rp.battle.exchanges
        window_start, window_end = b0 + 0.95, b1 - 1.25
        spacing = min(0.62, (window_end - window_start) / max(1, len(ex_list)))
        exchanges = []
        hp_a, hp_b = rp.battle.max_a, rp.battle.max_b
        for i, ex in enumerate(ex_list):
            start = window_start + i * spacing
            impact = start + min(0.15, spacing * 0.4)
            exchanges.append({"start": start, "impact": impact, "spacing": spacing,
                              "attacker": ex.attacker, "kind": ex.kind, "damage": ex.damage,
                              "hp_a_before": hp_a, "hp_b_before": hp_b,
                              "hp_a": ex.hp_a, "hp_b": ex.hp_b, "tags": ex.tags})
            hp_a, hp_b = ex.hp_a, ex.hp_b
            events.append({"t": round(impact, 4), "type": ex.kind, "attacker": ex.attacker,
                           "damage": ex.damage, "tags": ex.tags})
        ko = exchanges[-1]["impact"]
        events += [{"t": b0, "type": "whoosh"}, {"t": clash, "type": "clash"},
                   {"t": ko + 0.02, "type": "ko"}, {"t": ko + 0.30, "type": "victory",
                                                    "winner": rp.winner}]

        # ---- takeover ------------------------------------------------------------
        k0, k1 = b1, b1 + take_d
        paint = (k0 + 0.05, k0 + 1.05)
        plant = k0 + 1.0
        if rp.new_champion:
            targets = rp.territory + [rp.opponent]
            source = [rp.opponent]
            origin, radius = _paint_origin(world, rp.territory, [rp.opponent])
            radius = max(radius, _paint_origin(world, [rp.opponent], rp.territory)[1])
        else:
            targets = [rp.opponent]
            origin, radius = _paint_origin(world, targets, rp.territory)
        if not rp.new_champion:
            focus = Camera.fit(world.bbox_of([rp.opponent]), map_focus, pad=0.2, min_span_m=1_300_000)
            push = min(1.0, max(0.0, math.log(focus.scale / cam.scale) / math.log(4.0))) * 0.55
            cam_take = lerp_camera(cam, focus, push)
            moves.append(CamMove(k0, k0 + 1.1, cam, cam_take))
            cam = cam_take
        events += [{"t": paint[0], "type": "paint", "duration": paint[1] - paint[0]},
                   {"t": plant + 0.12, "type": "plant"}, {"t": plant + 0.15, "type": "count",
                                                           "count": len(rp.territory_after)}]
        if rp.new_champion:
            events.append({"t": k0 + 0.25, "type": "new_champion", "country": rp.winner})

        rounds.append(RoundTimes(rp, (s0, s1), land, ticks, wheel, (b0, b1), clash, exchanges, ko,
                                 (k0, k1), paint, plant, origin, radius, targets))
        t = k1

    # ---- outro ------------------------------------------------------------------
    o0, o1 = t, t + outro_d
    final = plan.end["territory"]
    cam_out = Camera.fit(world.bbox_of(final), outro_focus, pad=0.18, min_span_m=3_500_000)
    moves.append(CamMove(o0, o0 + 1.3, cam, cam_out))
    moves.append(CamMove(o0 + 1.3, o1, cam_out, cam_out.zoomed(0.93)))
    events += [{"t": o0, "type": "outro"}, {"t": o0 + 0.35, "type": "title"}]

    events.sort(key=lambda e: e["t"])
    tl = Timeline(cfg, plan, o1, video["fps"], (0.0, intro_d), (o0, o1), rounds, moves, events)
    tl.texts = _texts(world, cfg, plan)
    return tl


def _wheel_params(rng: random.Random, rp: Round, t0: float, t1: float) -> dict:
    """A spinning flag wheel that stops with the opponent under the pointer."""
    segs = list(rp.candidates)
    if len(segs) > 12:   # keep the wheel readable; the opponent is always on it
        others = [c for c in segs if c != rp.opponent]
        segs = sorted(rng.sample(others, 11) + [rp.opponent])
    if len(segs) == 1:
        segs = segs * 2
    rng.shuffle(segs)
    n = len(segs)
    seg_angle = 360.0 / n
    target = segs.index(rp.opponent)
    # Pointer sits at the top (angle 0). Segment i spans [i*seg, (i+1)*seg) clockwise.
    jitter = rng.uniform(0.25, 0.75)
    final_angle = 360.0 * rng.randint(3, 4) + (360.0 - (target + jitter) * seg_angle)
    # Angle follows an ease-out curve; a tick fires each time a boundary passes the pointer.
    ticks, prev = [], 0
    steps = 600
    for k in range(1, steps + 1):
        u = k / steps
        ang = final_angle * (1 - (1 - u) ** 3)
        idx = int(ang // seg_angle)
        if idx != prev:
            ticks.append(t0 + u * (t1 - t0))
            prev = idx
    ticks.append(t1)
    return {"segments": segs, "final_angle": final_angle, "t0": t0, "t1": t1, "tick_times": ticks}


def _texts(world: World, cfg: dict, plan: EpisodePlan) -> dict:
    tpl = cfg["text"]
    champ = plan.start["champion"]
    count = len(plan.start["territory"])
    fmt = dict(flag=flag_emoji(world[champ].iso2), name=_name(world, cfg, champ), count=count,
               countries="country" if count == 1 else "countries",
               COUNTRIES="COUNTRY" if count == 1 else "COUNTRIES", episode=plan.episode)
    first = plan.episode == 1 or (count == 1 and plan.start.get("streak", 0) == 0)
    return {
        "intro": (tpl["intro_first"] if first else tpl["intro_continue"]).format(**fmt),
        "outro": tpl["outro"],
        "spin": tpl["spin"],
    }
