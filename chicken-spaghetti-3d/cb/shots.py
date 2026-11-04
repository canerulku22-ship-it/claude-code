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
from mathutils import Vector, Euler

import config as C
from . import util as U, materials as M, models as MD, stage as ST, fx
from .util import seg, lerp, ease_out, ease_in, ease_io, ease_back, smooth, impact, squash_scale

TAU = 2 * math.pi
Z_SAUCE = MD.PAN_FLOOR + 0.10        # sauce level in the skillet
DISH_SCALE = 0.8                     # plated dish is kept small in frame
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
        if proto in ("sprite", "bubble", "oil_bubble", "wdrop"):
            # steam / foam: no shadows, not seen in reflections -> far cheaper
            for a in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission"):
                setattr(o, a, False)
        return o

    def static_points(self, name, proto, pts, s, sv=None, parent=None):
        """Instances that never move (resting flakes, floating herbs)."""
        n = len(pts)
        per = np.full(n, 1e6)
        return self.looping(name, proto, pts, np.zeros((n, 3)), per, per * 0.5, s, sv=sv, parent=parent)

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


# ---------------------------------------------------- shared chicken layout --
N_CUBES = 12


def pan_layout():
    """Where the seared chicken cubes sit in the skillet (shared by S3, S4, S6)."""
    rng = np.random.default_rng(42)
    pts = []
    while len(pts) < N_CUBES:
        a = rng.uniform(0, TAU)
        r = 0.72 * math.sqrt(rng.uniform(0.02, 1.0))
        p = (r * math.cos(a), r * math.sin(a))
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 0.26 for q in pts):
            pts.append(p)
    rz = rng.uniform(0, TAU, N_CUBES)
    flips = rng.integers(1, 3, N_CUBES)
    return [(pts[i][0], pts[i][1], rz[i], i, int(flips[i])) for i in range(N_CUBES)]


def cubes_in_pan(S, prefix, mat, center=(0, 0), z_floor=MD.PAN_FLOOR + 0.004):
    out = []
    for x, y, rz, seed, flips in pan_layout():
        o = MD.chicken_cube(f"{prefix}_ck{seed}", S.coll, mat, seed)
        hz = o.data["hz"]
        o.location = (center[0] + x, center[1] + y, z_floor + hz)
        o.rotation_euler = (math.pi * flips, 0, rz)
        out.append(o)
    return out


# --------------------------------------------------------- plated dish -----
NEST_TOP = 0.5
NEST_R = 0.6


def plated(S, prefix, parm_static=True):
    """Spaghetti nest on a plate with sauce, seared chicken and basil.
    Everything is parented to the returned root empty (rotate / scale it)."""
    root = bpy.data.objects.new(f"{prefix}_dish", None)
    S.coll.objects.link(root)
    root.scale = (DISH_SCALE,) * 3
    pl = MD.plate(f"{prefix}_plate", S.coll)
    pl.parent = root
    rng = np.random.default_rng(11)               # identical nest in S1 and S7
    mat, P = M.pasta(f"{prefix}_pasta")
    P["cook"].outputs[0].default_value = 1.0
    P["sauce"].outputs[0].default_value = 0.36
    nest = MD.pasta_object(f"{prefix}_nest", S.coll, MD.nest_strands(rng, top=NEST_TOP, Rm=NEST_R), mat,
                           fx.pasta_static_group())
    nest.parent = root
    nest.location.z = MD.PLATE_TOP
    cap = MD.sauce_cap(f"{prefix}_sauce", S.coll, 0.28, 0.05, lambda r: MD.mound_z(r, NEST_TOP, NEST_R))
    cap.parent = root
    cap.location.z = MD.PLATE_TOP
    cm, CP = M.seared_chicken(f"{prefix}_ckmat")
    for k, v in (("season", 1.0), ("sear", 1.0), ("sauce", 0.35)):
        CP[k].outputs[0].default_value = v
    cubes = []
    for i, (r, a) in enumerate([(0.20, 0.4), (0.40, 1.3), (0.28, 2.3), (0.44, 3.1), (0.24, 4.0),
                                (0.42, 4.9), (0.33, 5.8)]):
        o = MD.chicken_cube(f"{prefix}_ck{i}", S.coll, cm, i)
        o.parent = root
        hz = o.data["hz"]
        z = MD.PLATE_TOP + MD.mound_z(r, NEST_TOP, NEST_R) * 0.92 + hz * 0.55
        o.location = (r * math.cos(a), r * math.sin(a), z)
        slope = 0.6 * r / NEST_R
        o.rotation_euler = (rng.uniform(-0.3, 0.3) + slope * math.sin(a), rng.uniform(-0.3, 0.3) - slope * math.cos(a),
                            rng.uniform(0, TAU))
        cubes.append(o)
    leaves = []
    for i, (x, y, rz, s) in enumerate([(0.02, 0.05, 0.6, 1.0), (-0.10, -0.06, 2.6, 0.85), (0.12, -0.08, 4.4, 0.75)]):
        lf = MD.basil_leaf(f"{prefix}_basil{i}", S.coll, 0.36 * s, seed=i + 3)
        lf.parent = root
        lf.location = (x, y, MD.PLATE_TOP + NEST_TOP + 0.07)
        lf.rotation_euler = (0.12, -0.18, rz)
        leaves.append(lf)
    parm = None
    if parm_static:
        pts = []
        for _ in range(170):
            r = 0.55 * math.sqrt(rng.uniform(0, 1))
            a = rng.uniform(0, TAU)
            pts.append((r * math.cos(a), r * math.sin(a), MD.PLATE_TOP + MD.mound_z(r, NEST_TOP, NEST_R) + 0.025))
        parm = S.static_points(f"{prefix}_parm", "parm", np.array(pts), rng.uniform(0.008, 0.016, len(pts)),
                               sv=np.stack([np.ones(len(pts)), rng.uniform(0.5, 1, len(pts)), np.ones(len(pts))], 1),
                               parent=root)
    return root, dict(plate=pl, nest=nest, cap=cap, cubes=cubes, leaves=leaves, parm=parm, pasta_params=P)


# ============================================================ S1 INTRO =====
def shot_intro(name, n):
    S = Shot(name, n, M.backdrop_world("W_intro", center=(0.5, 0.5), radius=0.85), fstop=4.0)
    MD.floor("S1_floor", S.coll, z=0.0)
    root, parts = plated(S, "S1")
    U.animate(root, S.frames(), lambda f: dict(rot=(0, 0, -0.7 + 0.013 * f)))
    S.ambient("herbs", "herb", 40, box=((-2.2, 2.2), (-1.0, 3.0), (-0.2, 3.0)), s=(0.008, 0.016))
    S.ambient("parm", "parm", 30, box=((-2.2, 2.2), (-1.0, 3.0), (-0.2, 3.0)), s=(0.01, 0.02))
    top = Vector((0, 0, (MD.PLATE_TOP + NEST_TOP) * DISH_SCALE))

    def cam(f):
        t = ease_io(seg(f, 1, 48), 2)
        d = lerp(8.6, 6.0, t)
        el = math.radians(lerp(16, 30, t))
        az = lerp(-0.25, 0.1, t)
        tgt = Vector((0, 0, lerp(0.35, 0.28, t)))
        t2 = ease_in(seg(f, 48, 60), 2.4)
        if t2 > 0:
            d = lerp(d, 1.2, t2)
            tgt = tgt.lerp(top, t2)
            el = lerp(el, math.radians(50), t2)
        return orbit(tgt, d, el, az), tgt, 50.0
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.3), k=0.42, rim=0.8, top=0.7)
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
    if key == "spaghetti":
        strands, at = MD.dry_bundle_strands(rng, n=130, L=2.5, br=0.11, flare=0.07)
        mat, P = M.pasta("S2_pasta")
        o = MD.pasta_object("S2_bundle", S.coll, strands, mat, fx.pasta_static_group(), radius=0.0085)
        add(o, (0, 0, -0.45), (0, 0, 0), 0.36)
        base_rot = (0.25, 0.75, 0.3)
    elif key == "chicken":
        m, p = M.chicken("S2_chicken_mat")
        add(MD.chicken("S2_chicken_obj", S.coll, m), (0, 0, -0.05), scl=0.5)
        base_rot = (1.15, 0, 0.12)
    elif key == "seasoning":
        add(MD.shaker("S2_shaker", S.coll), (0, 0, -0.24), scl=1.0)
        base_rot = (0.15, 0, 0.2)
    elif key == "oil":
        add(MD.oil_bottle("S2_oil", S.coll), (0, 0, -0.3), scl=0.62)
        base_rot = (0.12, 0, 0.3)
    elif key == "garlic":
        add(MD.garlic_bulb("S2_garlic", S.coll), (0, 0, -0.25), scl=0.85)
        base_rot = (0.35, 0, 0)
    elif key == "onion":
        add(MD.onion("S2_onion", S.coll), (0, 0, -0.26), scl=0.75)
        base_rot = (0.3, 0, 0.5)
    elif key == "tomato":
        add(MD.dish("S2_tomdish", S.coll), (0, 0, -0.06), scl=0.4)
        add(MD.sauce_surface("S2_tom", S.coll, 0.77, MD.DISH_LIQ_Z, amp=0.02), (0, 0, -0.06 + MD.DISH_LIQ_Z * 0.4), scl=0.4)
        base_rot = (0.95, 0, 0)
    elif key == "basil":
        add(MD.basil_sprig("S2_basil", S.coll, 4, 0.5), (-0.05, 0, -0.05), scl=0.9)
        base_rot = (1.0, 0.2, 0.4)
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
        hero = key == "chicken"

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
    S.ambient("dust", "parm", 30, box=((-2.0, 2.0), (-3.5, 2.0), (-3.2, 3.0)), s=(0.004, 0.009))
    S.camera_path(lambda f: (cam_loc(f), tgt, 50.0))
    S.ov(type="header", num="", text="THE INGREDIENTS", t0=3, t1=89)
    S.cue(92, "whoosh", dur=0.5, up=True)
    return S


# ===================================================== S3 SEASON + SEAR =====
def shot_sear(name, n):
    S = Shot(name, n, M.backdrop_world("W_sear", center=(0.5, 0.62), inner=(0.07, 0.042, 0.024), radius=0.9),
             fstop=5.6, lens=40)
    rng = S.rng
    BX = Vector((-2.4, 0.0, 0.0))        # board centre
    PX = Vector((1.3, 0.25, 0.0))        # skillet centre
    MD.floor("S3_floor", S.coll, z=-0.08)
    MD.cutting_board("S3_board", S.coll, sx=1.55, sy=1.15).location = BX
    pan = MD.skillet("S3_pan", S.coll)
    pan.location = PX
    pan.rotation_euler = (0, 0, 0.35)
    OILZ = MD.PAN_FLOOR + 0.004
    MD.oil_film("S3_oil", S.coll, MD.pan_inner_r(OILZ + 0.005), OILZ).location = PX
    mat, PRM = M.seared_chicken("S3_ckmat")
    layout = pan_layout()
    T_LAUNCH, T_FLIP = 46, 92
    cubes, info = [], []
    for k, (x, y, rz, seed, flips) in enumerate(layout):
        o = MD.chicken_cube(f"S3_ck{seed}", S.coll, mat, seed)
        hz = o.data["hz"]
        a = rng.uniform(0, TAU)
        r = 0.42 * math.sqrt(rng.uniform(0, 1))
        b = BX + Vector((r * math.cos(a) * 1.2, r * math.sin(a), hz))
        p = PX + Vector((x, y, OILZ + hz))
        e = T_LAUNCH + 1.1 * k + rng.uniform(0, 0.8)
        dur = 13 + rng.uniform(0, 3)
        tf = T_FLIP + rng.uniform(0, 8)
        rz0 = rng.uniform(0, TAU)
        info.append((o, b, p, e, dur, tf, rz0, rz, flips))
        cubes.append(o)

    def cube_fn(f, b, p, e, dur, tf, rz0, rz1, flips):
        u = seg(f, e, e + dur)
        if f < e:
            return dict(loc=b, rot=(0, 0, rz0), scl=(1, 1, 1))
        pos = b.lerp(p, ease_io(u, 1.6)) + Vector((0, 0, 1.15 * 4 * u * (1 - u)))
        rx = math.pi * flips * ease_io(u, 1.5)
        rzz = lerp(rz0, rz1, ease_io(u))
        sq = 0.0
        if f >= e + dur:
            sq = 0.18 * impact((f - e - dur) / C.FPS, 3.6, 9.0)
            pos = p + Vector((0, 0, 0.004 * math.sin(f * 2.3 + rz1 * 5) * seg(f, e + dur, e + dur + 4)))
        v = seg(f, tf, tf + 11)
        if v > 0:
            pos = pos + Vector((0, 0, 0.16 * math.sin(math.pi * v)))
            rx += math.pi * ease_io(v)
        return dict(loc=pos, rot=(rx, 0, rzz), scl=squash_scale(sq))
    for o, b, p, e, dur, tf, rz0, rz1, flips in info:
        U.animate(o, S.frames(), lambda f, a=(b, p, e, dur, tf, rz0, rz1, flips): cube_fn(f, *a))
    for f in S.frames():
        U.key_socket(PRM["season"].outputs[0], f, smooth(seg(f, 14, 40)))
        U.key_socket(PRM["sear"].outputs[0], f, smooth(seg(f, 64, 128)))
    # ---- seasoning shaker ----------------------------------------------
    sh = MD.shaker("S3_shaker", S.coll)
    sh_rot = Euler((0.0, -2.55, 0.0))
    cap_dir = sh_rot.to_matrix() @ Vector((0, 0, 1))
    sh_home = BX + Vector((0.55, -0.05, 1.3))
    SHAKES = [14, 22, 30]

    def sh_loc(f):
        p = (BX + Vector((1.9, -0.05, 2.6))).lerp(sh_home, ease_out(seg(f, 5, 12), 3))
        for fs in SHAKES:
            p = p + cap_dir * 0.1 * math.exp(-((f - fs) / 1.6) ** 2)
        return p.lerp(BX + Vector((2.2, -0.05, 2.8)), ease_in(seg(f, 34, 44), 2))
    U.animate(sh, S.frames(), lambda f: dict(
        loc=sh_loc(f), rot=(0, -2.55 + 0.12 * sum(math.exp(-((f - fs) / 1.6) ** 2) for fs in SHAKES), 0.0),
        scl=(1.1, 1.1, 1.1)))
    hide_range(sh, S.frames(), lambda f: 5 <= f <= 44)
    # spice + herb bursts land on the cubes / board, then fade into the meat
    verts, polys = [], []
    for o, b, *_ in info:
        me = o.data
        off = len(verts)
        verts += [b + Vector((0, 0, 0)) + Euler((0, 0, 0)).to_matrix() @ v.co for v in me.vertices]
        polys += [tuple(off + i for i in pl.vertices) for pl in me.polygons]
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons(verts, polys)
    cap = sh_home + cap_dir * 0.53 * 1.1
    for j, fs in enumerate(SHAKES):
        for proto, N, sz in (("spice", 120, (0.006, 0.011)), ("herb", 45, (0.008, 0.014))):
            p0, v0 = burst(rng, N, cap, 0.03, cap_dir * 1.2, 0.4)
            e = fs + rng.uniform(-0.5, 3.0, N)
            land = fx.landing(p0, v0, 30.0, bvh=bvh, floor_z=0.0, max_frames=40)
            S.ballistic(f"{proto}{j}", proto, p0, v0, e, land, land + rng.uniform(6, 14, N), 8.0,
                        rng.uniform(*sz, N), sv=(1, 1, 0.6) if proto == "herb" else None)
        S.cue(fs, "shake")
    S.cue(18, "sprinkle", dur=0.5)
    # ---- sizzle: spatter, oil bubbles, steam ----------------------------
    for k, (o, b, p, e, dur, *_r) in enumerate(info):
        land_f = e + dur
        N = 10
        th = rng.uniform(0, TAU, N)
        p0 = np.stack([p.x + 0.12 * np.cos(th), p.y + 0.12 * np.sin(th), np.full(N, OILZ + 0.01)], 1)
        v0 = np.stack([0.5 * np.cos(th), 0.5 * np.sin(th), rng.uniform(1.0, 2.2, N)], 1)
        land = fx.landing(p0, v0, 30.0, floor_z=OILZ, max_frames=30)
        S.ballistic(f"spat{k}", "oil_drop", p0, v0, land_f + rng.uniform(0, 2, N), land, land, 1.0,
                    rng.uniform(0.006, 0.012, N))
        if k % 3 == 0:
            S.cue(land_f, "thud", size=0.35, soft=True)
    pts = []
    for x, y, *_ in layout:
        th = rng.uniform(0, TAU, 36)
        rr = rng.uniform(0.11, 0.19, 36)
        pts += [(PX.x + x + r_ * math.cos(t_), PX.y + y + r_ * math.sin(t_), OILZ + 0.003) for r_, t_ in zip(rr, th)]
    pts = np.array(pts)
    foam = S.looping("foam", "oil_bubble", pts, np.zeros_like(pts), rng.uniform(4, 11, len(pts)),
                     rng.uniform(0, 20, len(pts)), rng.uniform(0.006, 0.014, len(pts)), pop=1.0, density=0.0)
    key_density(foam, S.frames(), lambda f: 0.9 * smooth(seg(f, T_LAUNCH + 12, T_LAUNCH + 24)))
    cam_mid = orbit(PX, 4.0, math.radians(52), -0.1)
    st = S.steam("steam", (PX.x, PX.y), 0.6, (0.25, 0.5), 22, cam_mid)
    key_density(st, S.frames(), lambda f: 0.9 * smooth(seg(f, 70, 88)))
    S.cue(T_LAUNCH + 13, "sizzle_start")
    S.cue(T_LAUNCH, "whoosh", dur=0.45)
    S.cue(T_FLIP, "whoosh", dur=0.3)
    S.cue(T_FLIP + 10, "sizzle_soft", dur=1.2)
    # ---- camera ------------------------------------------------------------
    def cam(f):
        t = ease_io(seg(f, 42, 62), 2.2)
        tgt = (BX + Vector((0, 0, 0.12))).lerp(PX + Vector((0, 0, 0.1)), t)
        d = lerp(3.6, 4.6, t)
        el = math.radians(lerp(44, 54, t))
        az = lerp(-0.15, -0.05, t) + 0.0008 * f
        lens = 40.0
        t2 = ease_io(seg(f, 104, n), 2)
        if t2 > 0:
            tgt = tgt.lerp(PX + Vector((0.1, -0.25, 0.12)), t2)
            d = lerp(d, 2.5, t2)
            el = lerp(el, math.radians(36), t2)
            lens = lerp(40, 55, t2)
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (-0.5, 0, 0.1), k=0.32, rim=0.5, top=0.6)
    S.header("season", 3, 42)
    S.header("sear", 60, 118)
    S.ov(type="haze", t0=64, t1=n, y0=0.0, y1=0.5, amp=2.0)
    if C.SEAR_TEMPERATURE_LABEL:
        S.ov(type="temp", text=C.SEAR_TEMPERATURE_LABEL, t0=66, t1=118)
    hero = info[5]
    S.track("sear", lambda f, o=hero: hero[2] + Vector((0, 0, 0.12)))
    S.ov(type="callout", text="GOLDEN SEAR", track="sear", t0=112, t1=n, dx=-200, dy=-300)
    return S


# =========================================================== S4 SAUCE ======
def shot_sauce(name, n):
    S = Shot(name, n, M.backdrop_world("W_sauce", center=(0.5, 0.62), inner=(0.07, 0.04, 0.022), radius=0.9),
             fstop=5.6, lens=40)
    rng = S.rng
    MD.floor("S4_floor", S.coll, z=-0.0)
    MD.skillet("S4_pan", S.coll).rotation_euler = (0, 0, 0.35)
    mat, PRM = M.seared_chicken("S4_ckmat")
    PRM["season"].outputs[0].default_value = 1.0
    PRM["sear"].outputs[0].default_value = 1.0
    cubes = cubes_in_pan(S, "S4", mat)
    FL = MD.PAN_FLOOR + 0.006
    # garlic + onion
    for proto, N, t0, sz, org in (("garlic", 45, 8, (0.016, 0.026), (-0.25, 0.1, 1.9)),
                                  ("onion", 55, 14, (0.024, 0.04), (0.2, -0.1, 1.9))):
        p0, v0 = burst(rng, N, org, 0.1, (0, 0, -0.5), 0.55)
        e = t0 + rng.uniform(0, 5, N)
        land = fx.landing(p0, v0, 30.0, floor_z=FL, max_frames=50)
        S.ballistic(proto, proto, p0, v0, e, land, np.full(N, 1e5), 1.0, rng.uniform(*sz, N), spin=0.4)
        S.cue(t0 + 6, "sprinkle", dur=0.5)
    S.cue(14, "sizzle_soft", dur=1.4)
    # ---- the pour ----------------------------------------------------------
    T_IN, T_TILT, T_POUR, T_END, T_OUT = 26, 36, 41, 72, 78
    bowl = bpy.data.objects.new("S4_bowl", None)
    S.coll.objects.link(bowl)
    bd = MD.dish("S4_bowl_dish", S.coll)
    bd.parent = bowl
    bl = MD.sauce_surface("S4_bowl_sauce", S.coll, 0.77, 0.0, amp=0.015)
    bl.parent = bowl
    BS = 0.7
    home = Vector((-0.95, 0.35, 1.35))

    def bowl_fn(f):
        p = Vector((-2.4, 0.9, 2.8)).lerp(home, ease_out(seg(f, T_IN, T_TILT), 3))
        p = p.lerp(Vector((-2.6, 1.0, 3.0)), ease_in(seg(f, T_OUT, T_OUT + 12), 2))
        tilt = 1.2 * ease_io(seg(f, T_TILT, T_POUR + 4)) * (1 - ease_io(seg(f, T_END, T_OUT + 2)))
        return dict(loc=p, rot=(0, tilt, 0.0), scl=(BS, BS, BS))
    U.animate(bowl, S.frames(), bowl_fn)
    U.animate(bl, S.frames(), lambda f: dict(
        loc=(0, 0, lerp(MD.DISH_LIQ_Z, 0.07, smooth(seg(f, T_POUR, T_END)))),
        scl=(lerp(1.0, 0.75, smooth(seg(f, T_POUR, T_END))),) * 2 + (1.0,)))
    hide_tree(bowl, S.frames(), lambda f: T_IN <= f <= T_OUT + 12)
    tilt_m = Euler((0, 1.2, 0)).to_matrix()
    lip = home + tilt_m @ (Vector((0.86, 0, 0.25)) * BS)
    hit = Vector((0.05, 0.12, Z_SAUCE))
    pts = []
    vx = (hit.x - lip.x) / 0.32
    vy = (hit.y - lip.y) / 0.32
    for i in range(40):
        t = 0.32 * i / 39
        z = lip.z - 0.5 * 9.0 * t * t + (hit.z - lip.z + 0.5 * 9.0 * 0.32 ** 2) * t / 0.32
        pts.append((lip.x + vx * t, lip.y + vy * t, z))
    stm = MD.stream("S4_stream", S.coll, pts, 0.055, M.tomato_sauce(), taper=(1.0, 0.65))
    for f in S.frames():
        U.key_prop(stm.data, "bevel_factor_end", f, ease_in(seg(f, T_POUR, T_POUR + 5), 1.5))
        U.key_prop(stm.data, "bevel_factor_start", f, ease_in(seg(f, T_END - 2, T_END + 4), 1.5))
    hide_range(stm, S.frames(), lambda f: T_POUR <= f <= T_END + 4)
    S.cue(T_POUR, "pour", dur=(T_END - T_POUR) / C.FPS)
    # sauce surface rises in the skillet
    R_S = MD.pan_inner_r(Z_SAUCE) - 0.004
    sauce = MD.sauce_surface("S4_sauce", S.coll, R_S, Z_SAUCE)

    def lvl(f):
        return lerp(MD.PAN_FLOOR - 0.02, Z_SAUCE, smooth(seg(f, T_POUR + 3, T_END + 4)))
    U.animate(sauce, S.frames(), lambda f: dict(
        loc=(0, 0, lvl(f)), scl=((MD.pan_inner_r(max(lvl(f), MD.PAN_FLOOR)) - 0.004) / R_S,) * 2 + (1.0,)))
    fx.set_inputs(sauce, sauce.modifiers["Ripple"], {"RingStart": float(T_POUR + 4), "RingAmp": 0.012,
                                                     "RingCenter": (hit.x, hit.y, 0.0)})
    p0, v0 = burst(rng, 45, (hit.x, hit.y, Z_SAUCE + 0.02), 0.04, (0, 0, 1.6), 0.6)
    land = fx.landing(p0, v0, 30.0, floor_z=Z_SAUCE, max_frames=40)
    S.ballistic("splash", "drop", p0, v0, T_POUR + 4 + rng.uniform(0, 3, 45), land, land, 1.0,
                rng.uniform(0.01, 0.022, 45))
    S.cue(T_POUR + 4, "splash", size=0.7)
    for f in S.frames():
        U.key_socket(PRM["sauce"].outputs[0], f, 0.45 * smooth(seg(f, T_POUR + 8, T_END + 8)))
    # ---- herbs + simmer ----------------------------------------------------
    for proto, N in (("herb", 130), ("spice", 50)):
        p0, v0 = burst(rng, N, (0.1, 0.0, 1.8), 0.12, (0, 0, -0.3), 0.5)
        e = 84 + rng.uniform(0, 6, N)
        land = fx.landing(p0, v0, 30.0, floor_z=Z_SAUCE + 0.004, max_frames=50)
        S.ballistic(f"top_{proto}", proto, p0, v0, e, land, np.full(N, 1e5), 1.0,
                    rng.uniform(0.007, 0.013, N), sv=(1, 1, 0.5) if proto == "herb" else None, spin=0.3)
    S.cue(86, "sprinkle", dur=0.6)
    pts = disc_points(rng, 50, 0.1, 0.85, Z_SAUCE + 0.004)
    blub = S.looping("blub", "blub", pts, np.zeros_like(pts), rng.uniform(16, 32, 50), rng.uniform(0, 30, 50),
                     rng.uniform(0.02, 0.045, 50), sv=(1, 1, 0.7), pop=1.0, density=0.0)
    key_density(blub, S.frames(), lambda f: 0.85 * smooth(seg(f, 80, 96)))
    S.cue(82, "simmer", dur=(n - 82) / C.FPS)
    cam0 = orbit((0, 0, 0.1), 5.2, math.radians(56), -0.1)
    st = S.steam("steam", (0, 0), 0.7, (0.3, 0.6), 20, cam0)
    key_density(st, S.frames(), lambda f: 0.85 * smooth(seg(f, 72, 92)))

    def cam(f):
        tgt = Vector((0, 0, 0.1))
        d, el, az, lens = 5.4, math.radians(56), -0.12 + 0.0018 * f, 40.0
        t = ease_io(seg(f, 92, n), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((-0.15, -0.2, Z_SAUCE)), t)
            d, el, lens = lerp(d, 3.0, t), lerp(el, math.radians(40), t), lerp(40, 52, t)
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.1), k=0.26, rim=0.5, top=0.6)
    S.header("sauce", 3, 112)
    S.track("sauce", lambda f: Vector((-0.35, -0.42, Z_SAUCE)))
    S.ov(type="callout", text="RICH TOMATO SAUCE", track="sauce", t0=98, t1=n, dx=-120, dy=330)
    return S


# ============================================================ S5 BOIL ======
def shot_boil(name, n):
    S = Shot(name, n, M.backdrop_world("W_boil", center=(0.5, 0.6), inner=(0.06, 0.045, 0.03), radius=0.9),
             fstop=5.6, lens=40)
    rng = S.rng
    WZ, R = MD.POT_WATER_Z, MD.POT_R_IN
    MD.floor("S5_floor", S.coll, z=0.0)
    MD.pot("S5_pot", S.coll)
    water = MD.water_surface("S5_water", S.coll, R - 0.003, WZ)
    T_DROP, T_HIT = 9, 17
    fx.set_inputs(water, water.modifiers["Ripple"], {"RingStart": float(T_HIT), "RingAmp": 0.02,
                                                     "RingCenter": (0, 0, WZ)})
    # boiling: surface pops + rising bubbles + steam
    pts = disc_points(rng, 160, 0.0, R - 0.06, WZ + 0.002)
    S.looping("pops", "bubble", pts, np.zeros_like(pts), rng.uniform(6, 16, 160), rng.uniform(0, 20, 160),
              rng.uniform(0.012, 0.03, 160), sv=(1, 1, 0.6), pop=1.0)
    N = 110
    per = rng.uniform(10, 24, N)
    pts = disc_points(rng, N, 0.0, R - 0.08, MD.POT_FLOOR + 0.02)
    vel = np.zeros((N, 3))
    vel[:, 2] = (WZ - MD.POT_FLOOR - 0.03) / per
    S.looping("rise", "bubble", pts, vel, per, rng.uniform(0, 24, N), rng.uniform(0.006, 0.014, N),
              wob=0.01, wf=0.3)
    cam0 = orbit((0, 0, 0.6), 5.4, math.radians(48), -0.1)
    st = S.steam("steam", (0, 0), 0.7, (WZ + 0.15, WZ + 0.45), 24, cam0, s=(0.35, 0.55))
    key_density(st, S.frames(), lambda f: 1.0)
    S.cue(1, "boil", dur=n / C.FPS)
    # pinch of salt
    p0, v0 = burst(rng, 60, (0.15, -0.1, 1.7), 0.05, (0, 0, -0.6), 0.25)
    land = fx.landing(p0, v0, 30.0, floor_z=WZ, max_frames=40)
    S.ballistic("salt", "salt", p0, v0, 4 + rng.uniform(0, 5, 60), land, land, 1.0, rng.uniform(0.005, 0.009, 60))
    S.cue(6, "sprinkle", dur=0.4)
    # dry spaghetti: drop, fan out, soften and sink
    strands, at = MD.dry_bundle_strands(rng, n=110, L=2.2, br=0.075)
    mat, P = M.pasta("S5_pasta")
    pasta = MD.pasta_object("S5_pasta", S.coll, strands, mat, fx.pasta_dry_group(),
                            {"BaseZ": MD.POT_FLOOR + 0.01, "Zmin": MD.POT_FLOOR + 0.012, "Rmax": R - 0.03,
                             "Swirl": 0.7}, strand_attrs=at, radius=0.0088)
    for f in S.frames():
        fx.key_input(pasta, "Pasta", "Drop", f, 2.4 * (1 - ease_in(seg(f, T_DROP, T_HIT), 2.0)))
        fx.key_input(pasta, "Pasta", "Fan", f, ease_out(seg(f, T_HIT, T_HIT + 12), 2.5))
        fx.key_input(pasta, "Pasta", "Soft", f, ease_io(seg(f, 40, 98), 1.6))
        U.key_socket(P["cook"].outputs[0], f, smooth(seg(f, 40, 92)))
    hide_range(pasta, S.frames(), lambda f: f >= T_DROP - 1)
    p0 = disc_points(rng, 60, 0.05, 0.2, WZ + 0.01)
    th = np.arctan2(p0[:, 1], p0[:, 0])
    v0 = np.stack([0.6 * np.cos(th), 0.6 * np.sin(th), rng.uniform(1.2, 2.6, 60)], 1)
    land = fx.landing(p0, v0, 30.0, floor_z=WZ, max_frames=40)
    S.ballistic("splash", "wdrop", p0, v0, T_HIT + rng.uniform(0, 2, 60), land, land, 1.0, rng.uniform(0.01, 0.02, 60))
    S.cue(T_DROP, "whoosh", dur=0.3)
    S.cue(T_HIT, "splash", size=0.8)
    S.cue(T_HIT + 2, "clatter")

    def cam(f):
        tgt = Vector((0, 0, 0.62))
        d, el, az, lens = 5.6, math.radians(46), -0.15 + 0.002 * f, 40.0
        t = ease_io(seg(f, 76, n), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0, 0, WZ)), t)
            d, el, lens = lerp(d, 3.4, t), lerp(el, math.radians(60), t), lerp(40, 48, t)
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.5), k=0.45, rim=0.7, top=0.9)
    S.header("boil", 3, 98)
    S.track("pasta", lambda f: Vector((0.3, -0.35, WZ)))
    S.ov(type="callout", text="AL DENTE", track="pasta", t0=84, t1=n, dx=160, dy=-320)
    return S


# ============================================================ S6 TOSS ======
def shot_toss(name, n):
    S = Shot(name, n, M.backdrop_world("W_toss", center=(0.5, 0.62), inner=(0.07, 0.042, 0.024), radius=0.9),
             fstop=5.6, lens=40)
    rng = S.rng
    MD.floor("S6_floor", S.coll, z=0.0)
    MD.skillet("S6_pan", S.coll).rotation_euler = (0, 0, 0.35)
    sauce = MD.sauce_surface("S6_sauce", S.coll, MD.pan_inner_r(Z_SAUCE) - 0.004, Z_SAUCE)
    mat, PRM = M.seared_chicken("S6_ckmat")
    for k, v in (("season", 1.0), ("sear", 1.0), ("sauce", 0.45)):
        PRM[k].outputs[0].default_value = v
    cubes = cubes_in_pan(S, "S6", mat, z_floor=MD.PAN_FLOOR + 0.004)
    herbs = disc_points(rng, 120, 0.05, 0.95, Z_SAUCE + 0.004)
    S.static_points("herbs", "herb", herbs, rng.uniform(0.007, 0.013, 120), sv=(1, 1, 0.5))
    pts = disc_points(rng, 40, 0.1, 0.9, Z_SAUCE + 0.004)
    S.looping("blub", "blub", pts, np.zeros_like(pts), rng.uniform(16, 32, 40), rng.uniform(0, 30, 40),
              rng.uniform(0.02, 0.04, 40), sv=(1, 1, 0.7), pop=1.0, density=0.55)
    S.cue(1, "simmer", dur=n / C.FPS)
    # cooked spaghetti: falls in, gets sauced, tossed
    T_FALL, T_TOSS = 5, 58
    strands = MD.pile_strands(rng, n=230, Rp=0.72, h=0.27, z0=Z_SAUCE - 0.035)
    nS = len(strands)
    at = dict(e=rng.uniform(0, 1.5, nS), ta=rng.uniform(0.6, 1.25, nS), td=rng.uniform(0, 5, nS))
    pm, PP = M.pasta("S6_pasta")
    PP["cook"].outputs[0].default_value = 1.0
    pasta = MD.pasta_object("S6_pasta", S.coll, strands, pm, fx.pasta_pile_group(),
                            {"FallStart": float(T_FALL), "FallDur": 8.0, "Height": 1.5, "TossStart": float(T_TOSS),
                             "TossDur": 15.0, "TossAmp": 0.55}, strand_attrs=at, radius=0.0105)
    for f in S.frames():
        U.key_socket(PP["sauce"].outputs[0], f, 0.42 * smooth(seg(f, 18, 50)) + 0.12 * smooth(seg(f, T_TOSS, 82)))
    T_LAND = T_FALL + 11
    S.cue(T_FALL, "whoosh", dur=0.35)
    S.cue(T_LAND, "splat")
    S.cue(T_TOSS, "whoosh", dur=0.4, up=True)
    S.cue(T_TOSS + 15, "splat")
    for (o, (x, y, rz, seed, flips)) in zip(cubes, pan_layout()):
        base = Vector(o.location)
        rot0 = Euler(o.rotation_euler)
        td = T_TOSS + rng.uniform(0, 5)
        amp = rng.uniform(0.3, 0.6)
        spin = rng.choice([-1, 1]) * math.pi

        def fn(f, base=base, rot0=rot0, td=td, amp=amp, spin=spin):
            u = seg(f, td, td + 15)
            return dict(loc=base + Vector((0, 0, amp * 4 * u * (1 - u))),
                        rot=(rot0.x + spin * ease_io(u), rot0.y, rot0.z + 0.6 * ease_io(u)))
        U.animate(o, S.frames(), fn)
    for t0, N in ((T_LAND, 40), (T_TOSS + 2, 50), (T_TOSS + 15, 35)):
        p0 = disc_points(rng, N, 0.1, 0.7, Z_SAUCE + 0.05)
        th = np.arctan2(p0[:, 1], p0[:, 0])
        v0 = np.stack([0.5 * np.cos(th), 0.5 * np.sin(th), rng.uniform(1.0, 2.4, N)], 1)
        land = fx.landing(p0, v0, 30.0, floor_z=Z_SAUCE, max_frames=40)
        S.ballistic(f"drops{t0}", "drop", p0, v0, t0 + rng.uniform(0, 3, N), land, land, 1.0,
                    rng.uniform(0.008, 0.018, N))
    cam0 = orbit((0, 0, 0.15), 5.2, math.radians(45), -0.1)
    st = S.steam("steam", (0, 0), 0.7, (0.3, 0.6), 20, cam0)
    key_density(st, S.frames(), lambda f: 0.85)

    def cam(f):
        tgt = Vector((0, 0, 0.16))
        d, el, az, lens = 5.2, math.radians(46), -0.2 + 0.002 * f, 40.0
        sh = 0.02 * math.sin(f * 1.9) * seg(f, T_TOSS - 1, T_TOSS + 2) * (1 - seg(f, T_TOSS + 6, T_TOSS + 12))
        tgt = tgt + Vector((sh, 0, sh))
        t = ease_io(seg(f, 80, n), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0.1, -0.15, Z_SAUCE + 0.12)), t)
            d, el, lens = lerp(d, 3.1, t), lerp(el, math.radians(34), t), lerp(40, 52, t)
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.15), k=0.26, rim=0.5, top=0.6)
    S.header("toss", 3, 98)
    S.track("pasta", lambda f: Vector((0.25, -0.35, Z_SAUCE + 0.16)))
    S.ov(type="callout", text="FULLY COATED", track="pasta", t0=86, t1=n, dx=-170, dy=-330)
    return S


# =========================================================== S7 FINAL ======
def shot_final(name, n):
    S = Shot(name, n, M.backdrop_world("W_final", center=(0.5, 0.58), inner=(0.11, 0.06, 0.03), radius=0.85),
             fstop=4.0, lens=50)
    rng = S.rng
    MD.floor("S7_floor", S.coll, z=0.0)
    root, parts = plated(S, "S7", parm_static=False)
    U.animate(root, S.frames(), lambda f: dict(rot=(0, 0, 0.2 + 0.008 * f)))
    # basil leaves drop on top
    for i, lf in enumerate(parts["leaves"]):
        rest = Vector(lf.location)
        r0 = Euler(lf.rotation_euler)
        t0 = 14 + 5 * i

        def fn(f, rest=rest, r0=r0, t0=t0, i=i):
            u = seg(f, t0, t0 + 10)
            z = rest.z + 1.4 * (1 - ease_in(u, 2))
            if f > t0 + 10:
                z += 0.02 * impact((f - t0 - 10) / C.FPS, 3.0, 8.0)
            return dict(loc=(rest.x, rest.y, z), rot=(r0.x + 0.6 * (1 - u), r0.y, r0.z + 1.5 * (1 - u)))
        U.animate(lf, S.frames(), fn)
        hide_range(lf, S.frames(), lambda f, t0=t0: f >= t0)
        S.cue(t0 + 10, "pop", pitch=0.8 + 0.1 * i)
    # parmesan snow lands on the nest (root-local coordinates)
    N = 380
    p0 = np.stack([rng.uniform(-0.5, 0.5, N), rng.uniform(-0.5, 0.5, N), rng.uniform(2.4, 3.2, N)], 1)
    v0 = np.stack([rng.normal(0, 0.08, N), rng.normal(0, 0.08, N), rng.uniform(-0.6, -0.2, N)], 1)
    bvh = MD.mound_bvh(NEST_TOP, NEST_R, MD.PLATE_TOP)
    land = fx.landing(p0, v0, 6.0, drag=1.5, bvh=bvh, floor_z=MD.PLATE_TOP, max_frames=80)
    S.ballistic("parm", "parm", p0, v0, 34 + rng.uniform(0, 26, N), land, np.full(N, 1e5), 1.0,
                rng.uniform(0.008, 0.016, N), gravity=6.0, drag=1.5, parent=root, spin=0.6,
                sv=np.stack([np.ones(N), rng.uniform(0.5, 1, N), np.ones(N)], 1))
    S.cue(36, "sprinkle", dur=1.0)
    cam_el = lambda f: math.radians(lerp(20, 24, ease_io(seg(f, 1, n))))
    cam_d = lambda f: lerp(6.9, 6.4, ease_io(seg(f, 1, n)))
    tgt = Vector((0, 0, 0.82))

    def cam(f):
        return orbit(tgt, cam_d(f), cam_el(f), 0.0), tgt, 50.0
    # 3D title (kept small, above the dish)
    lines = [(C.FINAL_TEXT[0], 0.115, "cream", 2.17, 1.25),
             (C.FINAL_TEXT[1], 0.15, "gold", 1.93, 1.1),
             (C.FINAL_TEXT[2], 0.33, "cream", 1.58, 1.0)]
    el0 = cam_el(60)
    for j, (txt, size, matk, z, sp) in enumerate(lines):
        o = MD.text3d(f"S7_title{j}", S.coll, txt, C.FONT_BLACK, size=size, extrude=size * 0.12,
                      bevel=size * 0.025, mat=M.text_mat(matk), spacing=sp)
        t0 = 24 + 7 * j

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
    sw = ST.area(S.sc, "S7_sweep", (-2.5, 1.2, 1.6), (0, 0, 0.6), 0, (0.25, 3.0), (1.0, 0.85, 0.6))
    for f in S.frames():
        t = seg(f, 40, 95)
        sw.location = (lerp(-2.6, 2.6, ease_io(t)), 1.4, 1.6)
        sw.keyframe_insert("location", frame=f)
        U.key_prop(sw.data, "energy", f, 700 * math.sin(math.pi * t))
    st = S.steam("steam", (0, 0), 0.4, (0.55, 0.8), 14, cam(60)[0], s=(0.3, 0.45))
    key_density(st, S.frames(), lambda f: 0.8)
    S.ambient("herbs_bg", "herb", 40, box=((-2.0, 2.0), (0.6, 3.0), (-0.2, 3.0)), s=(0.008, 0.015))
    S.ambient("parm_bg", "parm", 26, box=((-2.0, 2.0), (0.6, 3.0), (-0.2, 3.0)), s=(0.01, 0.02))
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.4), k=0.42, rim=0.8, top=0.7)
    S.cue(1, "boom")
    S.cue(1, "simmer", dur=n / C.FPS, level=0.5)
    S.ov(type="sparkle", t0=44, t1=n)
    return S


BUILDERS = {
    "S1_intro": shot_intro,
    "S2_ingredients": shot_ingredients,
    "S3_sear": shot_sear,
    "S4_sauce": shot_sauce,
    "S5_boil": shot_boil,
    "S6_toss": shot_toss,
    "S7_final": shot_final,
}
