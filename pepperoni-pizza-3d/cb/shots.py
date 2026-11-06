"""The seven animated shots.  Every shot is its own Blender scene with its own
camera, lights and world.  Each shot also records:
  * overlays : 2D motion-graphics events (labels, headers, callouts ...)
  * tracks   : per-frame screen positions of 3D anchor points for overlays
  * cues     : sound-design events for audio.py
"""
import math
import zlib

import bpy
import numpy as np
from mathutils import Vector, Euler, Quaternion
import bmesh

import config as C
from . import util as U, materials as M, models as MD, stage as ST, fx
from .util import seg, lerp, ease_out, ease_in, ease_io, ease_back, smooth, impact, squash_scale

TAU = 2 * math.pi
TOP = MD.PZ_TOP                      # top of the pizza base
DW = TAU / 8                         # eight slices
CUT_OFF = -math.pi / 2 - DW / 2      # cut rays at CUT_OFF + k*DW; slice 0 points at -Y
PEPS = MD.pepperoni_layout(CUT_OFF)
PIZZA_SCALE = 0.8                    # served pizza is kept small in frame
_protos = None


def protos():
    global _protos
    if _protos is None:
        coll = bpy.data.collections.new("PROTOS")
        _protos = (coll, MD.proto_objects(coll))
    return _protos


def orbit(target, d, el, az):
    t = Vector(target)
    return t + Vector((math.sin(az) * math.cos(el) * d, -math.cos(az) * math.cos(el) * d, math.sin(el) * d))


class Shot:
    def __init__(self, name, n, world, fstop=4.0, lens=50.0):
        self.name, self.n = name, n
        self.sc = ST.new_scene(name, n, world)
        self.coll = self.sc.collection
        pc, self.P = protos()
        self.coll.children.link(pc)
        self.cam = ST.camera(self.sc, f"CAM_{name}", lens, fstop)
        self.ct = U.CamTrack(self.cam, (C.RES_X, C.RES_Y))
        self.overlays, self.cues, self._tracks = [], [], {}
        self.rng = np.random.default_rng(zlib.crc32(name.encode()))

    def frames(self):
        return range(1, self.n + 1)

    def cue(self, f, kind, **kw):
        self.cues.append(dict(f=float(f), kind=kind, **kw))

    def ov(self, **kw):
        self.overlays.append(kw)

    def track(self, name, fn):
        self._tracks[name] = fn

    def header(self, key, t0, t1):
        num, txt = C.STEP_TITLES[key]
        self.ov(type="header", num=num, text=txt, t0=t0, t1=t1)

    def camera_path(self, fn):
        for f in self.frames():
            loc, tgt, lens = fn(f)
            self.ct.set(f, loc, tgt, lens)

    def export(self):
        tracks = {k: [self.ct.project(f, fn(f)) for f in self.frames()] for k, fn in self._tracks.items()}
        return dict(name=self.name, n=self.n, overlays=self.overlays, cues=self.cues, tracks=tracks)

    # particle helpers ------------------------------------------------------
    def inst(self, proto):
        """A prototype key from PROTOS, or an object (e.g. a per-shot proto)."""
        return proto if isinstance(proto, bpy.types.Object) else self.P[proto]

    def proto(self, key, base, mat):
        """Per-shot copy of a prototype with its own (animatable) material."""
        me = self.P[base].data.copy()
        me.materials.clear()
        me.materials.append(mat)
        o = bpy.data.objects.new(f"{self.name}_proto_{key}", me)
        self.coll.objects.link(o)
        MD._hide_proto(o)
        return o

    def ballistic(self, name, proto, p0, v0, e, land, life, fade, s, sv=None, gravity=30.0, drag=0.0,
                  parent=None, spin=0.15, rot=None, final_rot=None):
        """final_rot: orientation each particle must have when it lands
        (rot is then solved from the spin and the flight time)."""
        n = len(p0)
        spinv = self.rng.normal(0, spin, (n, 3)) if np.isscalar(spin) else np.asarray(spin, float)
        if final_rot is not None:
            rot = np.asarray(final_rot, float) - spinv * np.asarray(land, float)[:, None]
        attrs = dict(p0=p0, v0=v0, e=e, land=land, life=life, fade=np.full(n, fade) if np.isscalar(fade) else fade,
                     s=s, sv=np.ones((n, 3)) if sv is None else np.broadcast_to(np.asarray(sv, float), (n, 3)),
                     rot=self.rng.uniform(0, TAU, (n, 3)) if rot is None else rot, spin=spinv)
        return fx.points_object(f"{self.name}_{name}", self.coll, attrs, fx.ballistic_group(),
                                {"Instance": self.inst(proto), "Gravity": gravity, "FPS": float(C.FPS),
                                 "Drag": drag, "ScaleMult": 1.0}, parent)

    def looping(self, name, proto, p0, vel, per, ph, s, sv=None, rot=None, spin=0.0, wob=0.0, wf=0.05,
                pop=0.0, density=1.0, parent=None):
        n = len(p0)
        rng = self.rng
        attrs = dict(p0=p0, vel=vel, per=per, ph=ph, s=s,
                     sv=np.ones((n, 3)) if sv is None else np.broadcast_to(np.asarray(sv, float), (n, 3)),
                     rot=rng.uniform(0, TAU, (n, 3)) if rot is None else rot,
                     spin=rng.normal(0, spin, (n, 3)) if np.isscalar(spin) else spin,
                     wob=np.full(n, wob) if np.isscalar(wob) else wob,
                     wf=np.full(n, wf) if np.isscalar(wf) else wf,
                     dens=rng.uniform(0, 1, n))
        o = fx.points_object(f"{self.name}_{name}", self.coll, attrs, fx.loop_group(),
                             {"Instance": self.inst(proto), "Density": density, "ScaleMult": 1.0,
                              "PopShape": pop}, parent)
        if isinstance(proto, str) and proto in ("sprite", "bubble", "oil_bubble", "wdrop"):
            # steam / foam: no shadows, not seen in reflections -> far cheaper
            for a in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission"):
                setattr(o, a, False)
        return o

    def static_points(self, name, proto, pts, s, sv=None, parent=None, rot=None):
        """Instances that never move (resting flakes, floating herbs)."""
        n = len(pts)
        per = np.full(n, 1e6)
        return self.looping(name, proto, pts, np.zeros((n, 3)), per, per * 0.5, s, sv=sv, parent=parent, rot=rot,
                            spin=np.zeros((n, 3)))

    def ambient(self, name, proto, N, box, s=(0.01, 0.03), sv=None, drift=0.0015):
        rng = self.rng
        p0 = np.stack([rng.uniform(*box[0], N), rng.uniform(*box[1], N), rng.uniform(*box[2], N)], 1)
        vel = np.stack([rng.normal(0, drift, N), rng.normal(0, drift, N), rng.uniform(0.3, 1.2, N) * drift], 1)
        per = rng.uniform(3000, 5000, N)
        ph = per * rng.uniform(0.4, 0.6, N)
        p0 = p0 - vel * ph[:, None]
        return self.looping(name, proto, p0, vel, per, ph, rng.uniform(*s, N), sv=sv, spin=0.01,
                            wob=rng.uniform(0.01, 0.04, N), wf=rng.uniform(0.02, 0.05, N))

    def steam(self, name, center, r, z, N, cam_loc, s=(0.3, 0.5), rise=(0.007, 0.012)):
        rng = self.rng
        th = rng.uniform(0, TAU, N)
        rr = r * np.sqrt(rng.uniform(0, 1, N))
        pts = np.stack([center[0] + rr * np.cos(th), center[1] + rr * np.sin(th), rng.uniform(*z, N)], 1)
        vel = np.stack([rng.normal(0, 0.0012, N), rng.normal(0, 0.0012, N), rng.uniform(*rise, N)], 1)
        rot = fx.face_camera_euler(pts, cam_loc)
        return self.looping(name, "sprite", pts, vel, rng.uniform(45, 70, N), rng.uniform(0, 70, N),
                            rng.uniform(*s, N), rot=rot, spin=np.zeros((N, 3)), wob=0.02, wf=0.05, density=0.0)


def hide_range(obj, frames, visible_fn):
    prev = None
    for f in frames:
        v = visible_fn(f)
        if v != prev:
            U.key(obj, f, hide=not v)
            prev = v


def hide_tree(obj, frames, visible_fn):
    hide_range(obj, frames, visible_fn)
    for ch in obj.children:
        hide_tree(ch, frames, visible_fn)


def key_density(obj, frames, fn):
    for f in frames:
        fx.key_input(obj, "FX", "Density", f, fn(f))


def disc_points(rng, n, r0, r1, z, center=(0.0, 0.0)):
    th = rng.uniform(0, TAU, n)
    rr = np.sqrt(rng.uniform(r0 ** 2, r1 ** 2, n))
    return np.stack([center[0] + rr * np.cos(th), center[1] + rr * np.sin(th), np.full(n, z)], 1)


def burst(rng, n, origin, spread, v_mean, v_sd):
    p0 = np.asarray(origin)[None, :] + rng.normal(0, spread, (n, 3))
    v0 = np.asarray(v_mean)[None, :] + rng.normal(0, v_sd, (n, 3))
    return p0, v0


# ---------------------------------------------------------------- helpers --
def aimed(rng, n, origin, spread, targets, frames=(9, 13), g=30.0):
    """Ballistic launches from a clump at `origin` that land on `targets`.
    Returns p0, v0 and the flight time in frames."""
    p0 = np.asarray(origin)[None, :] + rng.normal(0, spread, (n, 3))
    T = rng.uniform(*frames, n) / C.FPS
    v0 = (targets - p0 + np.stack([np.zeros(n), np.zeros(n), 0.5 * g * T * T], 1)) / T[:, None]
    return p0, v0, T * C.FPS


def sector(rng, n, center, r, z, rmax=0.82):
    """Points in a disc of radius r around center; any that fall beyond rmax
    from the pan centre are re-drawn closer in (no ring of clamped points)."""
    th = rng.uniform(0, TAU, n)
    rr = r * np.sqrt(rng.uniform(0, 1, n))
    pts = np.stack([center[0] + rr * np.cos(th), center[1] + rr * np.sin(th), np.full(n, z)], 1)
    rad = np.hypot(pts[:, 0], pts[:, 1])
    k = np.where(rad > rmax, rmax * np.sqrt(rng.uniform(0.55, 1.0, n)) / np.maximum(rad, 1e-6), 1.0)
    pts[:, 0] *= k
    pts[:, 1] *= k
    return pts


def flat_sv(rng, n, z=(0.5, 0.8)):
    return np.stack([np.ones(n), rng.uniform(0.75, 1.0, n), rng.uniform(*z, n)], 1)


def spline_path(keys, f):
    """Catmull-Rom through (frame, Vector) keys, parametrised by frame."""
    if f <= keys[0][0]:
        return Vector(keys[0][1])
    if f >= keys[-1][0]:
        return Vector(keys[-1][1])
    for i in range(len(keys) - 1):
        f0, f1 = keys[i][0], keys[i + 1][0]
        if f0 <= f <= f1:
            t = smooth((f - f0) / (f1 - f0)) * 0.35 + 0.65 * (f - f0) / (f1 - f0)
            p0 = Vector(keys[max(i - 1, 0)][1])
            p1, p2 = Vector(keys[i][1]), Vector(keys[i + 1][1])
            p3 = Vector(keys[min(i + 2, len(keys) - 1)][1])
            return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


def _empty(S, name, parent=None):
    e = bpy.data.objects.new(f"{S.name}_{name}", None)
    S.coll.objects.link(e)
    if parent is not None:
        e.parent = parent
    return e


# ------------------------------------------------------------ toppings -----
def shred_layout(n=1300, seed=42):
    """Resting shredded mozzarella on the raw pizza (shared by S4 and S5)."""
    rng = np.random.default_rng(seed)
    pts = disc_points(rng, n, 0.0, 0.93, 0.0)
    pts[:, 2] = TOP + 0.006 + rng.uniform(0, 0.013, n)
    s = rng.uniform(0.16, 0.26, n)
    sv = np.stack([np.ones(n), rng.uniform(0.8, 1.25, n), rng.uniform(0.8, 1.2, n)], 1)
    rot = np.stack([rng.normal(0, 0.12, n), rng.normal(0, 0.12, n), rng.uniform(0, TAU, n)], 1)
    return pts, s, sv, rot


def pep_layout(z):
    pts = np.array([(x, y, z) for x, y, rz, k in PEPS])
    rot = np.array([(0.0, 0.0, rz) for x, y, rz, k in PEPS])
    return pts, rot


def oregano_layout(z, n=170, seed=9):
    rng = np.random.default_rng(seed)
    pts = disc_points(rng, n, 0.0, 0.92, z)
    return pts, rng.uniform(0.008, 0.014, n)


def raw_base(S, prefix, flour=0.3):
    dm, dp = M.dough(f"{prefix}_dough")
    cm, _ = M.dough(f"{prefix}_crumb", cap=True)
    dp["flour"].outputs[0].default_value = flour
    base = MD.pizza_base(f"{prefix}_base", S.coll, keys=True, mats=[dm, cm])
    return base, dp


def baked_pizza(S, prefix, gap=0.0, hero_pull=0.0, oregano=True):
    """Baked pepperoni pizza cut into eight wedges.  Each wedge (base, sauce,
    cheese, pepperoni, oregano) is parented to its own empty so a slice can
    be pulled away.  Everything sits under the returned root."""
    root = _empty(S, f"{prefix}_pizza")
    dm, dp = M.dough(f"{prefix}_dough")
    dp["bake"].outputs[0].default_value = 1.0
    dp["flour"].outputs[0].default_value = 0.12
    cm, cp = M.dough(f"{prefix}_crumb", cap=True)
    cp["bake"].outputs[0].default_value = 1.0
    mz, mp = M.mozzarella(f"{prefix}_mozz")
    mp["melt"].outputs[0].default_value = 1.0
    mp["brown"].outputs[0].default_value = 0.85
    pm, pp = M.pepperoni(f"{prefix}_pep")
    pp["bake"].outputs[0].default_value = 1.0
    pep = S.proto("pep", "pep", pm)
    pep.data.shape_keys.key_blocks["cup"].value = 1.0
    opts, osz = oregano_layout(TOP + 0.024)
    oang = np.mod(np.arctan2(opts[:, 1], opts[:, 0]) - CUT_OFF, TAU)
    wedges = []
    for k in range(8):
        th0 = CUT_OFF + k * DW
        bis = th0 + DW / 2
        w = _empty(S, f"{prefix}_w{k}", root)
        w.rotation_mode = "QUATERNION"
        g = gap + (hero_pull if k == 0 else 0.0)
        w.location = (math.cos(bis) * g, math.sin(bis) * g, 0.0)
        b = MD.pizza_base(f"{prefix}_base{k}", S.coll, th0, th0 + DW, nseg=24, puff=1.0, mats=[dm, cm])
        b.parent = w
        sa = MD.pizza_layer(f"{prefix}_sauce{k}", S.coll, MD.PZ_SAUCE_R, MD.sauce_z, th0, th0 + DW, nseg=24,
                            rings=30, edge=0.02, seed=1.0, mat=M.pizza_sauce())
        sa.parent = w
        sa.location.z = TOP
        ch = MD.pizza_layer(f"{prefix}_cheese{k}", S.coll, MD.PZ_CHEESE_R, MD.cheese_z, th0, th0 + DW, nseg=24,
                            rings=30, edge=0.035, seed=5.0, mat=mz)
        ch.parent = w
        ch.location.z = TOP + 0.001
        so = ch.modifiers.new("Solidify", "SOLIDIFY")
        so.thickness = 0.01
        so.offset = -1.0
        pts = np.array([(x, y, TOP + 0.026) for x, y, rz, kk in PEPS if kk == k])
        rot = np.array([(0.0, 0.0, rz) for x, y, rz, kk in PEPS if kk == k])
        S.static_points(f"{prefix}_pep{k}", pep, pts, np.full(len(pts), MD.PEP_R), parent=w, rot=rot)
        if oregano:
            sel = (oang > k * DW + 0.02) & (oang < (k + 1) * DW - 0.02)
            S.static_points(f"{prefix}_oreg{k}", "oregano", opts[sel], osz[sel], parent=w)
        wedges.append(w)
    return root, wedges, dict(mozz=mz)


def served(S, prefix, gap=0.006, hero_pull=0.14):
    """Board + baked pizza, kept small in frame.  Returns (serve root, wedges)."""
    srv = _empty(S, f"{prefix}_serve")
    srv.scale = (PIZZA_SCALE,) * 3
    bd = MD.round_board(f"{prefix}_board", S.coll)
    bd.parent = srv
    root, wedges, parts = baked_pizza(S, prefix, gap=gap, hero_pull=hero_pull)
    root.parent = srv
    root.location.z = MD.ROUND_BOARD_TOP
    return srv, wedges, parts


def served_bvh():
    """Envelope of pizza + board (serve-local) for herb landings."""
    bt = MD.ROUND_BOARD_TOP
    prof = [(0.0, bt + TOP + 0.03), (0.97, bt + TOP + 0.03), (1.08, bt + 0.12), (1.2, bt + 0.165),
            (1.29, bt + 0.06), (1.32, bt), (1.5, bt)]
    me = MD.revolve_mesh("_serve_env", prof, 64, closed=False)
    b = fx.bvh_from_mesh(me)
    bpy.data.meshes.remove(me)
    return b


SERVE_TOP = (MD.ROUND_BOARD_TOP + TOP + 0.03) * PIZZA_SCALE


# ============================================================ S1 INTRO =====
def shot_intro(name, n):
    S = Shot(name, n, M.backdrop_world("W_intro", center=(0.5, 0.52), radius=0.85), fstop=4.0)
    MD.floor("S1_floor", S.coll, z=0.0)
    srv, wedges, _ = served(S, "S1")
    U.animate(srv, S.frames(), lambda f: dict(rot=(0, 0, -0.6 + 0.012 * f)))
    S.ambient("herbs", "herb", 36, box=((-2.2, 2.2), (-1.0, 3.0), (-0.2, 3.0)), s=(0.008, 0.016))
    S.ambient("cheese", "parm", 26, box=((-2.2, 2.2), (-1.0, 3.0), (-0.2, 3.0)), s=(0.01, 0.02))
    st = S.steam("steam", (0, 0), 0.7, (0.35, 0.7), 16, orbit((0, 0, 0.3), 7.0, math.radians(30), 0.0),
                 s=(0.3, 0.45))
    key_density(st, S.frames(), lambda f: 0.7)
    dive = Vector((0.15, -0.35, SERVE_TOP))

    def cam(f):
        t = ease_io(seg(f, 1, 48), 2)
        d = lerp(7.6, 5.6, t)
        el = math.radians(lerp(24, 34, t))
        az = lerp(-0.3, 0.08, t)
        tgt = Vector((0, 0, lerp(0.3, 0.2, t)))
        t2 = ease_in(seg(f, 48, 60), 2.4)
        if t2 > 0:
            d = lerp(d, 0.9, t2)
            tgt = tgt.lerp(dive, t2)
            el = lerp(el, math.radians(52), t2)
        return orbit(tgt, d, el, az), tgt, 50.0
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.2), k=0.42, rim=0.8, top=0.7)
    S.ov(type="fade_in", t0=1, t1=10)
    S.ov(type="kinetic", words=list(C.INTRO_WORDS), times=[8, 17, 26], t1=45)
    S.ov(type="subtitle", text="LET'S COOK", t0=38, t1=57)
    S.cue(1, "swell")
    for f in (8, 17, 26):
        S.cue(f, "tick")
    S.cue(48, "whoosh", dur=0.4, up=True)
    return S


# ====================================================== S2 INGREDIENTS =====
def _ingredient(S, key):
    e = bpy.data.objects.new(f"S2_{key}", None)
    S.coll.objects.link(e)

    def add(o, loc=(0, 0, 0), rot=(0, 0, 0), scl=1.0):
        o.parent = e
        o.location, o.rotation_euler, o.scale = loc, rot, (scl, scl, scl)
        return o
    base_rot = (0.3, 0, 0)
    rng = np.random.default_rng(5)
    if key == "dough":
        dm, dp = M.dough("S2_dough")
        dp["flour"].outputs[0].default_value = 0.55
        add(MD.dough_ball("S2_ball", S.coll, dm), (0, 0, -0.3), scl=0.85)
        base_rot = (0.3, 0, 0)
    elif key == "tomato":
        add(MD.dish("S2_tomdish", S.coll), (0, 0, -0.06), scl=0.4)
        add(MD.sauce_surface("S2_tom", S.coll, 0.77, MD.DISH_LIQ_Z, amp=0.02), (0, 0, -0.06 + MD.DISH_LIQ_Z * 0.4),
            scl=0.4)
        base_rot = (0.95, 0, 0)
    elif key in ("mozzarella", "oregano"):
        k = 0.42
        add(MD.dish(f"S2_{key}_dish", S.coll), (0, 0, -0.06), scl=k)
        N = 380 if key == "mozzarella" else 700
        r = 0.6 * np.sqrt(rng.uniform(0, 1, N))
        th = rng.uniform(0, TAU, N)
        h = 0.06 + 0.28 * np.clip(1 - (r / 0.62) ** 2, 0, 1) ** 0.8 * rng.uniform(0.7, 1.0, N) ** 0.4
        pts = np.stack([r * np.cos(th), r * np.sin(th), h], 1) * k + np.array([0, 0, -0.06])
        if key == "mozzarella":
            rot = np.stack([rng.normal(0, 0.4, N), rng.normal(0, 0.4, N), rng.uniform(0, TAU, N)], 1)
            S.static_points("S2_mozz", "shred", pts, rng.uniform(0.2, 0.3, N) * k, parent=e, rot=rot)
        else:
            S.static_points("S2_oreg", "oregano", pts, rng.uniform(0.025, 0.04, N) * k, parent=e)
        base_rot = (0.95, 0, 0)
    elif key == "pepperoni":
        pm, pp = M.pepperoni("S2_pep")
        add(MD.pepperoni_stick("S2_pstick", S.coll, pm), (-0.12, 0, -0.45), scl=0.72)
        for i in range(3):
            sl = MD.new_obj(f"S2_pslice{i}", S.P["pep"].data, S.coll)
            add(sl, (0.2 + 0.05 * i, -0.08 - 0.06 * i, -0.38 + 0.13 * i), (1.15, 0.0, 0.3 * i), 0.17)
            sl.data.materials[0] = pm
        base_rot = (0.3, 0.75, 0.3)
    elif key == "oil":
        add(MD.oil_bottle("S2_oil", S.coll), (0, 0, -0.42), scl=0.78)
        base_rot = (0.12, 0, 0.3)
    elif key == "garlic":
        add(MD.garlic_bulb("S2_garlic", S.coll), (0, 0, -0.25), scl=0.85)
        base_rot = (0.35, 0, 0)
    elif key == "basil":
        add(MD.basil_sprig("S2_basil", S.coll, n=5, L=0.5), (0, 0, -0.05), scl=0.95)
        base_rot = (0.95, 0, 0.3)
    elif key == "parmesan":
        add(MD.parmesan_wedge("S2_parm", S.coll), (-0.27, 0, -0.12), scl=0.75)
        base_rot = (0.5, 0, 0.6)
    return e, base_rot


def shot_ingredients(name, n):
    S = Shot(name, n, M.backdrop_world("W_ingr", center=(0.5, 0.5), radius=0.9), fstop=11.0)
    rows = [1.30, 0.05, -1.20]
    cols = [-1.02, 0.0, 1.02]
    cam_d = lambda f: lerp(9.2, 8.7, ease_io(seg(f, 1, n)))
    cam_az = lambda f: lerp(-0.06, 0.06, ease_io(seg(f, 1, n)))
    tgt = Vector((0, 0, -0.05))

    def cam_loc(f):
        return orbit(tgt, cam_d(f), math.radians(4), cam_az(f))
    for i, (key, label) in enumerate(C.INGREDIENTS):
        e, base_rot = _ingredient(S, key)
        col, row = i % 3, min(i // 3, len(rows) - 1)
        side = -1 if col == 0 else (1 if col == 2 else (-1 if row % 2 else 1))
        g = Vector((cols[col], 0.0, rows[row]))
        fi = 5 + 6 * i
        start = Vector((side * 3.4, -2.0, g.z + 0.9 * math.sin(i * 1.7)))
        exit_t0 = 91 + (i % 3)
        exit_dir = Vector((side * 4.5, 1.0, 1.2 * math.cos(i)))
        hero = key == "pepperoni"

        def pos(f, g=g, fi=fi, start=start, i=i, exit_t0=exit_t0, exit_dir=exit_dir, hero=hero):
            t = seg(f, fi, fi + 15)
            p = start.lerp(g, ease_out(t, 4))
            if f > fi + 15:
                p = p + Vector((0, 0, 0.03 * math.sin(TAU * (f - fi) / 45.0 + i)))
            if hero:
                te = ease_in(seg(f, 92, n), 2.5)
                cl = cam_loc(f)
                p = p.lerp(cl + (g - cl).normalized() * 0.9, te)
            else:
                p = p + exit_dir * ease_in(seg(f, exit_t0, exit_t0 + 13), 2.5)
            return p

        def fn(f, pos=pos, fi=fi, side=side, base_rot=base_rot, i=i, exit_t0=exit_t0, hero=hero):
            t = seg(f, fi, fi + 15)
            spin = (1 - ease_out(t, 3)) * side * 3.2
            sway = 0.07 * math.sin(TAU * (f - fi) / 70.0 + i) if f > fi + 15 else 0.0
            ex = 0.0 if hero else ease_in(seg(f, exit_t0, exit_t0 + 13), 2) * side * 2.0
            s = (0.35 + 0.65 * ease_back(t, 2.2))
            return dict(loc=pos(f), rot=(base_rot[0] + (1 - t) * 0.8, base_rot[1] + ex, base_rot[2] + spin + sway),
                        scl=(s, s, s))
        U.animate(e, S.frames(), fn)
        hide_tree(e, S.frames(), lambda f, fi=fi: f >= fi)
        S.track(f"ing{i}", lambda f, pos=pos: pos(f) + Vector((0, 0, -0.42)))
        S.ov(type="label", text=label, track=f"ing{i}", t0=fi + 11, t1=89, side="below", idx=i)
        S.cue(fi, "whoosh", dur=0.28, pitch=1.0 + 0.05 * i)
        S.cue(fi + 12, "pop", pitch=1.0 + 0.04 * i)
    ST.studio_rig(S.sc, (0, 0, -0.1), k=0.7, rim=1.0)
    S.ambient("dust", "flour", 30, box=((-2.0, 2.0), (-3.5, 2.0), (-3.2, 3.0)), s=(0.004, 0.009))
    S.camera_path(lambda f: (cam_loc(f), tgt, 50.0))
    S.ov(type="header", num="", text="THE INGREDIENTS", t0=3, t1=89)
    S.cue(92, "whoosh", dur=0.5, up=True)
    return S


# ========================================================== S3 STRETCH =====
def shot_stretch(name, n):
    S = Shot(name, n, M.backdrop_world("W_stretch", center=(0.5, 0.55), inner=(0.08, 0.05, 0.03), radius=0.9),
             fstop=5.6, lens=40)
    rng = S.rng
    MD.floor("S3_floor", S.coll, z=-0.12)
    MD.floured_board("S3_board", S.coll)
    base, dp = raw_base(S, "S3", flour=0.25)
    kb = base.data.shape_keys.key_blocks
    T_P0, T_P1, T_TOSS, T_LAND = 16, 42, 48, 74
    SC0 = 0.8
    HPEAK = 1.55

    def height(f):
        if T_TOSS <= f <= T_LAND:
            u = (f - T_TOSS) / (T_LAND - T_TOSS)
            return HPEAK * 4 * u * (1 - u)
        return 0.0

    def dough_fn(f):
        u = seg(f, T_TOSS, T_LAND)
        rz = 0.3 * ease_io(seg(f, T_P0, T_P1)) + TAU * 1.6 * ease_io(u, 1.3)
        rx = 0.16 * math.sin(TAU * u) if 0 < u < 1 else 0.0
        ry = 0.10 * math.sin(TAU * u * 1.5) if 0 < u < 1 else 0.0
        s = lerp(SC0, 1.0, ease_io(u))
        sxy, sz = 1.0, 1.0
        if f > T_LAND:
            imp = impact((f - T_LAND) / C.FPS, 3.5, 7.0)
            sz, sxy = 1 - 0.35 * imp, 1 + 0.05 * imp
        return dict(loc=(0, 0, height(f)), rot=(rx, ry, rz), scl=(s * sxy, s * sxy, s * sz))
    U.animate(base, S.frames(), dough_fn)
    for f in S.frames():
        U.key_prop(kb["ball"], "value", f, 1 - ease_io(seg(f, T_P0, T_P1), 1.8))
        U.key_socket(dp["flour"].outputs[0], f, 0.25 + 0.25 * smooth(seg(f, 6, 14)))
    # flour sprinkle onto the board and the dough ball
    N = 260
    tg = disc_points(rng, N, 0.0, 1.5, 0.0)
    p0, v0, land = aimed(rng, N, (0.1, 0.0, 2.6), 0.14, tg, frames=(13, 19), g=12.0)
    rr = np.hypot(tg[:, 0], tg[:, 1])
    life = np.where(rr < 0.42, land, 1e5)
    S.ballistic("flour", "flour", p0, v0, 2 + rng.uniform(0, 6, N), land, life, 1.0, rng.uniform(0.006, 0.012, N),
                gravity=12.0, spin=0.3)
    S.cue(2, "sprinkle", dur=0.6)
    # landing: flour bursts out from under the rim
    Nb = 160
    th = rng.uniform(0, TAU, Nb)
    r0 = rng.uniform(1.1, 1.3, Nb)
    p0 = np.stack([r0 * np.cos(th), r0 * np.sin(th), rng.uniform(0.01, 0.05, Nb)], 1)
    sp = rng.uniform(0.6, 1.4, Nb)
    v0 = np.stack([sp * np.cos(th), sp * np.sin(th), rng.uniform(0.6, 1.6, Nb)], 1)
    land = fx.landing(p0, v0, 12.0, drag=2.0, floor_z=0.0, max_frames=60)
    S.ballistic("flour_burst", "flour", p0, v0, T_LAND + rng.uniform(0, 2, Nb), land, np.full(Nb, 1e5), 1.0,
                rng.uniform(0.006, 0.011, Nb), gravity=12.0, drag=2.0, spin=0.3)
    cam0 = orbit((0, 0, 0.3), 6.6, math.radians(36), -0.1)
    puff = S.steam("puff", (0, 0), 1.25, (0.03, 0.25), 30, cam0, s=(0.35, 0.7), rise=(0.003, 0.007))
    key_density(puff, S.frames(), lambda f: 0.45 * smooth(seg(f, 8, 12)) * (1 - smooth(seg(f, 22, 34)))
                + 0.9 * smooth(seg(f, T_LAND, T_LAND + 3)) * (1 - smooth(seg(f, 88, n))))
    S.cue(9, "puff", size=0.5)
    S.cue(T_P0, "squeeze", dur=0.8)
    S.cue(T_TOSS, "whoosh", dur=0.5, up=True)
    S.cue(T_LAND - 6, "whoosh", dur=0.25)
    S.cue(T_LAND, "thud", size=0.7, soft=True)
    S.cue(T_LAND + 1, "puff", size=1.0)

    def cam(f):
        tgt = Vector((0, 0, 0.25 + 0.45 * height(f)))
        d, el, az, lens = 6.6, math.radians(36), -0.12 + 0.0015 * f, 40.0
        t = ease_io(seg(f, 76, n), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0.25, -0.3, 0.05)), t)
            d, el = lerp(d, 4.9, t), lerp(el, math.radians(46), t)
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.2), k=0.24, rim=0.7, top=0.4)
    S.header("stretch", 3, 98)
    S.track("rim", lambda f: Vector((0.84, -0.84, 0.08)))
    S.ov(type="callout", text="LEAVE A PUFFY EDGE", track="rim", t0=84, t1=n, dx=-150, dy=250)
    return S


# ============================================================== S4 TOP ======
def shot_top(name, n):
    S = Shot(name, n, M.backdrop_world("W_top", center=(0.5, 0.55), inner=(0.08, 0.05, 0.03), radius=0.9),
             fstop=5.6, lens=40)
    rng = S.rng
    MD.floor("S4_floor", S.coll, z=-0.12)
    MD.floured_board("S4_board", S.coll)
    base, dp = raw_base(S, "S4", flour=0.4)
    base.data.shape_keys.key_blocks["ball"].value = 0.0
    # ---- 02 SAUCE: a dollop lands and is spread out in a spiral ----------
    T_BLOB, T_HIT, T_SP0, T_SP1, T_OUT = 3, 10, 14, 48, 54
    sauce = MD.pizza_layer("S4_sauce", S.coll, MD.PZ_SAUCE_R, MD.sauce_z, mat=M.pizza_sauce())

    def rad(f):
        return lerp(0.22, 1.0, ease_io(seg(f, T_SP0, T_SP1), 1.4))
    U.animate(sauce, S.frames(), lambda f: dict(loc=(0, 0, TOP), scl=(rad(f), rad(f),
                                                                     lerp(5.0, 1.0, smooth(seg(f, T_HIT, T_SP1))))))
    hide_range(sauce, S.frames(), lambda f: f >= T_HIT)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.16)
    for fc in bm.faces:
        fc.smooth = True
    me = bpy.data.meshes.new("S4_blob")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M.pizza_sauce())
    blob = MD.new_obj("S4_blob", me, S.coll)
    U.animate(blob, S.frames(), lambda f: dict(loc=(0, 0, lerp(2.2, TOP + 0.1, ease_in(seg(f, T_BLOB, T_HIT), 2))),
                                              scl=(0.9, 0.9, lerp(1.35, 1.0, seg(f, T_BLOB, T_HIT)))))
    hide_range(blob, S.frames(), lambda f: T_BLOB <= f < T_HIT)
    spn = MD.spoon("S4_spoon", S.coll)

    def place(f):
        u = ease_io(seg(f, T_SP0, T_SP1), 1.4)
        r = max(0.0, rad(f) - 0.15)
        a = 0.4 + TAU * 2.3 * u
        c = Vector((r * math.cos(a), r * math.sin(a), TOP + 0.03))
        d = (Vector((math.cos(a), math.sin(a), 0)) * 0.3 + Vector((0.0, -0.35, 1.0))).normalized()
        lift = 1.8 * (1 - ease_out(seg(f, T_HIT, T_SP0 + 1), 3)) + 1.8 * ease_in(seg(f, T_SP1, T_OUT), 2.5)
        q = d.to_track_quat("Z", "Y")
        return dict(loc=c + Vector((0.3, -0.5, 1.0)) * lift, rot=tuple(q.to_euler()))
    U.animate(spn, S.frames(), place)
    hide_range(spn, S.frames(), lambda f: T_HIT <= f <= T_OUT)
    S.cue(T_BLOB + 2, "whoosh", dur=0.25)
    S.cue(T_HIT, "splat")
    S.cue(T_SP0, "stir", dur=1.1)
    S.header("sauce", 3, 54)
    # ---- 03 TOP: mozzarella rains down, then the pepperoni ------------------
    pts, s, sv, rot = shred_layout()
    N = len(pts)
    p0 = pts + np.stack([rng.normal(0, 0.12, N), rng.normal(0, 0.12, N) - 0.1, rng.uniform(1.8, 2.6, N)], 1)
    T = rng.uniform(9, 13, N) / C.FPS
    v0 = (pts - p0 + np.stack([np.zeros(N), np.zeros(N), 0.5 * 30.0 * T * T], 1)) / T[:, None]
    S.ballistic("shreds", "shred", p0, v0, 56 + rng.uniform(0, 14, N), T * C.FPS, np.full(N, 1e5), 1.0, s, sv=sv,
                spin=0.2, final_rot=rot)
    S.cue(58, "sprinkle", dur=0.9)
    ppts, prot = pep_layout(TOP + 0.036)
    Np = len(ppts)
    order = np.argsort(np.mod(np.arctan2(ppts[:, 1], ppts[:, 0]) + 1.2, TAU) + 0.3 * np.hypot(ppts[:, 0], ppts[:, 1]))
    e = np.empty(Np)
    e[order] = 84 + np.arange(Np) * 1.0
    origin = ppts * 0.4 + np.array([0.0, -0.5, 1.9]) + rng.normal(0, 0.1, (Np, 3))
    T = rng.uniform(8, 11, Np) / C.FPS
    v0 = (ppts - origin + np.stack([np.zeros(Np), np.zeros(Np), 0.5 * 30.0 * T * T], 1)) / T[:, None]
    spin = np.stack([rng.normal(0, 0.15, Np), rng.normal(0, 0.15, Np), rng.normal(0, 0.08, Np)], 1)
    S.ballistic("pep", "pep", origin, v0, e, T * C.FPS, np.full(Np, 1e5), 1.0, np.full(Np, MD.PEP_R),
                spin=spin, final_rot=prot)
    for j in range(0, Np, 3):
        i = order[j]
        S.cue(e[i] + T[i] * C.FPS, "pop", pitch=0.85 + 0.02 * j)
    opts, osz = oregano_layout(TOP + 0.033)
    No = len(opts)
    p0, v0, land = aimed(rng, No, (0.2, -0.1, 2.2), 0.15, opts, frames=(10, 14))
    S.ballistic("oregano", "oregano", p0, v0, 114 + rng.uniform(0, 8, No), land, np.full(No, 1e5), 1.0, osz,
                spin=0.3)
    S.cue(114, "sprinkle", dur=0.5)
    S.header("top", 56, 130)
    S.track("mozz", lambda f: Vector((0.45, -0.38, TOP + 0.03)))
    S.ov(type="label", text="MOZZARELLA", track="mozz", t0=70, t1=104, side="right")
    early = np.where(e < 94)[0]
    front = int(early[np.argmin(ppts[early, 1] + 0.3 * np.abs(ppts[early, 0]))])
    fp = Vector(ppts[front])
    S.track("pep", lambda f: fp + Vector((0, 0, 0.01)))
    S.ov(type="label", text="PEPPERONI", track="pep", t0=max(98, e[front] + 10), t1=n, side="left")

    def cam(f):
        tgt = Vector((0, 0, 0.05))
        d, el, az, lens = 6.0, math.radians(64), -0.15 + 0.0016 * f, 40.0
        t = ease_io(seg(f, 104, n), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0.1, -0.2, 0.05)), t)
            d, el = lerp(d, 4.7, t), lerp(el, math.radians(54), t)
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.05), k=0.27, rim=0.6, top=0.6)
    return S


# ============================================================= S5 BAKE ======
def shot_bake(name, n):
    S = Shot(name, n, M.backdrop_world("W_bake", center=(0.5, 0.5), inner=(0.03, 0.02, 0.015), radius=0.9),
             fstop=5.6, lens=35)
    rng = S.rng
    MD.oven("S5_oven", S.coll)
    fm = M.flame()
    fw = fm.node_tree.nodes["fw"].outputs[0]
    U.key_socket(fw, 1, 0.0)
    U.key_socket(fw, n, n * 0.07)
    for i, (x, y, r, h) in enumerate([(-2.4, 2.0, 0.28, 1.5), (-2.0, 2.4, 0.30, 1.8), (-1.7, 2.1, 0.22, 1.2),
                                      (-2.6, 2.5, 0.24, 1.3), (-2.2, 1.7, 0.20, 1.0), (-1.9, 2.7, 0.22, 1.4),
                                      (-2.5, 2.2, 0.18, 0.9)]):
        o = MD.flame_tongue(f"S5_flame{i}", S.coll, r, h, seed=i)
        o.location = (x, y, 0.15)
    for i, (loc, en) in enumerate([((-2.0, 2.0, 0.7), 1400.0), ((-1.5, 2.3, 1.6), 700.0)]):
        ld = bpy.data.lights.new(f"S5_fire{i}", "POINT")
        ld.color = (1.0, 0.5, 0.18)
        ld.shadow_soft_size = 0.5
        lo = bpy.data.objects.new(f"S5_fire{i}", ld)
        S.coll.objects.link(lo)
        lo.location = loc
        for f in S.frames():
            U.key_prop(ld, "energy", f, en * (1 + 0.18 * math.sin(f * 0.9 + i) + 0.1 * math.sin(f * 2.3 + 2 * i)))
    REST = Vector((0.0, -0.55, 0.0))
    ST.area(S.sc, "S5_key", (1.2, -7.5, 3.4), REST, 1600, (3.0, 3.0), (1.0, 0.93, 0.85))
    ST.area(S.sc, "S5_top", (0.6, -0.9, 3.6), REST, 240, (2.0, 2.0), (1.0, 0.9, 0.8))
    # ---- the raw pizza on its peel ----------------------------------------
    pz = _empty(S, "pizza")
    base, dp = raw_base(S, "S5", flour=0.3)
    base.parent = pz
    kb = base.data.shape_keys.key_blocks
    kb["ball"].value = 0.0
    sauce = MD.pizza_layer("S5_sauce", S.coll, MD.PZ_SAUCE_R, MD.sauce_z, mat=M.pizza_sauce())
    sauce.parent = pz
    sauce.location.z = TOP
    mz, mp = M.mozzarella("S5_mozz")
    shred = S.proto("shred", "shred", mz)
    sink = _empty(S, "sink", pz)
    pts, s, sv, rot = shred_layout()
    shreds = S.static_points("shreds", shred, pts, s, sv=sv, rot=rot, parent=sink)
    for f in S.frames():
        fx.key_input(shreds, "FX", "ScaleMult", f, 1.0 - smooth(seg(f, 58, 84)))
    sheet = MD.pizza_layer("S5_cheese", S.coll, MD.PZ_CHEESE_R, MD.cheese_z, edge=0.035, seed=5.0, mat=mz)
    sheet.parent = pz
    pm, pp = M.pepperoni("S5_pep")
    pep = S.proto("pep", "pep", pm)
    psink = _empty(S, "psink", pz)
    ppts, prot = pep_layout(TOP + 0.036)
    S.static_points("pep", pep, ppts, np.full(len(ppts), MD.PEP_R), rot=prot, parent=psink)
    opts, osz = oregano_layout(TOP + 0.033)
    S.static_points("oregano", "oregano", opts, osz, parent=psink)
    bpts = disc_points(rng, 70, 0.05, 0.9, TOP + 0.022)
    bub = S.looping("bubbles", "cbubble", bpts, np.zeros_like(bpts), rng.uniform(14, 26, 70), rng.uniform(0, 26, 70),
                    rng.uniform(0.02, 0.04, 70), sv=(1, 1, 0.65), pop=1.0, density=0.0, parent=pz)
    key_density(bub, S.frames(), lambda f: 0.75 * smooth(seg(f, 50, 62)))
    sk_melt = shred.data.shape_keys.key_blocks["melt"]
    sk_cup = pep.data.shape_keys.key_blocks["cup"]
    for f in S.frames():
        U.key_prop(kb["puff"], "value", f, ease_io(seg(f, 26, 72), 1.6))
        U.key_socket(dp["bake"].outputs[0], f, smooth(seg(f, 30, 96)))
        U.key_socket(dp["flour"].outputs[0], f, 0.3 - 0.18 * smooth(seg(f, 30, 80)))
        U.key_socket(mp["melt"].outputs[0], f, smooth(seg(f, 26, 58)))
        U.key_socket(mp["brown"].outputs[0], f, 0.9 * smooth(seg(f, 56, 100)))
        U.key_prop(sk_melt, "value", f, ease_io(seg(f, 28, 62), 1.6))
        U.key_socket(pp["bake"].outputs[0], f, smooth(seg(f, 36, 96)))
        U.key_prop(sk_cup, "value", f, ease_io(seg(f, 46, 90), 1.6))
        U.key(sink, f, loc=(0, 0, -0.019 * smooth(seg(f, 34, 74))))
        U.key(psink, f, loc=(0, 0, -0.011 * smooth(seg(f, 28, 62))))
        U.key(sheet, f, loc=(0, 0, lerp(TOP - 0.022, TOP, smooth(seg(f, 30, 64)))))
    pl = MD.peel("S5_peel", S.coll)
    T_IN1, T_OUT0, T_OUT1 = 20, 24, 38

    def peel_y(f):
        y = lerp(-6.6, REST.y, ease_out(seg(f, 1, T_IN1), 2.5))
        return lerp(y, -9.8, ease_in(seg(f, T_OUT0, T_OUT1), 2.2))
    U.animate(pl, S.frames(), lambda f: dict(loc=(0, peel_y(f), 0.012)))
    hide_tree(pl, S.frames(), lambda f: f <= T_OUT1 + 1)
    U.animate(pz, S.frames(), lambda f: dict(loc=(0, peel_y(f), 0.012) if f < T_OUT0 else tuple(REST)))
    S.cue(1, "crackle", dur=n / C.FPS)
    S.cue(2, "whoosh", dur=0.6)
    S.cue(T_IN1, "clack")
    S.cue(T_OUT0 + 1, "whoosh", dur=0.4)
    S.cue(50, "sizzle_soft", dur=1.9)
    cam_keys = [(1, (0.35, -8.9, 1.38)), (24, (0.25, -7.6, 1.42)), (46, (0.0, -3.65, 1.48)),
                (64, (0.04, -2.9, 2.4)), (n, (0.3, -2.7, 2.3))]
    tgt_keys = [(1, (0.0, -1.6, 0.45)), (24, (0.0, -1.2, 0.4)), (46, (0.0, -0.75, 0.15)),
                (64, (0.0, -0.6, 0.05)), (n, (0.12, -0.72, 0.06))]
    S.camera_path(lambda f: (spline_path(cam_keys, f), spline_path(tgt_keys, f), lerp(32, 38, smooth(seg(f, 30, n)))))
    S.header("bake", 3, 98)
    S.ov(type="haze", t0=30, t1=n, y0=0.0, y1=0.6, amp=1.4)
    S.track("bub", lambda f: Vector((0.32, -1.0, TOP + 0.03)))
    S.ov(type="callout", text="BUBBLING & GOLDEN", track="bub", t0=84, t1=n, dx=-150, dy=-330)
    return S


# ============================================================ S6 SLICE ======
def shot_slice(name, n):
    S = Shot(name, n, M.backdrop_world("W_slice", center=(0.5, 0.55), radius=0.9), fstop=5.6, lens=40)
    rng = S.rng
    MD.floor("S6_floor", S.coll, z=0.0)
    MD.round_board("S6_board", S.coll)
    root, wedges, parts = baked_pizza(S, "S6")
    root.location.z = MD.ROUND_BOARD_TOP
    G = 0.007
    passes = [(0, 6, 15), (2, 18, 27), (1, 30, 38), (3, 40, 48)]   # (cut ray j, start, end)

    def gap_disp(k, f):
        v = Vector((0, 0, 0))
        for j, t0, t1 in passes:
            e = ease_out(seg(f, t1 - 2, t1 + 3), 2)
            for ci in (j, j + 4):
                c = CUT_OFF + ci * DW
                perp = Vector((-math.sin(c), math.cos(c), 0))
                if k == ci % 8:
                    v += perp * G * e
                if k == (ci - 1) % 8:
                    v -= perp * G * e
        return v
    T_P0, T_P1 = 54, 98
    bis0 = CUT_OFF + DW / 2
    bdir = Vector((math.cos(bis0), math.sin(bis0), 0))
    tax = Vector((-math.sin(bis0), math.cos(bis0), 0))

    def pull(f):
        u = ease_io(seg(f, T_P0, T_P1), 1.7)
        lift = 0.55 * ease_out(seg(f, T_P0, T_P1 - 8), 2)
        return bdir * 1.15 * u + Vector((0, 0, lift)), 0.32 * ease_io(seg(f, T_P0, T_P1 - 10))
    for k, w in enumerate(wedges):
        for f in S.frames():
            loc = gap_disp(k, f)
            q = Quaternion()
            if k == 0:
                dl, al = pull(f)
                loc = loc + dl
                q = Quaternion(tax, -al)
            U.key(w, f, loc=loc, quat=q)
    # ---- pizza wheel: four passes through the centre ------------------------
    cr, spin = MD.cutter("S6_cutter", S.coll)
    cr.parent = root
    RW, REACH = 0.36, 1.45
    CZ = RW - 0.006

    def pass_pts(j):
        c = CUT_OFF + j * DW
        d = Vector((math.cos(c), math.sin(c), 0))
        return -d * REACH + Vector((0, 0, CZ)), d * REACH + Vector((0, 0, CZ)), c - math.pi / 2
    dist = {}

    def cutter_state(f):
        if f < passes[0][1]:
            a, _, rz = pass_pts(passes[0][0])
            u = ease_out(seg(f, 1, passes[0][1]), 2.5)
            return Vector((1.8, -1.2, 2.6)).lerp(a, u), rz, 0.0
        acc = 0.0
        for i, (j, t0, t1) in enumerate(passes):
            a, b, rz = pass_pts(j)
            if f <= t1:
                u = ease_io(seg(f, t0, t1), 1.3)
                return a.lerp(b, u), rz, acc + 2 * REACH * u
            acc += 2 * REACH
            nxt = passes[i + 1] if i + 1 < len(passes) else None
            if nxt and f < nxt[1]:
                a2, _, rz2 = pass_pts(nxt[0])
                u = smooth(seg(f, t1, nxt[1]))
                p = b.lerp(a2, u) + Vector((0, 0, 0.7 * math.sin(math.pi * u)))
                dr = (rz2 - rz + math.pi) % TAU - math.pi
                return p, rz + dr * u, acc
        _, b, rz = pass_pts(passes[-1][0])
        u = ease_in(seg(f, passes[-1][2], passes[-1][2] + 8), 2)
        return b.lerp(Vector((2.6, 0.8, 2.8)), u), rz, acc
    for f in S.frames():
        p, rz, dd = cutter_state(f)
        U.key(cr, f, loc=p, rot=(0, 0, rz))
        U.key(spin, f, rot=(-dd / RW, 0, 0))
    hide_tree(cr, S.frames(), lambda f: f <= passes[-1][2] + 8)
    for j, t0, t1 in passes:
        S.cue(t0 + 1, "crunch", size=0.55)
        S.cue(t1 - 1, "crunch", size=0.4)
    # ---- molten cheese strings between the hero slice and its neighbours ----
    NS, K = 64, 22
    chains, A, BL, Uu, BRK, RR, SD = [], [], [], [], [], [], []
    for i in range(NS):
        edge = i % 2
        c = CUT_OFF + edge * DW
        r = 0.06 + 0.88 * rng.uniform(0, 1) ** 0.85
        z = TOP + 0.013 + rng.uniform(-0.004, 0.006)
        p = Vector((r * math.cos(c), r * math.sin(c), z))
        nk = 7 if edge == 0 else 1
        a = p + gap_disp(nk, n)
        brk, rr, sd = rng.uniform(0.55, 1.5), rng.uniform(0.45, 1.25), rng.uniform(0, 50)
        chains.append(np.repeat(np.array(a)[None, :], K, 0))
        for q in range(K):
            A.append(tuple(a))
            BL.append(tuple(p))
            Uu.append(q / (K - 1))
            BRK.append(brk)
            RR.append(rr)
            SD.append(sd)
    fx.strands_object("S6_strings", S.coll, chains, dict(a=A, bl=BL, u=Uu, brk=BRK, rr=RR, sd=SD),
                      fx.cheese_pull_group(), {"Slice": wedges[0], "Radius": 0.014, "Sag": 0.3,
                                               "Material": parts["mozz"]}, parent=root)
    S.cue(T_P0 - 2, "whoosh", dur=0.4, up=True)
    S.cue(T_P0 + 2, "squeeze", dur=1.3)

    def cam(f):
        tgt = Vector((0, 0, 0.12))
        d, el, az, lens = 6.2, math.radians(58), 0.05 + 0.0015 * f, 40.0
        t = ease_io(seg(f, 44, 72), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0.0, -0.95, 0.34)), t)
            d, el, az, lens = lerp(d, 5.5, t), lerp(el, math.radians(17), t), lerp(az, -1.42, t), lerp(40, 34, t)
        t2 = ease_io(seg(f, 72, n), 1.5)
        if t2 > 0:
            tgt = tgt + Vector((0, -0.12, 0.14)) * t2
            d -= 0.25 * t2
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.15), k=0.4, rim=0.8, top=0.7)
    S.header("slice", 3, 50)
    S.track("pull", lambda f: Vector((0, -0.55, MD.ROUND_BOARD_TOP + TOP + 0.05)) + pull(f)[0] * 0.5)
    S.ov(type="callout", text="THE CHEESE PULL", track="pull", t0=78, t1=n, dx=-160, dy=-330)
    return S


# =========================================================== S7 FINAL ======
def shot_final(name, n):
    S = Shot(name, n, M.backdrop_world("W_final", center=(0.5, 0.58), inner=(0.11, 0.06, 0.03), radius=0.85),
             fstop=4.0, lens=50)
    rng = S.rng
    MD.floor("S7_floor", S.coll, z=0.0)
    srv, wedges, _ = served(S, "S7")
    U.animate(srv, S.frames(), lambda f: dict(rot=(0, 0, 0.3 + 0.006 * f)))
    bt = MD.ROUND_BOARD_TOP + TOP + 0.045
    for i, (x, y, rz, L) in enumerate([(0.25, 0.32, 0.6, 0.34), (-0.42, -0.08, 2.7, 0.3), (0.08, -0.5, 4.4, 0.28)]):
        lf = MD.basil_leaf(f"S7_basil{i}", S.coll, L, seed=i + 3)
        lf.parent = srv
        t0 = 12 + 5 * i
        r0 = Euler((0.1, -0.15, rz))

        def fn(f, x=x, y=y, r0=r0, t0=t0):
            u = seg(f, t0, t0 + 10)
            z = bt + 1.6 * (1 - ease_in(u, 2))
            if f > t0 + 10:
                z += 0.02 * impact((f - t0 - 10) / C.FPS, 3.0, 8.0)
            return dict(loc=(x, y, z), rot=(r0.x + 0.6 * (1 - u), r0.y, r0.z + 1.5 * (1 - u)))
        U.animate(lf, S.frames(), fn)
        hide_range(lf, S.frames(), lambda f, t0=t0: f >= t0)
        S.cue(t0 + 10, "pop", pitch=0.8 + 0.1 * i)
    N = 300
    p0 = np.stack([rng.uniform(-0.8, 0.8, N), rng.uniform(-0.8, 0.8, N), rng.uniform(3.0, 4.0, N)], 1)
    v0 = np.stack([rng.normal(0, 0.08, N), rng.normal(0, 0.08, N), rng.uniform(-0.6, -0.2, N)], 1)
    land = fx.landing(p0, v0, 6.0, drag=1.5, bvh=served_bvh(), floor_z=MD.ROUND_BOARD_TOP, max_frames=80)
    S.ballistic("herbs", "herb", p0, v0, 30 + rng.uniform(0, 24, N), land, np.full(N, 1e5), 1.0,
                rng.uniform(0.009, 0.016, N), gravity=6.0, drag=1.5, parent=srv, spin=0.6)
    S.cue(32, "sprinkle", dur=1.0)
    cam_el = lambda f: math.radians(lerp(24, 28, ease_io(seg(f, 1, n))))
    cam_d = lambda f: lerp(6.9, 6.4, ease_io(seg(f, 1, n)))
    tgt = Vector((0, 0, 0.78))

    def cam(f):
        return orbit(tgt, cam_d(f), cam_el(f), 0.0), tgt, 50.0
    lines = [(C.FINAL_TEXT[0], 0.105, "cream", 2.12, 1.2),
             (C.FINAL_TEXT[1], 0.17, "gold", 1.88, 1.1),
             (C.FINAL_TEXT[2], 0.36, "cream", 1.5, 1.0)]
    el0 = cam_el(60)
    for j, (txt, size, matk, z, sp) in enumerate(lines):
        o = MD.text3d(f"S7_title{j}", S.coll, txt, C.FONT_BLACK, size=size, extrude=size * 0.12,
                      bevel=size * 0.025, mat=M.text_mat(matk), spacing=sp)
        t0 = 20 + 7 * j

        def fn(f, t0=t0, z=z, j=j):
            t = seg(f, t0, t0 + 13)
            eb = ease_back(t, 2.0)
            s = 0.6 + 0.4 * eb
            fl = 0.01 * math.sin(TAU * (f - t0) / 60.0 + j)
            return dict(loc=(0, 0.6, z - 0.12 * (1 - ease_out(t)) + fl),
                        rot=(math.pi / 2 - el0 - 1.3 * (1 - eb), 0, 0), scl=(s, s, s))
        U.animate(o, S.frames(), fn)
        hide_range(o, S.frames(), lambda f, t0=t0: f >= t0)
        S.cue(t0, "whoosh", dur=0.25, pitch=0.9 + 0.1 * j)
        S.cue(t0 + 6, "slam", size=0.45 + 0.2 * j)
    sw = ST.area(S.sc, "S7_sweep", (-2.5, 1.2, 1.6), (0, 0, 0.3), 0, (0.25, 3.0), (1.0, 0.85, 0.6))
    for f in S.frames():
        t = seg(f, 36, 90)
        sw.location = (lerp(-2.6, 2.6, ease_io(t)), 1.4, 1.4)
        sw.keyframe_insert("location", frame=f)
        U.key_prop(sw.data, "energy", f, 700 * math.sin(math.pi * t))
    st = S.steam("steam", (0, 0), 0.7, (0.3, 0.6), 14, cam(60)[0], s=(0.3, 0.45))
    key_density(st, S.frames(), lambda f: 0.7)
    S.ambient("herbs_bg", "herb", 36, box=((-2.0, 2.0), (0.6, 3.0), (-0.2, 3.0)), s=(0.008, 0.015))
    S.ambient("cheese_bg", "parm", 24, box=((-2.0, 2.0), (0.6, 3.0), (-0.2, 3.0)), s=(0.01, 0.02))
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.2), k=0.42, rim=0.8, top=0.7)
    S.cue(1, "boom")
    S.ov(type="sparkle", t0=40, t1=n)
    return S


BUILDERS = {
    "S1_intro": shot_intro,
    "S2_ingredients": shot_ingredients,
    "S3_stretch": shot_stretch,
    "S4_top": shot_top,
    "S5_bake": shot_bake,
    "S6_slice": shot_slice,
    "S7_final": shot_final,
}
