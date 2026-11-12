"""The episode timeline: when each fold happens and what the camera does.

Everything is computed from the config in plain Python, so the Blender
renderer, the overlay and the audio all agree on timing. Times are seconds.

Structure of an episode:
    intro      title on screen over the flat sheet (the hook)
    folds      1..physical_folds as real fold animations, then the column
               grows by doubling. Pacing speeds up between landmark beats
               and slows down at each one, where it holds.
    finale     the last fold, a longer hold, then the call to action.
"""

import math

from . import style
from .landmarks import HOLD_S, FINAL_HOLD_S, compute_beats
from .mathutil import (MonotoneCurve, clamp, damped_bounce, ease_in_out_cubic,
                       ease_out_back, ease_out_cubic, lerp, smoothstep)
from .numbers import format_int, format_length, layers, thickness_m

INTRO_S = 0.9         # flat sheet + title before the first fold starts
CTA_S = 3.6           # "What should we fold next?" at the end
TITLE_S = 2.8         # how long the hook title stays up

# Base durations (seconds) before everything is scaled to duration_s.
PHYS_FIRST_S, PHYS_LAST_S = 1.75, 0.95      # first and last physical fold
COL_SLOW_S, COL_FAST_S = 1.05, 0.48         # column folds near / between beats
FINAL_FOLD_S = 1.8                          # the last, dramatic doubling


class Fold:
    """Timing for one fold (n = number of folds once it completes)."""

    def __init__(self, n, mode, t0, dur, hold):
        self.n, self.mode, self.t0, self.dur, self.hold = n, mode, t0, dur, hold
        self.t_end = t0 + dur              # fold animation finished
        self.hold_end = self.t_end + hold  # next fold starts here
        if mode == "physical":
            self.flip_start = t0 + 0.10 * dur
            self.flip_end = t0 + 0.66 * dur
            self.t_land = self.flip_end    # sheet lands -> counters update
        else:
            grow = 0.8 * dur if mode == "final" else min(0.45, 0.55 * dur)
            self.flip_start = t0
            self.flip_end = t0 + grow
            self.t_land = t0 + grow


class Timeline:
    def __init__(self, cfg):
        self.cfg = cfg
        self.fps = cfg["fps"]
        self.duration = cfg["duration_s"]
        self.n_frames = int(round(self.duration * self.fps))
        self.t_mm = cfg["thickness_mm"]
        self.N = cfg["folds"]
        self.P = min(cfg["physical_folds"], self.N)
        w, h = cfg["sheet_size_mm"]
        # Lay the sheet landscape so the first fold is seen side-on.
        self.sheet = (max(w, h) / 1000.0, min(w, h) / 1000.0)
        self.beats = compute_beats(self.t_mm, self.N, cfg.get("landmarks", "auto"))
        self._footprints()
        self._schedule()
        self._elevation_curve()
        self._camera()
        self._landmark_windows()

    # --- Geometry --------------------------------------------------------------

    def height(self, n):
        return thickness_m(self.t_mm, n)

    def _footprints(self):
        """Sheet footprint after each physical fold; always halve the long side."""
        dims = [self.sheet]
        self.fold_axis = [None]
        lx, ly = self.sheet
        for _ in range(self.P):
            if lx >= ly:
                lx /= 2
                self.fold_axis.append("x")
            else:
                ly /= 2
                self.fold_axis.append("y")
            dims.append((lx, ly))
        self.dims = dims

    def footprint(self, n):
        return self.dims[min(n, self.P)]

    # --- Pacing ----------------------------------------------------------------

    def _base_duration(self, n):
        if n == self.N and n > self.P:
            return FINAL_FOLD_S
        if n <= self.P:
            u = (n - 1) / max(1, self.P - 1)
            return lerp(PHYS_FIRST_S, PHYS_LAST_S, u)
        # Column folds: slow next to beats, fast in between.
        bounds = [self.P] + [b for b in self.beats if b > self.P] + [self.N]
        lo = max(b for b in bounds if b < n)
        hi = min(b for b in bounds if b >= n)
        m = hi - lo
        u = (n - lo - 0.5) / m
        return COL_SLOW_S - (COL_SLOW_S - COL_FAST_S) * math.sin(math.pi * u) ** 0.8

    def _schedule(self):
        base = []
        for n in range(1, self.N + 1):
            hold = FINAL_HOLD_S if n == self.N else (HOLD_S if n in self.beats else 0.0)
            base.append((n, self._base_duration(n), hold))
        flexible = sum(d + h for _, d, h in base)
        available = self.duration - INTRO_S - CTA_S
        self.scale = available / flexible
        if not 0.5 <= self.scale <= 2.0:
            print(f"[timeline] warning: {self.N} folds in {self.duration}s gives pacing x{self.scale:.2f}")

        self.folds = []
        t = INTRO_S
        for n, d, h in base:
            mode = "physical" if n <= self.P else ("final" if n == self.N else "column")
            f = Fold(n, mode, t, d * self.scale, h * self.scale)
            self.folds.append(f)
            t = f.hold_end
        self.cta_start = t
        self.title_end = min(TITLE_S, self.folds[0].t_land + 1.2) if self.folds else TITLE_S
        self.column_start = self.folds[self.P].t0 if self.P < self.N else self.duration
        self.finale_t = self.folds[-1].t_land

    # --- Camera ----------------------------------------------------------------

    def _view_folding(self, n):
        """View height (m) that frames the sheet/stack after n physical folds."""
        lx, ly = self.footprint(n)
        t = self.folds[n - 1].t_end if n >= 1 else 0.0
        e = math.radians(self.elevation(t))
        a = math.radians(style.AZIMUTH_START_DEG)
        depth = abs(lx * math.sin(a)) + abs(ly * math.cos(a))
        width = abs(lx * math.cos(a)) + abs(ly * math.sin(a))
        proj_h = depth * math.sin(e) + self.height(n) * math.cos(e)
        return max(proj_h / style.FILL_FOLDING, width / (0.5625 * 0.68))

    def _view_column(self, n):
        return self.height(n) / style.FILL_COLUMN

    def _view_stack(self, n):
        return self._view_folding(n) if n <= self.P else self._view_column(n)

    def _view_landmark(self, n):
        lm = self.beats[n]
        return max(self._view_stack(n),
                   lm["frame_h"] / style.FILL_LANDMARK,
                   lm["frame_w"] / (0.5625 * (style.SUBJECT_X - 0.05)))

    def _camera(self):
        keys = []
        v0 = self._view_folding(0)
        keys.append((0.0, v0 * 1.06))           # gentle push-in during the hook
        if self.folds:
            keys.append((self.folds[0].t0 + 0.2, v0))
        for f in self.folds:
            if f.mode == "physical":
                keys.append((f.t_end, self._view_stack(f.n)))
            else:
                keys.append((min(f.t_land + 0.15, f.t_end), self._view_stack(f.n)))
            if f.n in self.beats:
                v = self._view_landmark(f.n)
                keys.append((f.t_end + min(1.1, 0.5 * f.hold), v))
                drift = 1.35 if f.n == self.N else 1.03
                keys.append((f.hold_end, v * drift))
            elif f.n == self.N:
                v = self._view_stack(f.n)
                keys.append((f.hold_end, v * 1.35))
        keys.append((self.duration, keys[-1][1] * 1.05))
        self.log_view = MonotoneCurve([(t, math.log(v)) for t, v in keys])
        self.camera_keys = keys

    def _elevation_curve(self):
        """Look down on the flat sheet, lower as it thickens, then go low so
        the column rises against the sky."""
        hi, mid, lo = (style.ELEVATION_FOLDING_DEG, style.ELEVATION_STACK_DEG,
                       style.ELEVATION_COLUMN_DEG)
        if self.P == 0:
            keys = [(0.0, lo)]
        else:
            f_a = self.folds[max(0, round(self.P * 0.35) - 1)]
            f_b = self.folds[max(0, round(self.P * 0.7) - 1)]
            f_c = self.folds[self.P - 1]
            keys = [(0.0, hi), (f_a.t0, hi), (f_b.t_end, mid), (f_c.t_end, mid - 6.0)]
            if self.P < self.N:
                keys.append((self.folds[self.P].t0 + 1.6, lo))
        self._elev = MonotoneCurve(keys)

    def view_height(self, t):
        return math.exp(self.log_view(t))

    def elevation(self, t):
        return self._elev(t)

    def column_blend(self, t):
        """0 while looking down on the sheet, 1 once the camera is low."""
        hi, lo = style.ELEVATION_FOLDING_DEG, style.ELEVATION_COLUMN_DEG
        return clamp((hi - self.elevation(t)) / (hi - lo))

    def azimuth(self, t):
        return lerp(style.AZIMUTH_START_DEG, style.AZIMUTH_END_DEG, t / self.duration)

    # --- Landmarks -------------------------------------------------------------

    def _landmark_windows(self):
        """When each landmark appears, shows its label and retires."""
        self.landmark_windows = []
        beats = sorted(self.beats.items())
        for i, (n, lm) in enumerate(beats):
            f = self.folds[n - 1]
            if lm["kind"] == "pass":
                lead = lm.get("lead_folds", 0)
                appear = self.folds[max(0, n - 1 - lead)].t0
                if i > 0:  # never before the previous landmark has had its moment
                    appear = max(appear, self.folds[beats[i - 1][0] - 1].hold_end)
            else:
                appear = f.t_land + 0.05
            label_in = f.t_end + 0.15
            # The final label clears for the call to action.
            label_out = self.cta_start if n == self.N else f.hold_end + 0.25

            # Retire it once it is tiny, or before the column grows into it.
            gap = abs(lm["pos"][0]) - lm["width_m"] / 2
            v_exit = lm["height_m"] / 0.06
            if gap > 0:  # beside the stack: leave before the column reaches it
                v_exit = min(v_exit, gap / (style.COLUMN_MIN_WIDTH / 2) * 0.7)
            retire = self.duration + 1
            if n != self.N:
                t = f.hold_end
                while t < self.duration:
                    if self.view_height(t) > v_exit:
                        retire = t
                        break
                    t += 1.0 / self.fps
            if i + 1 < len(beats):
                nxt = self.folds[beats[i + 1][0] - 1]
                retire = min(retire, nxt.t_land + 0.6)
            retire = max(retire, label_out)
            self.landmark_windows.append(dict(
                id=lm["id"], fold=n, appear=appear, label_in=label_in,
                label_out=min(label_out, retire), retire=retire, landmark=lm))

    def landmark_presence(self, win, t):
        """Scale factor 0..1 for a landmark model at time t (pop in / shrink out)."""
        if t < win["appear"]:
            return 0.0
        grow = ease_out_back(clamp((t - win["appear"]) / 0.45), 1.2)
        shrink = 1.0 - ease_out_cubic(clamp((t - win["retire"]) / 0.4))
        return max(0.0, grow * shrink)

    # --- Per-frame state ---------------------------------------------------------

    def count_at(self, t):
        """Folds completed (and shown on the counters) at time t."""
        c = 0
        for f in self.folds:
            if f.t_land <= t:
                c = f.n
            else:
                break
        return c

    def active_fold(self, t):
        cur = None
        for f in self.folds:
            if f.t0 <= t:
                cur = f
            else:
                break
        return cur

    def stack_state(self, t):
        """What the stack looks like at time t (all lengths in metres)."""
        f = self.active_fold(t)
        if f is None:  # intro: the flat sheet
            lx, ly = self.footprint(0)
            return dict(phase="sheet", lx=lx, ly=ly, h=self.height(0), squash=0.0)

        if f.mode == "physical":
            n = f.n
            if t < f.flip_start:
                lx, ly = self.footprint(n - 1)
                return dict(phase="sheet", lx=lx, ly=ly, h=self.height(n - 1), squash=0.0)
            if t < f.flip_end:
                u = (t - f.flip_start) / (f.flip_end - f.flip_start)
                lx, ly = self.footprint(n - 1)
                return dict(phase="folding", lx=lx, ly=ly, h=self.height(n - 1),
                            axis=self.fold_axis[n], theta=math.pi * ease_in_out_cubic(u),
                            slide=ease_in_out_cubic(u), progress=u)
            lx, ly = self.footprint(n)
            settle = (t - f.flip_end) / max(0.15, 0.6 * (f.t_end - f.flip_end) + 0.15)
            return dict(phase="sheet", lx=lx, ly=ly, h=self.height(n),
                        squash=0.10 * damped_bounce(settle))

        # Column: the stack doubles in height.
        lx, ly = self.footprint(self.P)
        h0, h1 = self.height(f.n - 1), self.height(f.n)
        u = clamp((t - f.flip_start) / max(1e-6, f.flip_end - f.flip_start))
        e = ease_in_out_cubic(u) if f.mode == "final" else ease_out_back(u, 0.9)
        h = h0 * 2 ** e
        settle = clamp((t - f.flip_end) / 0.5)
        return dict(phase="column", lx=lx, ly=ly, h=max(h, 1e-9),
                    squash=0.05 * damped_bounce(settle), growth=u)

    # --- Events ----------------------------------------------------------------

    def events(self):
        """Every timed beat, for the overlay and the sound effects."""
        ev = [dict(t=0.0, type="title_in", text=self.cfg["title"]),
              dict(t=self.title_end, type="title_out")]
        for f in self.folds:
            if f.mode == "physical":
                ev.append(dict(t=f.flip_start, type="fold_start", n=f.n,
                               duration=f.flip_end - f.flip_start))
                ev.append(dict(t=f.t_land, type="fold_land", n=f.n))
            else:
                ev.append(dict(t=f.t0, type="grow", n=f.n, final=f.mode == "final",
                               duration=f.flip_end - f.flip_start))
                ev.append(dict(t=f.t_land, type="grow_land", n=f.n))
            ev.append(dict(t=f.t_land, type="counter", n=f.n,
                           layers=format_int(layers(f.n)),
                           thickness=format_length(self.height(f.n))))
        for w in self.landmark_windows:
            lm = w["landmark"]
            ev.append(dict(t=w["appear"], type="landmark_in", id=w["id"], n=w["fold"]))
            ev.append(dict(t=w["label_in"], type="label_in", id=w["id"],
                           labels=[list(x) for x in lm["labels"]]))
            ev.append(dict(t=w["label_out"], type="label_out", id=w["id"]))
            if w["fold"] in self.beats and w["fold"] != self.N:
                f = self.folds[w["fold"] - 1]
                ev.append(dict(t=f.t_end, type="landmark_whoosh", id=w["id"]))
            if lm.get("headline") and w["fold"] == self.N:
                ev.append(dict(t=self.finale_t + 0.35, type="headline", text=lm["headline"]))
        if self.P < self.N:
            ev.append(dict(t=self.column_start, type="pullback_start"))
        ev.append(dict(t=self.finale_t, type="pullback_end"))
        ev.append(dict(t=self.finale_t, type="finale_hit"))
        ev.append(dict(t=self.cta_start, type="cta_in", text=self.cfg["cta"]))
        ev.append(dict(t=self.duration, type="end"))
        ev.sort(key=lambda e: e["t"])
        for e in ev:
            e["t"] = round(e["t"], 4)
            e["frame"] = int(round(e["t"] * self.fps))
        return ev

    def summary(self):
        lines = [f"{self.cfg['title']}  ({self.N} folds, {self.duration:.0f}s, pacing x{self.scale:.2f})"]
        for n, lm in self.beats.items():
            f = self.folds[n - 1]
            lines.append(f"  fold {n:2d} at {f.t_land:5.1f}s  {format_length(self.height(n)):>12}  "
                         f"{lm['labels'][0][1]}")
        lines.append(f"  finale at {self.finale_t:.1f}s, CTA at {self.cta_start:.1f}s")
        return "\n".join(lines)
