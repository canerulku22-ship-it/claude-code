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
from mathutils import Vector, Euler, Matrix

import config as C
from . import util as U, materials as M, models as MD, stage as ST, fx
from .util import (seg, lerp, ease_out, ease_in, ease_io, ease_back, smooth, impact, squash_scale)

TAU = 2 * math.pi
HC = 0.078            # chicken centre height above its origin
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

    def camera_path(self, fn):
        for f in self.frames():
            loc, tgt, lens = fn(f)
            self.ct.set(f, loc, tgt, lens)

    def export(self):
        tracks = {k: [self.ct.project(f, fn(f)) for f in self.frames()] for k, fn in self._tracks.items()}
        return dict(name=self.name, n=self.n, overlays=self.overlays, cues=self.cues, tracks=tracks)

    # particle helpers ------------------------------------------------------
    def ballistic(self, name, proto, p0, v0, e, land, life, fade, s, sv=None, gravity=30.0, drag=0.0,
                  parent=None, spin=0.15):
        n = len(p0)
        attrs = dict(p0=p0, v0=v0, e=e, land=land, life=life, fade=np.full(n, fade) if np.isscalar(fade) else fade,
                     s=s, sv=np.ones((n, 3)) if sv is None else np.broadcast_to(np.asarray(sv, float), (n, 3)),
                     rot=self.rng.uniform(0, TAU, (n, 3)), spin=self.rng.normal(0, spin, (n, 3)))
        return fx.points_object(f"{self.name}_{name}", self.coll, attrs, fx.ballistic_group(),
                                {"Instance": self.P[proto], "Gravity": gravity, "FPS": float(C.FPS),
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
                             {"Instance": self.P[proto], "Density": density, "ScaleMult": 1.0,
                              "PopShape": pop}, parent)
        if proto in ("sprite", "bubble"):
            # steam / foam: no shadows, not seen in reflections -> far cheaper
            for a in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission"):
                setattr(o, a, False)
        return o

    def ambient(self, name, proto, N, center=(0, 0, 0), r=(0.8, 2.4), z=(-0.5, 1.5), s=(0.01, 0.03),
                sv=None, drift=0.0015, box=None):
        rng = self.rng
        if box is not None:
            p0 = np.stack([rng.uniform(*box[0], N), rng.uniform(*box[1], N), rng.uniform(*box[2], N)], 1)
        else:
            th = rng.uniform(0, TAU, N)
            rr = np.sqrt(rng.uniform(r[0] ** 2, r[1] ** 2, N))
            p0 = np.stack([center[0] + rr * np.cos(th), center[1] + rr * np.sin(th),
                           center[2] + rng.uniform(*z, N)], 1)
        vel = np.stack([rng.normal(0, drift, N), rng.normal(0, drift, N), rng.uniform(0.3, 1.2, N) * drift], 1)
        per = rng.uniform(3000, 5000, N)
        ph = per * rng.uniform(0.4, 0.6, N)
        p0 = p0 - vel * ph[:, None]
        if sv is None:
            sv = np.stack([np.ones(N), rng.uniform(0.6, 1.0, N), rng.uniform(0.4, 0.8, N)], 1)
        return self.looping(name, proto, p0, vel, per, ph, rng.uniform(*s, N), sv=sv, spin=0.01,
                            wob=rng.uniform(0.01, 0.04, N), wf=rng.uniform(0.02, 0.05, N))


def hide_range(obj, frames, visible_fn):
    prev = None
    for f in frames:
        v = visible_fn(f)
        if v != prev:
            U.key(obj, f, hide=not v)
            prev = v


def chicken_outline(rng, n, rz=0.0, grow=(0.0, 0.1), z=0.0, center=(0, 0)):
    th = rng.uniform(0, TAU, n)
    R = 1 + 0.06 * np.sin(2 * th + 0.7) + 0.045 * np.sin(3 * th + 2.1) + 0.03 * np.sin(5 * th + 0.4)
    x = 0.64 * R * np.cos(th)
    y = 0.52 * R * np.sin(th)
    d = rng.uniform(*grow, n)
    nx, ny = np.cos(th), np.sin(th)
    x, y = x + nx * d, y + ny * d
    c, s = math.cos(rz), math.sin(rz)
    X = c * x - s * y + center[0]
    Y = s * x + c * y + center[1]
    out_dir = np.stack([c * nx - s * ny, s * nx + c * ny, np.zeros(n)], 1)
    return np.stack([X, Y, np.full(n, z)], 1), out_dir


def chicken_bvh():
    return fx.bvh_from_mesh(MD.chicken_mesh())


def to_local(points, loc, rz, vectors=False):
    m = Matrix.Rotation(-rz, 3, "Z")
    out = []
    for p in points:
        v = Vector(p) if vectors else Vector(p) - Vector(loc)
        out.append(tuple(m @ v))
    return np.array(out, dtype=np.float32)


def chicken_place(center, rot):
    """Origin location for a chicken whose visual centre is `center`."""
    R = Euler(rot, "XYZ").to_matrix()
    return Vector(center) - R @ Vector((0, 0, HC))


# ============================================================ S1 INTRO =====
def shot_intro(name, n):
    S = Shot(name, n, M.backdrop_world("W_intro", center=(0.5, 0.52)), fstop=3.5)
    order = C.ASSEMBLY_ORDER
    zs, H = MD.stack_heights(order)
    b = MD.burger("S1", S.coll, order, C.SAUCE_COLOR)

    def theta(f):
        return -0.85 + 0.017 * f

    def bob(f):
        return 0.025 * math.sin(TAU * f / 55.0)
    for k, o in b.items():
        rk = MD.LAYER_ROT.get(k, 0.0)
        U.animate(o, S.frames(), lambda f, k=k, rk=rk: dict(loc=(0, 0, zs[k] + bob(f)), rot=(0, 0, theta(f) + rk)))
    ST.studio_rig(S.sc, (0, 0, 0.42), k=0.75)
    S.ambient("crumbs", "crumb", 80, r=(0.8, 2.6), z=(-0.6, 1.7), s=(0.012, 0.032))
    S.ambient("seeds", "seed", 36, r=(0.7, 2.2), z=(-0.4, 1.5), s=(0.022, 0.028),
              sv=np.tile([1.0, 0.52, 0.25], (36, 1)))
    ck_z = zs["chicken"] + 0.1

    def cam(f):
        t = ease_io(seg(f, 1, 62), 2)
        d = lerp(7.2, 2.8, t)
        el = math.radians(lerp(5, 13, t))
        az = lerp(-0.3, 0.12, t)
        tgt = Vector((0, 0, lerp(0.42, 0.5, t)))
        t2 = ease_in(seg(f, 62, 75), 2.4)
        if t2 > 0:
            d = lerp(2.8, 1.0, t2)
            tgt = tgt.lerp(Vector((0, 0, ck_z)), t2)
            el = lerp(el, math.radians(3), t2)
        return orbit(tgt, d, el, az), tgt, lerp(50, 56, t)
    S.camera_path(cam)
    S.ov(type="fade_in", t0=1, t1=12)
    S.ov(type="kinetic", words=["CRISPY.", "CHEESY.", "STACKED."], times=[10, 22, 34], t1=56)
    S.ov(type="subtitle", text="LET'S MAKE IT", t0=50, t1=72)
    S.cue(1, "swell")
    for f in (10, 22, 34):
        S.cue(f, "tick")
    S.cue(62, "whoosh", dur=0.45, up=True)
    return S


# ====================================================== S2 INGREDIENTS =====
def _ingredient(S, key, idx):
    e = bpy.data.objects.new(f"S2_{key}", None)
    S.coll.objects.link(e)

    def add(o, loc=(0, 0, 0), rot=(0, 0, 0), scl=1.0):
        o.parent = e
        o.location, o.rotation_euler, o.scale = loc, rot, (scl, scl, scl)
        return o
    base_rot = (0.3, 0, 0)
    if key == "chicken":
        m, p = M.chicken("S2_chicken_mat")
        add(MD.chicken("S2_chicken_obj", S.coll, m, coat=0.0, level=2), (0, 0, -0.05), scl=0.68)
        base_rot = (1.2, 0, 0.12)
    elif key == "seasoning":
        add(MD.shaker("S2_shaker", S.coll), (0, 0, -0.3), scl=1.25)
        base_rot = (0.15, 0, 0.2)
    elif key == "egg":
        add(MD.dish("S2_eggdish", S.coll), (0, 0, -0.08), scl=0.6)
        add(MD.egg_liquid("S2_egg", S.coll), (0, 0, -0.08), scl=0.6)
        base_rot = (0.95, 0, 0)
    elif key == "flour":
        add(MD.dish("S2_flourdish", S.coll), (0, 0, -0.08), scl=0.6)
        add(MD.flour_mound("S2_flour", S.coll), (0, 0, -0.08), scl=0.6)
        base_rot = (0.95, 0, 0)
    elif key == "buns":
        add(MD.bun_bottom("S2_bunb", S.coll), (0, 0, -0.30), scl=0.72)
        add(MD.bun_top("S2_bunt", S.coll), (0, 0, -0.07), scl=0.72)
        base_rot = (0.35, 0, 0.3)
    elif key == "sauce":
        add(MD.squeeze_bottle("S2_bottle", S.coll, C.SAUCE_COLOR), (0, 0, -0.36), scl=0.85)
        base_rot = (0.1, 0, 0.4)
    elif key == "lettuce":
        add(MD.lettuce("S2_lettuce", S.coll), scl=0.72)
        base_rot = (1.15, 0, 0.2)
    elif key == "cheese":
        add(MD.cheese("S2_cheese", S.coll), scl=0.78)
        base_rot = (1.1, 0.0, 0.5)
    else:  # unknown ingredient from config: neutral placeholder
        add(MD.new_obj(f"S2_{key}_ph", MD.bun_bottom_mesh(), S.coll), scl=0.5)
    return e, base_rot


def shot_ingredients(name, n):
    S = Shot(name, n, M.backdrop_world("W_ingr", center=(0.5, 0.5), radius=0.9), fstop=11.0)
    rows = [1.72, 0.42, -0.88, -2.18]
    cols = [-0.82, 0.82]
    items = []
    cam_d = lambda f: lerp(9.0, 8.4, ease_io(seg(f, 1, n)))
    cam_az = lambda f: lerp(-0.07, 0.07, ease_io(seg(f, 1, n)))
    tgt = Vector((0, 0, -0.15))

    def cam_loc(f):
        return orbit(tgt, cam_d(f), math.radians(4), cam_az(f))
    for i, (key, label) in enumerate(C.INGREDIENTS):
        e, base_rot = _ingredient(S, key, i)
        col, row = i % 2, min(i // 2, len(rows) - 1)
        side = -1 if col == 0 else 1
        g = Vector((cols[col], 0.0, rows[row]))
        fi = 6 + 8 * i
        start = Vector((side * 3.6, -2.0, g.z + 0.9 * math.sin(i * 1.7)))
        exit_t0 = 103 + (i % 3)
        exit_dir = Vector((side * 4.5, 1.0, 1.2 * math.cos(i)))

        def pos(f, g=g, fi=fi, start=start, i=i, exit_t0=exit_t0, exit_dir=exit_dir, key=key):
            t = seg(f, fi, fi + 16)
            p = start.lerp(g, ease_out(t, 4))
            if f > fi + 16:
                p = p + Vector((0, 0, 0.035 * math.sin(TAU * (f - fi) / 45.0 + i)))
            if i == 0:
                te = ease_in(seg(f, 104, n), 2.5)
                cl = cam_loc(f)
                p = p.lerp(cl + (g - cl).normalized() * 0.9, te)
            else:
                p = p + exit_dir * ease_in(seg(f, exit_t0, exit_t0 + 14), 2.5)
            return p

        def fn(f, pos=pos, fi=fi, side=side, base_rot=base_rot, i=i, exit_t0=exit_t0):
            t = seg(f, fi, fi + 16)
            spin = (1 - ease_out(t, 3)) * side * 3.2
            sway = 0.07 * math.sin(TAU * (f - fi) / 70.0 + i) if f > fi + 16 else 0.0
            ex = ease_in(seg(f, exit_t0, exit_t0 + 14), 2) * side * 2.0 if i else 0.0
            s = (0.35 + 0.65 * ease_back(t, 2.2)) * 1.22
            return dict(loc=pos(f), rot=(base_rot[0] + (1 - t) * 0.8, base_rot[1] + ex, base_rot[2] + spin + sway),
                        scl=(s, s, s))
        U.animate(e, S.frames(), fn)
        hide_range(e, S.frames(), lambda f, fi=fi: f >= fi)
        for ch in e.children:
            hide_range(ch, S.frames(), lambda f, fi=fi: f >= fi)
            for gch in ch.children:
                hide_range(gch, S.frames(), lambda f, fi=fi: f >= fi)
        S.track(f"ing{i}", lambda f, pos=pos: pos(f) + Vector((0, 0, -0.5)))
        S.ov(type="label", text=label, track=f"ing{i}", t0=fi + 12, t1=101, side="below", idx=i)
        S.cue(fi, "whoosh", dur=0.3, pitch=1.0 + 0.06 * i)
        S.cue(fi + 13, "pop", pitch=1.0 + 0.05 * i)
        items.append(e)
    ST.studio_rig(S.sc, (0, 0, -0.1), k=0.95, rim=1.3)
    S.ambient("dust", "flour", 40, box=((-2.0, 2.0), (-3.5, 2.0), (-3.2, 3.0)), s=(0.003, 0.008))
    S.camera_path(lambda f: (cam_loc(f), tgt, 50.0))
    S.ov(type="header", num="", text="THE INGREDIENTS", t0=3, t1=101)
    S.cue(104, "whoosh", dur=0.55, up=True)
    return S


# ============================================================ S3 PREP ======
def shot_prep(name, n):
    S = Shot(name, n, M.backdrop_world("W_prep", center=(0.5, 0.7), inner=(0.06, 0.038, 0.022), radius=0.9),
             fstop=4.0)
    rng = S.rng
    MD.floor("S3_floor", S.coll, z=-0.08)
    board = MD.cutting_board("S3_board", S.coll)
    mat, PRM = M.chicken("S3_chicken_mat")
    ck = MD.chicken("S3_chicken", S.coll, mat, coat=0.0, level=2)
    RZ = 0.25
    # ---- chicken path --------------------------------------------------
    T_LAND, T_LIFT1, T_DIP, T_UP, T_FLOUR, T_FLIP, T_FLIP_END, T_SHOW = 9, 44, 58, 68, 92, 118, 130, 134
    ZF = 0.12  # resting height in the flour dish

    def zb(f):
        if f <= T_LAND:
            return lerp(1.3, 0.0, ease_in(seg(f, 1, T_LAND), 2))
        if f <= T_LIFT1:
            return 0.0
        if f <= T_DIP:
            return lerp(0.0, 0.75, ease_io(seg(f, T_LIFT1, 56))) + 0.02 * math.sin(TAU * f / 30)
        if f <= 64:
            return lerp(0.75 + 0.02 * math.sin(TAU * T_DIP / 30), 0.06, ease_in(seg(f, T_DIP, 64), 2))
        if f <= T_UP:
            return 0.06
        if f <= T_FLOUR:
            return lerp(0.06, 0.85, ease_out(seg(f, T_UP, 78), 3)) + 0.02 * math.sin(TAU * (f - 78) / 28) * seg(f, 78, 82)
        if f <= 98:
            return lerp(0.85 + 0.02 * math.sin(TAU * (T_FLOUR - 78) / 28), ZF, ease_in(seg(f, T_FLOUR, 98), 2))
        return ZF

    def state(f):
        """(centre, rot) of the chicken."""
        rx, ry, rz = 0.0, 0.0, RZ
        if T_DIP - 2 <= f <= T_UP:
            rz += 0.06 * math.sin(TAU * (f - 60) / 8.0) * seg(f, 60, 64) * (1 - seg(f, 66, T_UP))
        if f < T_FLIP:
            c = Vector((0, 0, zb(f) + HC))
            return c, (rx, ry, rz)
        t = seg(f, T_FLIP, T_FLIP_END)
        zc = ZF + HC + 0.5 * math.sin(math.pi * ease_io(t))
        rx = math.pi * ease_io(t)
        if f >= T_SHOW:
            ts = ease_io(seg(f, T_SHOW, 144))
            zc = ZF + HC + 0.62 * ts
            ry = 0.10 * math.sin(TAU * (f - 138) / 4.0) * seg(f, 138, 139) * (1 - seg(f, 144, 147))
            rx = math.pi + 0.42 * ease_io(seg(f, 142, n))
            rz = RZ + 0.25 * ease_io(seg(f, 140, n))
        return Vector((0, 0, zc)), (rx, ry, rz)

    impacts = [T_LAND, 98, T_FLIP_END]

    def ck_fn(f):
        c, rot = state(f)
        sq = 0.0
        for fi in impacts:
            if f >= fi:
                sq = 0.16 * impact((f - fi) / C.FPS, 3.4, 8.0) if fi != T_FLIP_END else 0.1 * impact((f - fi) / C.FPS, 3.4, 8.0)
        return dict(loc=chicken_place(c, rot), rot=rot, scl=squash_scale(sq))
    U.animate(ck, S.frames(), ck_fn)
    # material + crust timing
    for f in S.frames():
        U.key_socket(PRM["season"].outputs[0], f, smooth(seg(f, 19, 44)))
        U.key_socket(PRM["wet"].outputs[0], f, smooth(seg(f, 62, 67)))
        U.key_socket(PRM["coat"].outputs[0], f, smooth(seg(f, 99, 124)))
        fx.key_input(ck, "Crust", "Coat", f, smooth(seg(f, 99, 124)))
    # ---- dishes --------------------------------------------------------
    egg_d, egg_l = MD.dish("S3_eggdish", S.coll), MD.egg_liquid("S3_egg", S.coll)
    fl_d, fl_m = MD.dish("S3_flourdish", S.coll), MD.flour_mound("S3_flour", S.coll)

    def egg_x(f):
        return lerp(-3.4, 0, ease_out(seg(f, 46, 58), 3)) + lerp(0, -3.4, ease_in(seg(f, 76, 88), 2.5))

    def fl_x(f):
        return lerp(3.4, 0, ease_out(seg(f, 80, 92), 3))
    for o in (egg_d, egg_l):
        U.animate(o, S.frames(), lambda f: dict(loc=(egg_x(f), 0, 0)))
        hide_range(o, S.frames(), lambda f: 44 <= f <= 90)
    for o in (fl_d, fl_m):
        U.animate(o, S.frames(), lambda f: dict(loc=(fl_x(f), 0, 0)))
        hide_range(o, S.frames(), lambda f: f >= 78)
    fx.set_inputs(egg_l, egg_l.modifiers["Ripple"], {"Amp": 0.002, "RingStart": 61.0, "RingAmp": 0.014,
                                                     "RingCenter": (0, 0, MD.DISH_LIQ_Z)})
    # ---- seasoning shaker ------------------------------------------------
    sh = MD.shaker("S3_shaker", S.coll)
    sh_rot = Euler((0.0, -2.6, 0.0))
    cap_dir = sh_rot.to_matrix() @ Vector((0, 0, 1))
    sh_home = Vector((0.45, -0.05, 1.25))
    SHAKES = [18, 26, 34]

    def sh_loc(f):
        p = Vector((1.7, -0.05, 2.5)).lerp(sh_home, ease_out(seg(f, 8, 16), 3))
        for fs in SHAKES:
            p = p + cap_dir * 0.11 * math.exp(-((f - fs) / 1.6) ** 2)
        return p.lerp(Vector((1.9, -0.05, 2.7)), ease_in(seg(f, 38, 48), 2))
    U.animate(sh, S.frames(), lambda f: dict(
        loc=sh_loc(f), rot=(0, -2.6 + 0.12 * sum(math.exp(-((f - fs) / 1.6) ** 2) for fs in SHAKES), 0.0),
        scl=(1.2, 1.2, 1.2)))
    hide_range(sh, S.frames(), lambda f: 8 <= f <= 48)
    bvh = chicken_bvh()
    # spice bursts land and stick on the chicken (parented, chicken-local)
    p0s, v0s, es = [], [], []
    for fs in SHAKES:
        N = 120
        e = fs + rng.uniform(-0.5, 3.0, N)
        cap = np.array([tuple(sh_home + cap_dir * 0.53 * 1.2) for _ in range(N)])
        p0s.append(cap + rng.normal(0, 0.03, (N, 3)))
        v0s.append(np.array(cap_dir)[None, :] * rng.uniform(0.8, 1.6, (N, 1)) + rng.normal(0, 0.38, (N, 3)))
        es.append(e)
    p0 = to_local(np.concatenate(p0s), (0, 0, 0), RZ)
    v0 = to_local(np.concatenate(v0s), None, RZ, vectors=True)
    e = np.concatenate(es)
    land = fx.landing(p0, v0, 22.0, bvh=bvh, floor_z=0.0, max_frames=60)
    NN = len(p0)
    S.ballistic("spice", "spice", p0, v0, e, land, land + rng.uniform(4, 10, NN), 8.0,
                rng.uniform(0.006, 0.012, NN), sv=np.stack([np.ones(NN), rng.uniform(0.6, 1, NN),
                                                           rng.uniform(0.4, 0.8, NN)], 1),
                gravity=22.0, parent=ck)
    for fs in SHAKES:
        S.cue(fs, "shake")
    # egg splash + drips
    N = 70
    pts, od = chicken_outline(rng, N, RZ, (0.0, 0.05), MD.DISH_LIQ_Z)
    v = od * rng.uniform(0.3, 1.0, (N, 1)) + np.stack([np.zeros(N), np.zeros(N), rng.uniform(0.8, 1.8, N)], 1)
    land = fx.landing(pts, v, 30.0, floor_z=MD.DISH_LIQ_Z, max_frames=40)
    S.ballistic("eggsplash", "egg_drop", pts, v, 61 + rng.uniform(0, 2, N), land, land, 2.0,
                rng.uniform(0.008, 0.018, N), gravity=30.0)
    N = 40
    e = rng.uniform(71, 92, N)
    pts = []
    for ei in e:
        c, rot = state(ei)
        a = rng.uniform(0, TAU)
        pts.append(tuple(c + Euler(rot).to_matrix() @ Vector((0.5 * math.cos(a) * rng.uniform(0.3, 1),
                                                              0.4 * math.sin(a) * rng.uniform(0.3, 1), -0.085))))
    pts = np.array(pts)
    v = np.stack([np.zeros(N), np.zeros(N), rng.uniform(-0.4, -0.1, N)], 1)
    land = fx.landing(pts, v, 30.0, floor_z=0.0, max_frames=40)
    S.ballistic("eggdrip", "egg_drop", pts, v, e, land, land, 2.0, rng.uniform(0.008, 0.013, N),
                sv=(1, 1, 1.7), gravity=30.0)
    S.cue(61, "splash", size=0.6)
    for fd in (74, 79, 85, 90):
        S.cue(fd, "drip")
    # flour puffs (impact) ---------------------------------------------------
    for t0, N, k in ((98, 600, 1.0), (T_FLIP_END, 300, 0.7)):
        pts, od = chicken_outline(rng, N, RZ, (-0.05, 0.08), 0.2)
        v = od * rng.uniform(0.6, 2.2, (N, 1)) * k + np.stack([np.zeros(N), np.zeros(N), rng.uniform(0.8, 3.0, N) * k], 1)
        land = fx.landing(pts, v, 6.0, drag=3.0, floor_z=0.19, max_frames=60)
        life = np.minimum(land, rng.uniform(14, 34, N))
        S.ballistic(f"puff{t0}", "flour", pts, v, t0 + rng.uniform(0, 3, N), land, life, 12.0,
                    rng.uniform(0.004, 0.011, N), gravity=6.0, drag=3.0)
        S.cue(t0, "puff", size=k)
    # flour rain that sticks to the chicken (chicken static at ZF during it)
    N = 700
    e = rng.uniform(100, 113, N)
    pw = np.stack([rng.uniform(-0.75, 0.75, N), rng.uniform(-0.6, 0.6, N), np.full(N, 1.55)], 1)
    vw = np.stack([rng.normal(0, 0.1, N), rng.normal(0, 0.1, N), rng.uniform(-2.0, -1.0, N)], 1)
    p0 = to_local(pw, (0, 0, ZF), RZ)
    v0 = to_local(vw, None, RZ, vectors=True)
    land = fx.landing(p0, v0, 25.0, bvh=bvh, floor_z=0.2 - ZF, max_frames=40)
    S.ballistic("flourrain", "flour", p0, v0, e, land, land + rng.uniform(2, 7, N), 7.0,
                rng.uniform(0.004, 0.009, N), gravity=25.0, parent=ck)
    S.cue(100, "sprinkle", dur=0.45)
    # shake-off
    N = 90
    e = rng.uniform(138, 148, N)
    pts = []
    for ei in e:
        c, rot = state(ei)
        pts.append(tuple(c + Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.4, 0.4), -0.09))))
    pts = np.array(pts)
    v = np.stack([rng.normal(0, 0.15, N), rng.normal(0, 0.15, N), rng.uniform(-0.6, -0.2, N)], 1)
    land = fx.landing(pts, v, 20.0, floor_z=0.2, max_frames=40)
    S.ballistic("shakeoff", "flour", pts, v, e, land, land, 3.0, rng.uniform(0.006, 0.012, N), gravity=20.0)
    # ---- camera ------------------------------------------------------------
    def cam(f):
        c, _ = state(f)
        tgt = Vector((0, 0, 0.2 + 0.45 * zb(min(f, T_FLIP - 1))))
        d, el, az, lens = 4.3, math.radians(38), -0.12 + 0.0018 * f, 50.0
        t = ease_io(seg(f, T_SHOW, n))
        if t > 0:
            tgt = tgt.lerp(c, t)
            d, el, lens = lerp(d, 2.9, t), lerp(el, math.radians(24), t), lerp(50, 62, t)
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.2), k=0.24, rim=1.8)
    # ---- overlays ----------------------------------------------------------
    st = {k: (num, title) for k, num, title in C.PREP_STEPS}
    S.ov(type="header", num=st["season"][0], text=st["season"][1], t0=10, t1=44)
    S.ov(type="header", num=st["dip"][0], text=st["dip"][1], t0=46, t1=88)
    S.ov(type="header", num=st["coat"][0], text=st["coat"][1], t0=90, t1=134)
    S.track("crust", lambda f: state(f)[0] + Euler(state(f)[1]).to_matrix() @ Vector((0.42, -0.25, -0.06)))
    S.ov(type="callout", text="CRISPY COATING", track="crust", t0=138, t1=n, dx=-260, dy=-330)
    S.cue(T_LAND, "thud", size=0.7)
    S.cue(T_LIFT1, "whoosh", dur=0.3)
    S.cue(T_FLOUR, "whoosh", dur=0.25)
    S.cue(T_FLIP, "whoosh", dur=0.35)
    S.cue(140, "whoosh", dur=0.4)
    return S


# ============================================================= S4 FRY ======
def shot_fry(name, n):
    S = Shot(name, n, M.backdrop_world("W_fry", center=(0.5, 0.75), inner=(0.065, 0.04, 0.02), radius=0.9),
             fstop=5.6, lens=45)
    rng = S.rng
    OZ = MD.POT_OIL_Z
    MD.floor("S4_floor", S.coll, z=0.0)
    MD.pot("S4_pot", S.coll)
    oil = MD.oil_surface("S4_oil", S.coll)
    mat, PRM = M.chicken("S4_chicken_mat")
    PRM["season"].outputs[0].default_value = 1.0
    PRM["coat"].outputs[0].default_value = 1.0
    ck = MD.chicken("S4_chicken", S.coll, mat, coat=1.0, level=2)
    RZ = 0.2
    T_IN, T_FLIP, T_FLIP_END, T_CUT, T_LIFT, T_LIFT_END = 22, 56, 68, 89, 98, 120
    ZC = OZ - 0.135 + HC   # floating centre height (mostly submerged)

    def state(f):
        rx, ry, rz = 0.0, 0.0, RZ
        if f <= T_IN:
            zc = lerp(1.65, ZC, ease_io(seg(f, 1, T_IN), 2.2))
        else:
            zc = ZC + 0.03 * impact((f - T_IN) / C.FPS, 1.6, 2.5) - 0.03 * math.exp(-((f - T_IN - 2) / 3) ** 2)
            zc += 0.006 * math.sin(TAU * f / 26)
        t = seg(f, T_FLIP, T_FLIP_END)
        if 0 < t < 1 or f >= T_FLIP_END:
            zc += 0.16 * math.sin(math.pi * ease_io(t))
            rx = math.pi * ease_io(t)
        if f >= T_LIFT:
            tl = ease_io(seg(f, T_LIFT, T_LIFT_END))
            zc = lerp(zc, 0.98, tl)
            rz = RZ + 0.35 * ease_io(seg(f, T_LIFT, n))
            rx = math.pi - 0.25 * tl
        return Vector((0, 0, zc)), (rx, ry, rz)
    U.animate(ck, S.frames(), lambda f: dict(loc=chicken_place(*state(f)), rot=state(f)[1]))
    for f in S.frames():
        fr = 0.55 * smooth(seg(f, 26, T_CUT)) + 0.45 * smooth(seg(f, T_CUT, 125))
        U.key_socket(PRM["fry"].outputs[0], f, fr)
    for f in (1, T_CUT - 1, T_CUT, n):
        fx.key_input(ck, "Crust", "Level", f, 2 if f < T_CUT else 3)
    # ---- tongs ---------------------------------------------------------------
    root, hl, hr = MD.tongs("S4_tongs", S.coll)
    root.scale = (1.6, 1.6, 1.6)
    root.rotation_euler = (0, 0.93, 0.35)

    def grip(f):
        c, rot = state(f)
        return c + Euler(rot).to_matrix() @ Vector((0.6, 0.0, 0.0))
    away = Vector((0.9, 0.3, 1.4))

    def tong_fn(f):
        if f < T_CUT:
            p = grip(min(f, T_IN + 2)) + away * ease_in(seg(f, 26, 36), 2)
        else:
            p = grip(f) + away * (1 - ease_out(seg(f, T_CUT, 95), 3))
        return dict(loc=p)
    U.animate(root, S.frames(), tong_fn)

    def arm(f):
        if f < T_CUT:
            return lerp(0.075, 0.17, ease_out(seg(f, T_IN + 2, T_IN + 8)))
        return lerp(0.17, 0.075, ease_out(seg(f, 94, 98)))
    for h, sgn in ((hl, 1), (hr, -1)):
        U.animate(h, S.frames(), lambda f, sgn=sgn: dict(rot=(0, sgn * arm(f), 0)))
    vis = lambda f: f <= 35 or f >= T_CUT
    for o in (root, hl, hr) + tuple(c for h in (hl, hr) for c in h.children):
        hide_range(o, S.frames(), vis)
    S.cue(T_IN + 2, "clack")
    S.cue(96, "clack")
    # ---- oil surface ---------------------------------------------------------
    rip = oil.modifiers["Ripple"]
    fx.set_inputs(oil, rip, {"RingStart": float(T_IN), "RingAmp": 0.02, "RingCenter": (0, 0, OZ)})
    for f in S.frames():
        fx.key_input(oil, "Ripple", "Amp", f, lerp(0.0015, 0.005, smooth(seg(f, T_IN, T_IN + 10))))
    # ---- splashes ------------------------------------------------------------
    for t0, N, k in ((T_IN, 170, 1.0), (T_FLIP_END, 80, 0.7)):
        pts, od = chicken_outline(rng, N, RZ, (0.0, 0.06), OZ)
        v = od * rng.uniform(0.4, 1.5, (N, 1)) * k + np.stack([np.zeros(N), np.zeros(N), rng.uniform(1.0, 2.8, N) * k], 1)
        land = fx.landing(pts, v, 30.0, floor_z=OZ, max_frames=40)
        S.ballistic(f"splash{t0}", "drop", pts, v, t0 + rng.uniform(0, 2, N), land, land, 2.0,
                    rng.uniform(0.008, 0.02, N), sv=(1, 1, 1.3), gravity=30.0)
        S.cue(t0, "splash", size=k)
    # ---- bubbles ---------------------------------------------------------------
    N = 1400
    pts, od = chicken_outline(rng, N, RZ, (0.0, 0.0), OZ)
    d = 0.11 * rng.uniform(0, 1, N) ** 2.5 - 0.01
    pts = pts + od * d[:, None]
    per = rng.uniform(6, 18, N)
    foam = S.looping("foam", "bubble", pts, od * rng.uniform(0.0005, 0.003, (N, 1)), per, rng.uniform(0, 30, N),
                     rng.uniform(0.004, 0.014, N), spin=0.0, wob=0.003, wf=0.2, pop=1.0, density=0.0)
    N = 200
    th = rng.uniform(0, TAU, N)
    rr = np.sqrt(rng.uniform(0.62 ** 2, 0.86 ** 2, N))
    pts = np.stack([rr * np.cos(th), rr * np.sin(th), np.full(N, OZ)], 1)
    scat = S.looping("bubbles", "bubble", pts, np.zeros((N, 3)), rng.uniform(10, 30, N), rng.uniform(0, 30, N),
                     rng.uniform(0.008, 0.024, N), wob=0.004, wf=0.15, pop=1.0, density=0.0)
    N = 50
    th = rng.uniform(0, TAU, N)
    rr = rng.uniform(0.6, 0.84, N)
    pts = np.stack([rr * np.cos(th), rr * np.sin(th), np.full(N, OZ + 0.004)], 1)
    vel = np.stack([-np.sin(th), np.cos(th), np.zeros(N)], 1) * 0.0012
    per = np.full(N, 4000.0)
    ph = per * rng.uniform(0.45, 0.55, N)
    bits = S.looping("bits", "crumb", pts - vel * ph[:, None], vel, per, ph, rng.uniform(0.008, 0.02, N),
                     sv=np.stack([np.ones(N), rng.uniform(0.6, 1, N), rng.uniform(0.3, 0.6, N)], 1),
                     spin=0.004, density=0.0)
    for f in S.frames():
        fx.key_input(foam, "FX", "Density", f, smooth(seg(f, T_IN - 1, T_IN + 5)) * (1 - 0.65 * smooth(seg(f, T_LIFT, T_LIFT_END))))
        fx.key_input(scat, "FX", "Density", f, 0.85 * smooth(seg(f, T_IN, T_IN + 9)))
        fx.key_input(bits, "FX", "Density", f, smooth(seg(f, 30, 50)))
    # ---- steam -----------------------------------------------------------------
    camA = lambda f: orbit((0, 0.05, 0.47), lerp(4.3, 3.8, ease_io(seg(f, 1, T_CUT))),
                           math.radians(lerp(54, 50, seg(f, 1, T_CUT))), -0.2 + 0.0025 * f)
    N = 36
    th = rng.uniform(0, TAU, N)
    rr = 0.5 * np.sqrt(rng.uniform(0, 1, N))
    pts = np.stack([rr * np.cos(th), rr * np.sin(th), rng.uniform(OZ + 0.06, OZ + 0.16, N)], 1)
    vel = np.stack([rng.normal(0, 0.0015, N), rng.normal(0, 0.0015, N), rng.uniform(0.008, 0.014, N)], 1)
    rot = fx.face_camera_euler(pts, camA(45))
    steamA = S.looping("steamA", "sprite", pts, vel, rng.uniform(40, 70, N), rng.uniform(0, 70, N),
                       rng.uniform(0.35, 0.6, N), rot=rot, spin=np.zeros((N, 3)), wob=0.02, wf=0.05, density=0.0)
    # ---- macro camera B ----------------------------------------------------
    def camB(f):
        c, rot = state(f)
        t = ease_io(seg(f, T_CUT, n))
        tgt = c + Vector((0.0, -0.32, 0.03))
        return orbit(tgt, lerp(1.7, 1.35, t), math.radians(lerp(38, 16, t)), lerp(-0.5, -0.18, t))
    N = 30
    pts = np.stack([rng.uniform(-0.5, 0.5, N), rng.uniform(-0.4, 0.3, N), rng.uniform(OZ + 0.06, 1.12, N)], 1)
    vel = np.stack([rng.normal(0, 0.001, N), rng.normal(0, 0.001, N), rng.uniform(0.006, 0.01, N)], 1)
    rot = fx.face_camera_euler(pts, camB(112))
    steamB = S.looping("steamB", "sprite", pts, vel, rng.uniform(40, 60, N), rng.uniform(0, 60, N),
                       rng.uniform(0.18, 0.32, N), rot=rot, spin=np.zeros((N, 3)), wob=0.015, wf=0.05,
                       density=0.0)
    for f in S.frames():
        fx.key_input(steamA, "FX", "Density", f, smooth(seg(f, 26, 42)) * (1.0 if f < T_CUT else 0.0))
        fx.key_input(steamB, "FX", "Density", f, smooth(seg(f, T_CUT, 100)))
    # oil dripping off the lifted chicken
    N = 80
    e = rng.uniform(T_LIFT + 4, n, N)
    pts = []
    for ei in e:
        c, rot = state(ei)
        a = rng.uniform(0, TAU)
        pts.append(tuple(c + Euler((0, 0, rot[2])).to_matrix() @ Vector((0.55 * math.cos(a) * rng.uniform(0.5, 0.95),
                                                                           0.45 * math.sin(a) * rng.uniform(0.5, 0.95), -0.08))))
    pts = np.array(pts)
    v = np.stack([np.zeros(N), np.zeros(N), rng.uniform(-0.4, -0.1, N)], 1)
    land = fx.landing(pts, v, 30.0, floor_z=OZ, max_frames=40)
    S.ballistic("drips", "drop", pts, v, e, land, land, 2.0, rng.uniform(0.006, 0.013, N), sv=(1, 1, 1.7),
                gravity=30.0)

    # ---- camera ------------------------------------------------------------
    def cam(f):
        if f < T_CUT:
            tgt = Vector((0, 0.05, lerp(0.95, 0.47, ease_io(seg(f, 1, 26)))))
            return camA(f), tgt, 45.0
        c, rot = state(f)
        return camB(f), c + Vector((0.0, -0.32, 0.03)), 85.0
    S.camera_path(cam)
    for f in (1, T_CUT - 1):
        U.key_prop(S.cam.data.dof, "aperture_fstop", f, 5.6)
    for f in (T_CUT, n):
        U.key_prop(S.cam.data.dof, "aperture_fstop", f, 2.2)
    ST.studio_rig(S.sc, (0, 0, OZ), k=0.28, rim=1.8)
    # ---- overlays / cues ---------------------------------------------------
    S.ov(type="header", num=C.FRY_TITLE[0], text=C.FRY_TITLE[1], t0=6, t1=T_CUT - 2)
    if C.FRY_TEMPERATURE_LABEL:
        S.ov(type="temp", text=C.FRY_TEMPERATURE_LABEL, t0=30, t1=T_CUT - 2)
    S.ov(type="haze", t0=T_IN + 2, t1=T_CUT - 1, y0=0.0, y1=0.5, amp=3.0)
    S.ov(type="haze", t0=T_CUT, t1=n, y0=0.0, y1=0.45, amp=2.0)
    S.track("top", lambda f: state(f)[0] + Euler((0, 0, state(f)[1][2])).to_matrix() @ Vector((-0.15, -0.3, 0.1)))
    S.track("edge", lambda f: state(f)[0] + Euler((0, 0, state(f)[1][2])).to_matrix() @ Vector((0.35, -0.42, -0.02)))
    S.ov(type="callout", text="GOLDEN BROWN", track="top", t0=100, t1=n, dx=-240, dy=-380)
    S.ov(type="callout", text="CRUNCHY CRUST", track="edge", t0=110, t1=n, dx=200, dy=330)
    S.cue(1, "whoosh", dur=0.5)
    S.cue(T_IN, "sizzle_start")
    S.cue(T_FLIP, "whoosh", dur=0.3)
    S.cue(T_CUT, "whoosh", dur=0.35)
    S.cue(112, "crunch", size=0.6)
    return S


# =========================================================== S5 BUILD ======
def shot_build(name, n):
    S = Shot(name, n, M.backdrop_world("W_build", center=(0.5, 0.62)), fstop=4.0, lens=55)
    rng = S.rng
    order = C.ASSEMBLY_ORDER
    zs, H = MD.stack_heights(order)
    MD.floor("S5_floor", S.coll, z=-0.08)
    MD.round_board("S5_board", S.coll)
    b = MD.burger("S5", S.coll, order, C.SAUCE_COLOR, level=2)
    DROP = 2.0
    sched, t = {}, 4
    fall = {"bun_bottom": 8, "lettuce": 12, "cheese": 10, "chicken": 8, "bun_top": 10}
    for k in order:
        if k == "sauce":
            sched[k] = dict(start=t, land=t + 6, end=t + 30)
            t += 32
        else:
            sched[k] = dict(start=t, land=t + fall[k])
            t += fall[k] + 4
    flutter = {"lettuce": 1.0, "cheese": 0.8}
    heavy = {"chicken": 0.2, "bun_top": 0.16, "bun_bottom": 0.12, "lettuce": 0.06, "cheese": 0.05}
    for k, o in b.items():
        if k == "sauce":
            continue
        s = sched[k]
        rk = MD.LAYER_ROT.get(k, 0.0)
        drift = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0))

        def fn(f, s=s, k=k, rk=rk, drift=drift):
            tt = seg(f, s["start"], s["land"])
            z = zs[k] + DROP * (1 - ease_in(tt, 2))
            fl = flutter.get(k, 0.0)
            rx = fl * 0.35 * math.sin(TAU * 1.6 * tt) * (1 - tt)
            ry = fl * 0.25 * math.cos(TAU * 1.2 * tt) * (1 - tt)
            rz = rk + (1 - ease_out(tt)) * (0.8 if fl else 0.3)
            p = drift * (1 - ease_out(tt, 2)) * (1 if fl else 0.3)
            if f >= s["land"]:
                sc = squash_scale(heavy.get(k, 0.1) * impact((f - s["land"]) / C.FPS, 3.4, 7.5))
            else:
                st = 1 + 0.08 * tt if not fl else 1.0
                sc = (1 / math.sqrt(st), 1 / math.sqrt(st), st)
            return dict(loc=(p.x, p.y, z), rot=(rx, ry, rz), scl=sc)
        U.animate(o, S.frames(), fn)
        hide_range(o, S.frames(), lambda f, s=s: f >= s["start"])
        S.cue(s["start"], "whoosh", dur=0.22, pitch=1.2)
        S.cue(s["land"], "crunch" if k == "chicken" else "thud",
              size={"chicken": 1.0, "bun_top": 0.8, "bun_bottom": 0.8}.get(k, 0.4),
              soft=k in ("lettuce", "cheese"))
    # cheese drape
    if "cheese" in b:
        kb = b["cheese"].data.shape_keys.key_blocks["drape"]
        lc = sched["cheese"]["land"]
        lch = sched.get("chicken", {}).get("land", lc)
        for f in S.frames():
            v = 0.0
            if f >= lc:
                v = 0.45 * ease_out(seg(f, lc, lc + 8))
            if lch > lc and f >= lch:
                v = 0.45 + 0.55 * ease_out(seg(f, lch, lch + 14))
            elif lch <= lc and f >= lc:
                v = ease_out(seg(f, lc, lc + 14))
            U.key_prop(kb, "value", f, v)
    # sauce squeeze
    if "sauce" in b:
        sc_obj = b["sauce"]
        s = sched["sauce"]
        sq0, sq1 = s["land"] + 1, s["end"] - 6
        sc_obj.location = (0, 0, zs["sauce"])
        hide_range(sc_obj, S.frames(), lambda f: f >= sq0)
        for f in S.frames():
            U.key_prop(sc_obj.data, "bevel_factor_end", f, max(0.0005, seg(f, sq0, sq1)))
        bottle = MD.squeeze_bottle("S5_bottle", S.coll, C.SAUCE_COLOR)
        brot = Euler((math.pi - 0.3, 0.15, 0.0))
        Rb = brot.to_matrix()
        tip_local = Vector((0, 0, 0.822 * 0.9))

        def bottle_fn(f):
            tt = seg(f, sq0, sq1)
            tip = MD.spiral_point(sc_obj, tt)
            tip = Vector((tip.x, tip.y, zs["sauce"] + 0.075))
            off = Vector((0, 0, 1.6)) * (1 - ease_out(seg(f, s["start"], s["land"]), 3)) \
                + Vector((0.4, 0.2, 1.8)) * ease_in(seg(f, s["end"] - 5, s["end"] + 4), 2)
            return dict(loc=tip - Rb @ tip_local + off, rot=tuple(brot), scl=(0.9, 0.9, 0.9))
        U.animate(bottle, S.frames(), bottle_fn)
        hide_range(bottle, S.frames(), lambda f: s["start"] <= f <= s["end"] + 4)
        kb = bottle.data.shape_keys.key_blocks["squeeze"]
        for f in S.frames():
            U.key_prop(kb, "value", f, 0.85 * ease_out(seg(f, sq0 - 2, sq0 + 2)) * (1 - ease_out(seg(f, sq1, sq1 + 3))))
        S.cue(sq0, "squeeze", dur=(sq1 - sq0) / C.FPS)
    # crumbs burst when the chicken lands
    if "chicken" in b:
        lch = sched["chicken"]["land"]
        N = 90
        pts, od = chicken_outline(rng, N, MD.LAYER_ROT.get("chicken", 0.0), (0.0, 0.05), zs["chicken"] + 0.04)
        v = od * rng.uniform(0.4, 1.4, (N, 1)) + np.stack([np.zeros(N), np.zeros(N), rng.uniform(0.6, 1.8, N)], 1)
        land = fx.landing(pts, v, 30.0, floor_z=0.0, max_frames=60)
        S.ballistic("crumbs", "crumb", pts, v, lch + rng.uniform(0, 2, N), land, np.full(N, 500.0), 10.0,
                    rng.uniform(0.008, 0.02, N), gravity=30.0)

    def cam(f):
        t = ease_io(seg(f, 1, n))
        tgt = Vector((0, 0, 0.42))
        return orbit(tgt, lerp(4.0, 3.55, t), math.radians(lerp(15, 19, t)), lerp(-0.5, 0.25, t)), tgt, 55.0
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.4), k=0.45, rim=1.4)
    S.ov(type="header", num=C.BUILD_TITLE[0], text=C.BUILD_TITLE[1], t0=4, t1=104)
    for i, k in enumerate(order):
        s = sched[k]
        side = 1 if i % 2 == 0 else -1
        t0 = (s["land"] + 1) if k != "sauce" else s["land"] + 4
        S.track(f"lay{i}", lambda f, k=k, side=side: Vector((0, 0, zs[k] + MD.LAYER_H[k] * 0.5))
                + Vector(S.ct.frames[f][1] @ Vector((1, 0, 0))) * 0.62 * side)
        S.ov(type="label", text=C.LAYER_LABELS.get(k, k.upper()), track=f"lay{i}", t0=t0, t1=t0 + 22,
             side="right" if side > 0 else "left", idx=i)
    return S


# ======================================================== S6 EXPLODED ======
def shot_exploded(name, n):
    S = Shot(name, n, M.backdrop_world("W_expl", center=(0.5, 0.5), radius=0.85), fstop=5.6)
    order = C.ASSEMBLY_ORDER
    zs, H = MD.stack_heights(order)
    b = MD.burger("S6", S.coll, order, C.SAUCE_COLOR, level=2)
    G = 0.30
    nL = len(order)

    def E(i, f):
        up = ease_back(seg(f, 6 + 1.5 * i, 22 + 1.5 * i), 1.6)
        down = ease_in(seg(f, 56 + 2.6 * i, 66 + 2.6 * i), 2.2)
        return up * (1 - down)

    def theta(f):
        return 0.3 + 0.006 * f

    def zc(i, k, f):
        return zs[k] + i * G * E(i, f)

    for i, k in enumerate(order):
        o = b[k]
        rk = MD.LAYER_ROT.get(k, 0.0)
        land = 66 + 2.6 * i

        def fn(f, i=i, k=k, rk=rk, land=land):
            e = E(i, f)
            rot = (0.10 * e * math.sin(i * 1.7 + 0.5), 0.08 * e * math.cos(i * 2.3), theta(f) + rk + 0.35 * e * (-1) ** i)
            sq = 0.12 * impact((f - land) / C.FPS, 3.6, 8.0) if (f >= land and i > 0) else 0.0
            return dict(loc=(0, 0, zc(i, k, f)), rot=rot, scl=squash_scale(sq))
        U.animate(o, S.frames(), fn)
        if i > 0:
            S.cue(land, "thud", size=0.35 + 0.1 * i, soft=k in ("lettuce", "cheese", "sauce"))
    avgE = lambda f: sum(E(i, f) for i in range(nL)) / nL
    S.ambient("crumbs", "crumb", 60, center=(0, 0, 0.8), r=(1.0, 2.6), z=(-1.2, 1.6), s=(0.012, 0.03))
    S.ambient("seeds", "seed", 24, center=(0, 0, 0.8), r=(0.9, 2.2), z=(-1, 1.4), s=(0.022, 0.028),
              sv=np.tile([1.0, 0.52, 0.25], (24, 1)))

    def cam(f):
        top = zc(nL - 1, order[-1], f) + MD.LAYER_H[order[-1]]
        tgt = Vector((0, 0, 0.5 * top))
        return orbit(tgt, lerp(5.2, 4.6, ease_io(seg(f, 1, n))), math.radians(lerp(12, 20, seg(f, 1, n))),
                     -0.35 + 0.021 * f), tgt, 50.0
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.9), k=0.8, rim=1.3)
    for i, k in enumerate(order):
        side = 1 if i % 2 == 0 else -1
        S.track(f"lay{i}", lambda f, i=i, k=k, side=side: Vector((0, 0, zc(i, k, f) + MD.LAYER_H[k] * 0.5))
                + Vector(S.ct.frames[f][1] @ Vector((1, 0, 0))) * 0.64 * side)
        S.ov(type="label", text=C.LAYER_LABELS.get(k, k.upper()), track=f"lay{i}", t0=24 + 3 * i, t1=55,
             side="right" if side > 0 else "left", idx=i)
    S.cue(6, "whoosh", dur=0.5, up=True)
    S.cue(24, "riser", dur=1.1)
    S.cue(56, "whoosh", dur=0.4)
    S.cue(66 + 2.6 * (nL - 1) + 0.5, "boom")
    return S


# =========================================================== S7 FINAL ======
def shot_final(name, n):
    S = Shot(name, n, M.backdrop_world("W_final", center=(0.5, 0.6), inner=(0.11, 0.06, 0.03), radius=0.8),
             fstop=4.0, lens=55)
    rng = S.rng
    order = C.ASSEMBLY_ORDER
    zs, H = MD.stack_heights(order)
    MD.floor("S7_floor", S.coll, z=-0.08)
    board = MD.round_board("S7_board", S.coll)
    b = MD.burger("S7", S.coll, order, C.SAUCE_COLOR, level=2)

    def theta(f):
        return 0.15 + 0.0075 * f
    for k, o in b.items():
        rk = MD.LAYER_ROT.get(k, 0.0)
        U.animate(o, S.frames(), lambda f, k=k, rk=rk: dict(loc=(0, 0, zs[k]), rot=(0, 0, theta(f) + rk)))
    U.animate(board, S.frames(), lambda f: dict(rot=(0, 0, theta(f))))
    # crumbs resting on the board (rotate with it)
    N = 40
    th = rng.uniform(0, TAU, N)
    rr = rng.uniform(0.62, 0.86, N)
    pts = np.stack([rr * np.cos(th), rr * np.sin(th), np.full(N, 0.006)], 1)
    per = np.full(N, 1e6)
    S.looping("boardcrumbs", "crumb", pts, np.zeros((N, 3)), per, per * 0.5, rng.uniform(0.01, 0.022, N),
              sv=np.stack([np.ones(N), rng.uniform(0.6, 1, N), rng.uniform(0.35, 0.6, N)], 1), parent=board)
    cam_el = lambda f: math.radians(lerp(7, 10, ease_io(seg(f, 1, n))))
    cam_d = lambda f: lerp(4.1, 3.75, ease_io(seg(f, 1, n)))
    tgt = Vector((0, 0, 0.98))

    def cam(f):
        return orbit(tgt, cam_d(f), cam_el(f), 0.0), tgt, 55.0
    # 3D title
    lines = [(C.FINAL_TEXT[0], 0.10, "cream", 1.86, 1.2),
             (C.FINAL_TEXT[1], 0.13, "gold", 1.66, 1.05),
             (C.FINAL_TEXT[2], 0.30, "cream", 1.38, 1.0)]
    el0 = cam_el(50)
    for j, (txt, size, matk, z, sp) in enumerate(lines):
        o = MD.text3d(f"S7_title{j}", S.coll, txt, C.FONT_BLACK, size=size, extrude=size * 0.12,
                      bevel=size * 0.025, mat=M.text_mat(matk), spacing=sp)
        t0 = 18 + 7 * j

        def fn(f, t0=t0, z=z, j=j):
            t = seg(f, t0, t0 + 13)
            eb = ease_back(t, 2.0)
            s = 0.6 + 0.4 * eb
            fl = 0.012 * math.sin(TAU * (f - t0) / 60.0 + j)
            return dict(loc=(0, 0.35, z - 0.15 * (1 - ease_out(t)) + fl),
                        rot=(math.pi / 2 - el0 - 1.3 * (1 - eb), 0, 0), scl=(s, s, s))
        U.animate(o, S.frames(), fn)
        hide_range(o, S.frames(), lambda f, t0=t0: f >= t0)
        S.cue(t0, "whoosh", dur=0.25, pitch=0.9 + 0.1 * j)
        S.cue(t0 + 6, "slam", size=0.5 + 0.25 * j)
    # light sweep across the bun and title
    sw = ST.area(S.sc, "S7_sweep", (-2.5, 1.2, 1.6), (0, 0, 0.8), 0, (0.25, 3.0), (1.0, 0.85, 0.6))
    for f in S.frames():
        t = seg(f, 30, 80)
        sw.location = (lerp(-2.6, 2.6, ease_io(t)), 1.4, 1.7)
        sw.keyframe_insert("location", frame=f)
        U.key_prop(sw.data, "energy", f, 900 * math.sin(math.pi * t))
    # steam + floating crumbs
    N = 22
    pts = np.stack([rng.uniform(-0.45, 0.45, N), rng.uniform(-0.3, 0.3, N),
                    rng.uniform(zs.get("chicken", 0.3) + 0.12, zs.get("chicken", 0.3) + 0.25, N)], 1)
    vel = np.stack([rng.normal(0, 0.001, N), rng.normal(0, 0.001, N), rng.uniform(0.006, 0.01, N)], 1)
    rot = fx.face_camera_euler(pts, cam(50)[0])
    S.looping("steam", "sprite", pts, vel, rng.uniform(50, 80, N), rng.uniform(0, 80, N), rng.uniform(0.35, 0.6, N),
              rot=rot, spin=np.zeros((N, 3)), wob=0.02, wf=0.04)
    S.ambient("crumbs_bg", "crumb", 50, box=((-1.8, 1.8), (0.6, 3.0), (-0.3, 2.2)), s=(0.012, 0.03))
    S.ambient("crumbs_fg", "crumb", 12, box=((-0.7, 0.7), (-2.4, -1.4), (0.1, 1.7)), s=(0.012, 0.022))
    S.ambient("seeds", "seed", 20, box=((-1.6, 1.6), (-1.2, 2.0), (-0.2, 2.0)), s=(0.022, 0.028),
              sv=np.tile([1.0, 0.52, 0.25], (20, 1)))
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.6), k=0.75, rim=1.4)
    S.cue(1, "boom")
    S.cue(1, "sizzle_soft", dur=n / C.FPS)
    S.ov(type="sparkle", t0=40, t1=n)
    return S


BUILDERS = {
    "S1_intro": shot_intro,
    "S2_ingredients": shot_ingredients,
    "S3_prep": shot_prep,
    "S4_fry": shot_fry,
    "S5_build": shot_build,
    "S6_exploded": shot_exploded,
    "S7_final": shot_final,
}
