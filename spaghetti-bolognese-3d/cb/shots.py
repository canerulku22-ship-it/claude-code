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
Z_SAUCE = MD.PAN_FLOOR + 0.10        # ragu level in the skillet
FLOOR = MD.PAN_FLOOR + 0.004         # top of the oil film
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
                  parent=None, spin=0.15):
        n = len(p0)
        attrs = dict(p0=p0, v0=v0, e=e, land=land, life=life, fade=np.full(n, fade) if np.isscalar(fade) else fade,
                     s=s, sv=np.ones((n, 3)) if sv is None else np.broadcast_to(np.asarray(sv, float), (n, 3)),
                     rot=self.rng.uniform(0, TAU, (n, 3)), spin=self.rng.normal(0, spin, (n, 3)))
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


VEG = [  # key, base proto, colours, burst frame, count, size, pile centre
    ("onion", "onion_d", M.ONION, 8, 240, (0.022, 0.032), (-0.35, 0.15)),
    ("carrot", "carrot", M.CARROT, 18, 170, (0.018, 0.026), (0.35, 0.25)),
    ("celery", "celery", M.CELERY, 28, 150, (0.02, 0.03), (0.05, -0.38)),
    ("garlic", "garlic", M.GARLIC, 36, 50, (0.014, 0.02), (0.0, 0.0)),
]


def veg_protos(S, cook=None):
    """Per-shot diced-vegetable prototypes; cook=None -> animatable params."""
    out = {}
    for key, base, cols, *_ in VEG:
        m, p = M.veg(f"{S.name}_{key}", *cols)
        if cook is not None:
            p["cook"].outputs[0].default_value = cook
        out[key] = (S.proto(key, base, m), p)
    return out


def stir_spoon(S, t_in, t0, t1, t_out, a0=0.6, turns=0.42, R=0.45):
    """Wooden spoon that dips in and circles through the pan."""
    sp = MD.spoon(f"{S.name}_spoon", S.coll)

    def place(f):
        a = a0 + TAU * turns * ease_io(seg(f, t0, t1), 1.6)
        c = Vector((R * math.cos(a), R * math.sin(a), FLOOR + 0.03))
        d = (Vector((math.cos(a), math.sin(a), 0)) * 0.55 + Vector((0, 0, 1))).normalized()
        lift = 1.6 * (1 - ease_out(seg(f, t_in, t0), 3)) + 1.6 * ease_in(seg(f, t1, t_out), 2.5)
        q = d.to_track_quat("Z", "Y")
        return dict(loc=c + Vector((0.4, 0.2, 1.0)) * lift, rot=tuple(q.to_euler()))
    U.animate(sp, S.frames(), place)
    hide_range(sp, S.frames(), lambda f: t_in <= f <= t_out)
    return sp


def stir_empty(S, t0, t1, angle):
    e = bpy.data.objects.new(f"{S.name}_stir", None)
    S.coll.objects.link(e)
    U.animate(e, S.frames(), lambda f: dict(rot=(0, 0, angle * ease_io(seg(f, t0, t1), 1.6))))
    return e


def pan_scene(S):
    MD.floor(f"{S.name}_floor", S.coll, z=0.0)
    MD.skillet(f"{S.name}_pan", S.coll).rotation_euler = (0, 0, 0.35)


def ragu_surface(S, mince_proto, z=Z_SAUCE, n_meat=1300):
    R_S = MD.pan_inner_r(Z_SAUCE) - 0.004
    sauce = MD.sauce_surface(f"{S.name}_ragu", S.coll, R_S, z, amp=0.016, mat=M.ragu())
    rng = S.rng
    pts = disc_points(rng, n_meat, 0.0, R_S * 0.95, 0.006)
    S.static_points("meat", mince_proto, pts, rng.uniform(0.016, 0.03, n_meat), sv=flat_sv(rng, n_meat, (0.5, 0.75)),
                    parent=sauce)
    return sauce, R_S


def pan_cam(f, n, push_from, tgt_end, d0=5.3, el0=56, d1=3.0, el1=40, az0=-0.12):
    tgt = Vector((0, 0, 0.1))
    d, el, az, lens = d0, math.radians(el0), az0 + 0.0018 * f, 40.0
    t = ease_io(seg(f, push_from, n), 2)
    if t > 0:
        tgt = tgt.lerp(Vector(tgt_end), t)
        d, el, lens = lerp(d, d1, t), lerp(el, math.radians(el1), t), lerp(40, 52, t)
    return orbit(tgt, d, el, az), tgt, lens


# --------------------------------------------------------- plated dish -----
NEST_TOP = 0.5
NEST_R = 0.6
CAP_R, CAP_H = 0.46, 0.065


def plated(S, prefix, parm_static=True):
    """Spaghetti nest on a plate, topped with ragu, meat and basil.
    Everything is parented to the returned root empty."""
    root = bpy.data.objects.new(f"{prefix}_dish", None)
    S.coll.objects.link(root)
    root.scale = (DISH_SCALE,) * 3
    pl = MD.plate(f"{prefix}_plate", S.coll)
    pl.parent = root
    rng = np.random.default_rng(11)
    mat, P = M.pasta(f"{prefix}_pasta")
    P["cook"].outputs[0].default_value = 1.0
    P["sauce"].outputs[0].default_value = 0.34
    nest = MD.pasta_object(f"{prefix}_nest", S.coll, MD.nest_strands(rng, top=NEST_TOP, Rm=NEST_R), mat,
                           fx.pasta_static_group())
    nest.parent = root
    nest.location.z = MD.PLATE_TOP
    base = lambda r: MD.mound_z(r, NEST_TOP, NEST_R)
    cap = MD.sauce_cap(f"{prefix}_ragu", S.coll, CAP_R, CAP_H, base, mat=M.ragu())
    cap.parent = root
    cap.location.z = MD.PLATE_TOP
    mm, mp = M.mince(f"{prefix}_meat")
    mp["brown"].outputs[0].default_value = 1.0
    mp["sauce"].outputs[0].default_value = 0.7
    meat = S.proto("meat", "mince", mm)
    N = 650
    pts = []
    for _ in range(N):
        r = CAP_R * 0.95 * math.sqrt(rng.uniform(0, 1))
        a = rng.uniform(0, TAU)
        z = MD.PLATE_TOP + base(r) + 0.012 + CAP_H * max(0.0, 1 - (r / CAP_R) ** 2) ** 0.6 + 0.004
        pts.append((r * math.cos(a), r * math.sin(a), z))
    S.static_points(f"{prefix}_meat", meat, np.array(pts), rng.uniform(0.016, 0.028, N), sv=flat_sv(rng, N, (0.55, 0.8)),
                    parent=root)
    leaves = []
    for i, (x, y, rz, s) in enumerate([(0.03, 0.04, 0.6, 1.0), (-0.09, -0.05, 2.7, 0.8)]):
        lf = MD.basil_leaf(f"{prefix}_basil{i}", S.coll, 0.34 * s, seed=i + 3)
        lf.parent = root
        lf.location = (x, y, MD.PLATE_TOP + NEST_TOP + CAP_H + 0.05)
        lf.rotation_euler = (0.12, -0.18, rz)
        leaves.append(lf)
    if parm_static:
        pts = []
        for _ in range(170):
            r = 0.55 * math.sqrt(rng.uniform(0, 1))
            a = rng.uniform(0, TAU)
            z = MD.PLATE_TOP + base(r) + 0.025 + (CAP_H * max(0.0, 1 - (r / CAP_R) ** 2) ** 0.6 if r < CAP_R else 0)
            pts.append((r * math.cos(a), r * math.sin(a), z))
        S.static_points(f"{prefix}_parm", "parm", np.array(pts), rng.uniform(0.008, 0.016, len(pts)),
                        sv=np.stack([np.ones(len(pts)), rng.uniform(0.5, 1, len(pts)), np.ones(len(pts))], 1),
                        parent=root)
    return root, dict(leaves=leaves)


def dish_bvh():
    """Envelope of nest + ragu cap (root-local) for parmesan landings."""
    from mathutils.bvhtree import BVHTree
    base = lambda r: MD.mound_z(r, NEST_TOP, NEST_R)
    prof = [(r, MD.PLATE_TOP + base(r) + 0.03 + (CAP_H * max(0.0, 1 - (r / CAP_R) ** 2) ** 0.6 if r < CAP_R else 0))
            for r in np.linspace(0, NEST_R, 31)]
    me = MD.revolve_mesh("_dish_env", prof, 48, closed=False)
    b = fx.bvh_from_mesh(me)
    bpy.data.meshes.remove(me)
    return b


# ============================================================ S1 INTRO =====
def shot_intro(name, n):
    S = Shot(name, n, M.backdrop_world("W_intro", center=(0.5, 0.5), radius=0.85), fstop=4.0)
    MD.floor("S1_floor", S.coll, z=0.0)
    root, parts = plated(S, "S1")
    U.animate(root, S.frames(), lambda f: dict(rot=(0, 0, -0.7 + 0.013 * f)))
    S.ambient("herbs", "herb", 36, box=((-2.2, 2.2), (-1.0, 3.0), (-0.2, 3.0)), s=(0.008, 0.016))
    S.ambient("parm", "parm", 30, box=((-2.2, 2.2), (-1.0, 3.0), (-0.2, 3.0)), s=(0.01, 0.02))
    top = Vector((0, 0, (MD.PLATE_TOP + NEST_TOP + CAP_H) * DISH_SCALE))

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
    elif key == "mince":
        k = 0.42
        add(MD.dish("S2_mince_dish", S.coll), (0, 0, -0.06), scl=k)
        N = 520
        r = 0.6 * np.sqrt(rng.uniform(0, 1, N))
        th = rng.uniform(0, TAU, N)
        h = 0.06 + 0.3 * np.clip(1 - (r / 0.62) ** 2, 0, 1) ** 0.8 * rng.uniform(0.7, 1.0, N) ** 0.4
        pts = np.stack([r * np.cos(th), r * np.sin(th), h], 1) * k + np.array([0, 0, -0.06])
        S.static_points("S2_mince", "mince", pts, rng.uniform(0.032, 0.05, N) * k, sv=flat_sv(rng, N, (0.6, 0.9)),
                        parent=e)
        base_rot = (0.95, 0, 0)
    elif key == "onion":
        add(MD.onion("S2_onion", S.coll), (0, 0, -0.26), scl=0.75)
        base_rot = (0.3, 0, 0.5)
    elif key == "carrot":
        add(MD.carrot("S2_carrot", S.coll), (0, 0, -0.33), scl=0.64)
        base_rot = (0.35, 0.85, 0.3)
    elif key == "celery":
        add(MD.celery("S2_celery", S.coll), (-0.36, 0, -0.02), scl=0.66)
        base_rot = (0.7, -0.45, 0.25)
    elif key == "garlic":
        add(MD.garlic_bulb("S2_garlic", S.coll), (0, 0, -0.25), scl=0.85)
        base_rot = (0.35, 0, 0)
    elif key == "wine":
        add(MD.wine_bottle("S2_wine", S.coll), (0, 0, -0.3), scl=0.6)
        base_rot = (0.12, 0, 0.3)
    elif key == "tomato":
        add(MD.dish("S2_tomdish", S.coll), (0, 0, -0.06), scl=0.4)
        add(MD.sauce_surface("S2_tom", S.coll, 0.77, MD.DISH_LIQ_Z, amp=0.02), (0, 0, -0.06 + MD.DISH_LIQ_Z * 0.4),
            scl=0.4)
        base_rot = (0.95, 0, 0)
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
        hero = key == "mince"

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


# ======================================================== S3 SOFFRITTO ======
def shot_soffritto(name, n):
    S = Shot(name, n, M.backdrop_world("W_soff", center=(0.5, 0.62), inner=(0.07, 0.042, 0.024), radius=0.9),
             fstop=5.6, lens=40)
    rng = S.rng
    pan_scene(S)
    MD.oil_film("S3_oil", S.coll, MD.pan_inner_r(FLOOR + 0.005), FLOOR)
    stir = stir_empty(S, 50, 92, 2.2)
    vp = veg_protos(S)
    labels = {"onion": ("ONION", "left"), "carrot": ("CARROT", "right"), "celery": ("CELERY", "right")}
    for key, base, cols, t0, N, sz, ctr in VEG:
        proto, p = vp[key]
        s = rng.uniform(*sz, N)
        tg = sector(rng, N, ctr, 0.42 if key != "garlic" else 0.3, FLOOR + 0.012)
        tg[:, 2] = FLOOR + s * 0.45 + rng.uniform(0, 0.012, N)
        p0, v0, land = aimed(rng, N, (ctr[0] * 0.4 - 0.2, ctr[1] * 0.4 + 0.3, 1.9), 0.09, tg)
        e = t0 + rng.uniform(0, 5, N)
        S.ballistic(key, proto, p0, v0, e, land, np.full(N, 1e5), 1.0, s, parent=stir, spin=0.5,
                    sv=(1, 1, 1) if key != "garlic" else (1, 1, 0.35))
        S.cue(t0 + 10, "splat")
        if key in labels:
            txt, side = labels[key]
            S.track(f"veg_{key}", lambda f, c=ctr: Vector((c[0], c[1], FLOOR + 0.03)))
            S.ov(type="label", text=txt, track=f"veg_{key}", t0=t0 + 12, t1=50, side=side)
        for f in S.frames():
            U.key_socket(p["cook"].outputs[0], f, smooth(seg(f, 44, 100)))
    stir_spoon(S, 44, 52, 90, 100)
    pts = disc_points(rng, 300, 0.05, 0.85, FLOOR + 0.003)
    foam = S.looping("foam", "oil_bubble", pts, np.zeros_like(pts), rng.uniform(5, 12, 300), rng.uniform(0, 20, 300),
                     rng.uniform(0.006, 0.013, 300), pop=1.0, density=0.0)
    key_density(foam, S.frames(), lambda f: 0.7 * smooth(seg(f, 14, 26)))
    cam0 = orbit((0, 0, 0.1), 5.3, math.radians(56), -0.1)
    st = S.steam("steam", (0, 0), 0.65, (0.25, 0.55), 18, cam0)
    key_density(st, S.frames(), lambda f: 0.8 * smooth(seg(f, 40, 60)))
    S.cue(9, "sizzle_start")
    S.cue(52, "stir", dur=1.3)
    S.camera_path(lambda f: pan_cam(f, n, 80, (-0.1, -0.15, 0.08)))
    ST.studio_rig(S.sc, (0, 0, 0.1), k=0.26, rim=0.5, top=0.6)
    S.header("soffritto", 3, 98)
    S.ov(type="haze", t0=12, t1=n, y0=0.0, y1=0.45, amp=1.6)
    S.track("soft", lambda f: Vector((0.25, -0.32, FLOOR + 0.03)))
    S.ov(type="callout", text="SWEAT UNTIL SOFT", track="soft", t0=84, t1=n, dx=-150, dy=-330)
    return S


# ============================================================ S4 RAGU ======
def shot_ragu(name, n):
    S = Shot(name, n, M.backdrop_world("W_ragu", center=(0.5, 0.62), inner=(0.07, 0.04, 0.022), radius=0.9),
             fstop=5.6, lens=40)
    rng = S.rng
    pan_scene(S)
    MD.oil_film("S4_oil", S.coll, MD.pan_inner_r(FLOOR + 0.005), FLOOR)
    stir = stir_empty(S, 26, 66, 1.8)
    vp = veg_protos(S, cook=1.0)
    for key, base, cols, t0, N, sz, ctr in VEG:
        pts = sector(rng, int(N * 0.8), (0, 0), 0.82, 0.0)
        s = rng.uniform(*sz, len(pts))
        pts[:, 2] = FLOOR + s * 0.45
        S.static_points(f"soff_{key}", vp[key][0], pts, s, parent=stir,
                        sv=(1, 1, 1) if key != "garlic" else (1, 1, 0.35))
    # ---- 02 BROWN: mince drops in, breaks up and browns ------------------
    mm, MP = M.mince("S4_mince")
    mince = S.proto("mince", "mince", mm)
    N = 2300
    s = rng.uniform(0.015, 0.03, N)
    tg = sector(rng, N, (0, 0), 0.8, 0.0)
    tg[:, 2] = FLOOR + 0.025 + s * 0.5 + rng.uniform(0, 0.02, N)
    p0, v0, land = aimed(rng, N, (0.15, 0.1, 1.7), 0.07, tg, frames=(8, 12))
    S.ballistic("mince", mince, p0, v0, 8 + rng.uniform(0, 3, N), land, np.full(N, 1e5), 1.0, s,
                sv=flat_sv(rng, N, (0.5, 0.75)), parent=stir, spin=0.6)
    for f in S.frames():
        U.key_socket(MP["brown"].outputs[0], f, smooth(seg(f, 22, 66)))
    # some soffritto stays visible on top of the meat once it is stirred in
    for key, base, cols, t0, Nv, sz, ctr in VEG[:3]:
        pts = sector(rng, Nv // 3, (0, 0), 0.75, 0.0)
        sv_ = rng.uniform(*sz, len(pts))
        pts[:, 2] = FLOOR + 0.05 + sv_ * 0.4
        o = S.static_points(f"soff_top_{key}", vp[key][0], pts, sv_, parent=stir)
        hide_range(o, S.frames(), lambda f: f >= 34)
    stir_spoon(S, 20, 28, 64, 72, a0=-0.4, turns=0.38)
    S.cue(8, "whoosh", dur=0.3)
    S.cue(18, "splat")
    S.cue(10, "sizzle_start")
    S.cue(28, "stir", dur=1.2)
    S.header("brown", 3, 68)
    # ---- 03 SIMMER: wine, then tomatoes --------------------------------------
    T_W0, T_W1 = 72, 86
    hit_w = Vector((0.2, 0.05, FLOOR + 0.05))
    top_w = Vector((0.85, 0.5, 2.6))
    pts = []
    for i in range(32):
        t = i / 31
        p = top_w.lerp(hit_w, t)
        p.z = lerp(top_w.z, hit_w.z, t ** 1.6)
        pts.append(tuple(p))
    wine = MD.stream("S4_wine", S.coll, pts, 0.03, M.red_wine(), taper=(1.0, 0.8))
    for f in S.frames():
        U.key_prop(wine.data, "bevel_factor_end", f, ease_in(seg(f, T_W0, T_W0 + 4), 1.5))
        U.key_prop(wine.data, "bevel_factor_start", f, ease_in(seg(f, T_W1 - 2, T_W1 + 3), 1.5))
    hide_range(wine, S.frames(), lambda f: T_W0 <= f <= T_W1 + 3)
    p0, v0 = burst(rng, 40, tuple(hit_w), 0.03, (0, 0, 1.4), 0.5)
    landw = fx.landing(p0, v0, 30.0, floor_z=FLOOR + 0.03, max_frames=40)
    S.ballistic("wine_splash", "drop", p0, v0, T_W0 + 4 + rng.uniform(0, 4, 40), landw, landw, 1.0,
                rng.uniform(0.008, 0.016, 40))
    cam0 = orbit((0, 0, 0.1), 5.3, math.radians(56), -0.1)
    puff = S.steam("deglaze", (0, 0), 0.6, (0.2, 0.5), 26, cam0, s=(0.35, 0.6), rise=(0.012, 0.02))
    key_density(puff, S.frames(), lambda f: smooth(seg(f, T_W0 + 2, T_W0 + 8)) * (1 - 0.6 * smooth(seg(f, 92, 110))))
    S.cue(T_W0, "pour", dur=(T_W1 - T_W0) / C.FPS)
    S.cue(T_W0 + 3, "hiss", dur=1.4)
    S.header("simmer", 72, 128)
    T_IN, T_TILT, T_POUR, T_END, T_OUT = 86, 94, 98, 116, 120
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
    lip = home + Euler((0, 1.2, 0)).to_matrix() @ (Vector((0.86, 0, 0.25)) * BS)
    hit = Vector((0.05, 0.12, Z_SAUCE))
    pts = []
    vx, vy = (hit.x - lip.x) / 0.32, (hit.y - lip.y) / 0.32
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
    mm2, MP2 = M.mince("S4_meat_sauced")
    MP2["brown"].outputs[0].default_value = 1.0
    MP2["sauce"].outputs[0].default_value = 0.65
    sauce, R_S = ragu_surface(S, S.proto("meat", "mince", mm2))

    def lvl(f):
        return lerp(MD.PAN_FLOOR - 0.03, Z_SAUCE, smooth(seg(f, T_POUR + 3, T_END + 6)))
    U.animate(sauce, S.frames(), lambda f: dict(
        loc=(0, 0, lvl(f)), scl=((MD.pan_inner_r(max(lvl(f), MD.PAN_FLOOR)) - 0.004) / R_S,) * 2 + (1.0,)))
    fx.set_inputs(sauce, sauce.modifiers["Ripple"], {"RingStart": float(T_POUR + 4), "RingAmp": 0.012,
                                                     "RingCenter": (hit.x, hit.y, 0.0)})
    p0, v0 = burst(rng, 40, (hit.x, hit.y, Z_SAUCE + 0.02), 0.04, (0, 0, 1.5), 0.6)
    land = fx.landing(p0, v0, 30.0, floor_z=Z_SAUCE, max_frames=40)
    S.ballistic("splash", "drop", p0, v0, T_POUR + 4 + rng.uniform(0, 3, 40), land, land, 1.0,
                rng.uniform(0.01, 0.02, 40))
    S.cue(T_POUR + 4, "splash", size=0.6)
    pts = disc_points(rng, 45, 0.1, 0.85, Z_SAUCE + 0.004)
    blub = S.looping("blub", "blub", pts, np.zeros_like(pts), rng.uniform(16, 30, 45), rng.uniform(0, 30, 45),
                     rng.uniform(0.02, 0.04, 45), sv=(1, 1, 0.7), pop=1.0, density=0.0)
    key_density(blub, S.frames(), lambda f: 0.8 * smooth(seg(f, 116, 126)))
    S.cue(116, "simmer", dur=(n - 116) / C.FPS)
    S.camera_path(lambda f: pan_cam(f, n, 112, (-0.15, -0.2, Z_SAUCE)))
    ST.studio_rig(S.sc, (0, 0, 0.1), k=0.26, rim=0.5, top=0.6)
    S.ov(type="haze", t0=12, t1=70, y0=0.0, y1=0.45, amp=1.6)
    S.track("ragu", lambda f: Vector((-0.35, -0.42, Z_SAUCE)))
    S.ov(type="callout", text="SLOW SIMMERED", track="ragu", t0=118, t1=n, dx=-120, dy=330)
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
    T_DROP, T_HIT = 8, 15
    fx.set_inputs(water, water.modifiers["Ripple"], {"RingStart": float(T_HIT), "RingAmp": 0.02,
                                                     "RingCenter": (0, 0, WZ)})
    pts = disc_points(rng, 160, 0.0, R - 0.06, WZ + 0.002)
    S.looping("pops", "bubble", pts, np.zeros_like(pts), rng.uniform(6, 16, 160), rng.uniform(0, 20, 160),
              rng.uniform(0.012, 0.03, 160), sv=(1, 1, 0.6), pop=1.0)
    N = 110
    per = rng.uniform(10, 24, N)
    pts = disc_points(rng, N, 0.0, R - 0.08, MD.POT_FLOOR + 0.02)
    vel = np.zeros((N, 3))
    vel[:, 2] = (WZ - MD.POT_FLOOR - 0.03) / per
    S.looping("rise", "bubble", pts, vel, per, rng.uniform(0, 24, N), rng.uniform(0.006, 0.014, N), wob=0.01, wf=0.3)
    cam0 = orbit((0, 0, 0.6), 5.4, math.radians(48), -0.1)
    st = S.steam("steam", (0, 0), 0.7, (WZ + 0.15, WZ + 0.45), 24, cam0, s=(0.35, 0.55))
    key_density(st, S.frames(), lambda f: 1.0)
    S.cue(1, "boil", dur=n / C.FPS)
    p0, v0 = burst(rng, 60, (0.15, -0.1, 1.7), 0.05, (0, 0, -0.6), 0.25)
    land = fx.landing(p0, v0, 30.0, floor_z=WZ, max_frames=40)
    S.ballistic("salt", "salt", p0, v0, 2 + rng.uniform(0, 4, 60), land, land, 1.0, rng.uniform(0.005, 0.009, 60))
    S.cue(4, "sprinkle", dur=0.4)
    strands, at = MD.dry_bundle_strands(rng, n=110, L=2.2, br=0.075)
    mat, P = M.pasta("S5_pasta")
    pasta = MD.pasta_object("S5_pasta", S.coll, strands, mat, fx.pasta_dry_group(),
                            {"BaseZ": MD.POT_FLOOR + 0.01, "Zmin": MD.POT_FLOOR + 0.012, "Rmax": R - 0.03,
                             "Swirl": 0.7}, strand_attrs=at, radius=0.0088)
    for f in S.frames():
        fx.key_input(pasta, "Pasta", "Drop", f, 2.4 * (1 - ease_in(seg(f, T_DROP, T_HIT), 2.0)))
        fx.key_input(pasta, "Pasta", "Fan", f, ease_out(seg(f, T_HIT, T_HIT + 11), 2.5))
        fx.key_input(pasta, "Pasta", "Soft", f, ease_io(seg(f, 32, 84), 1.6))
        U.key_socket(P["cook"].outputs[0], f, smooth(seg(f, 32, 80)))
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
        t = ease_io(seg(f, 64, n), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0, 0, WZ)), t)
            d, el, lens = lerp(d, 3.4, t), lerp(el, math.radians(60), t), lerp(40, 48, t)
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.5), k=0.45, rim=0.7, top=0.9)
    S.header("boil", 3, 84)
    S.track("pasta", lambda f: Vector((0.3, -0.35, WZ)))
    S.ov(type="callout", text="AL DENTE", track="pasta", t0=70, t1=n, dx=160, dy=-320)
    return S


# ============================================================ S6 TOSS ======
def shot_toss(name, n):
    S = Shot(name, n, M.backdrop_world("W_toss", center=(0.5, 0.62), inner=(0.07, 0.042, 0.024), radius=0.9),
             fstop=5.6, lens=40)
    rng = S.rng
    pan_scene(S)
    mm, MP = M.mince("S6_meat")
    MP["brown"].outputs[0].default_value = 1.0
    MP["sauce"].outputs[0].default_value = 0.65
    meat = S.proto("meat", "mince", mm)
    ragu_surface(S, meat)
    pts = disc_points(rng, 40, 0.1, 0.9, Z_SAUCE + 0.004)
    S.looping("blub", "blub", pts, np.zeros_like(pts), rng.uniform(16, 32, 40), rng.uniform(0, 30, 40),
              rng.uniform(0.02, 0.04, 40), sv=(1, 1, 0.7), pop=1.0, density=0.5)
    S.cue(1, "simmer", dur=n / C.FPS)
    T_FALL, T_TOSS = 4, 46
    strands = MD.pile_strands(rng, n=230, Rp=0.72, h=0.27, z0=Z_SAUCE - 0.035)
    nS = len(strands)
    at = dict(e=rng.uniform(0, 1.5, nS), ta=rng.uniform(0.6, 1.25, nS), td=rng.uniform(0, 5, nS))
    pm, PP = M.pasta("S6_pasta")
    PP["cook"].outputs[0].default_value = 1.0
    MD.pasta_object("S6_pasta", S.coll, strands, pm, fx.pasta_pile_group(),
                    {"FallStart": float(T_FALL), "FallDur": 8.0, "Height": 1.5, "TossStart": float(T_TOSS),
                     "TossDur": 14.0, "TossAmp": 0.5}, strand_attrs=at, radius=0.0105)
    for f in S.frames():
        U.key_socket(PP["sauce"].outputs[0], f, 0.44 * smooth(seg(f, 14, 40)) + 0.12 * smooth(seg(f, T_TOSS, 70)))
    T_LAND = T_FALL + 8
    S.cue(T_FALL, "whoosh", dur=0.35)
    S.cue(T_LAND, "splat")
    S.cue(T_TOSS, "whoosh", dur=0.4, up=True)
    S.cue(T_TOSS + 14, "splat")
    # meaty ragu spooned over the pasta as it settles after the toss
    N = 260
    tg = []
    for _ in range(N):
        r = 0.6 * math.sqrt(rng.uniform(0, 1))
        a = rng.uniform(0, TAU)
        tg.append((r * math.cos(a), r * math.sin(a), Z_SAUCE - 0.035 + MD.pile_z(r, 0.72, 0.27) + 0.03))
    tg = np.array(tg)
    p0, v0, land = aimed(rng, N, (0.0, 0.0, Z_SAUCE + 0.35), 0.12, tg, frames=(7, 11))
    S.ballistic("meat_top", meat, p0, v0, T_TOSS + 2 + rng.uniform(0, 6, N), land, np.full(N, 1e5), 1.0,
                rng.uniform(0.018, 0.03, N), sv=flat_sv(rng, N, (0.55, 0.8)), spin=0.5)
    for t0, Nd in ((T_LAND, 40), (T_TOSS + 2, 50), (T_TOSS + 14, 35)):
        p0 = disc_points(rng, Nd, 0.1, 0.7, Z_SAUCE + 0.05)
        th = np.arctan2(p0[:, 1], p0[:, 0])
        v0 = np.stack([0.5 * np.cos(th), 0.5 * np.sin(th), rng.uniform(1.0, 2.4, Nd)], 1)
        land = fx.landing(p0, v0, 30.0, floor_z=Z_SAUCE, max_frames=40)
        S.ballistic(f"drops{t0}", "drop", p0, v0, t0 + rng.uniform(0, 3, Nd), land, land, 1.0,
                    rng.uniform(0.008, 0.018, Nd))
    cam0 = orbit((0, 0, 0.15), 5.2, math.radians(45), -0.1)
    st = S.steam("steam", (0, 0), 0.7, (0.3, 0.6), 20, cam0)
    key_density(st, S.frames(), lambda f: 0.85)

    def cam(f):
        tgt = Vector((0, 0, 0.16))
        d, el, az, lens = 5.2, math.radians(46), -0.2 + 0.002 * f, 40.0
        sh = 0.02 * math.sin(f * 1.9) * seg(f, T_TOSS - 1, T_TOSS + 2) * (1 - seg(f, T_TOSS + 6, T_TOSS + 12))
        tgt = tgt + Vector((sh, 0, sh))
        t = ease_io(seg(f, 66, n), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0.1, -0.15, Z_SAUCE + 0.12)), t)
            d, el, lens = lerp(d, 3.1, t), lerp(el, math.radians(34), t), lerp(40, 52, t)
        return orbit(tgt, d, el, az), tgt, lens
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.15), k=0.26, rim=0.5, top=0.6)
    S.header("toss", 3, 84)
    S.track("pasta", lambda f: Vector((0.25, -0.35, Z_SAUCE + 0.16)))
    S.ov(type="callout", text="COATED IN RAGÙ", track="pasta", t0=70, t1=n, dx=-170, dy=-330)
    return S


# =========================================================== S7 FINAL ======
def shot_final(name, n):
    S = Shot(name, n, M.backdrop_world("W_final", center=(0.5, 0.58), inner=(0.11, 0.06, 0.03), radius=0.85),
             fstop=4.0, lens=50)
    rng = S.rng
    MD.floor("S7_floor", S.coll, z=0.0)
    root, parts = plated(S, "S7", parm_static=False)
    U.animate(root, S.frames(), lambda f: dict(rot=(0, 0, 0.2 + 0.008 * f)))
    for i, lf in enumerate(parts["leaves"]):
        rest = Vector(lf.location)
        r0 = Euler(lf.rotation_euler)
        t0 = 12 + 5 * i

        def fn(f, rest=rest, r0=r0, t0=t0):
            u = seg(f, t0, t0 + 10)
            z = rest.z + 1.4 * (1 - ease_in(u, 2))
            if f > t0 + 10:
                z += 0.02 * impact((f - t0 - 10) / C.FPS, 3.0, 8.0)
            return dict(loc=(rest.x, rest.y, z), rot=(r0.x + 0.6 * (1 - u), r0.y, r0.z + 1.5 * (1 - u)))
        U.animate(lf, S.frames(), fn)
        hide_range(lf, S.frames(), lambda f, t0=t0: f >= t0)
        S.cue(t0 + 10, "pop", pitch=0.8 + 0.1 * i)
    N = 380
    p0 = np.stack([rng.uniform(-0.5, 0.5, N), rng.uniform(-0.5, 0.5, N), rng.uniform(2.4, 3.2, N)], 1)
    v0 = np.stack([rng.normal(0, 0.08, N), rng.normal(0, 0.08, N), rng.uniform(-0.6, -0.2, N)], 1)
    land = fx.landing(p0, v0, 6.0, drag=1.5, bvh=dish_bvh(), floor_z=MD.PLATE_TOP, max_frames=80)
    S.ballistic("parm", "parm", p0, v0, 30 + rng.uniform(0, 24, N), land, np.full(N, 1e5), 1.0,
                rng.uniform(0.008, 0.016, N), gravity=6.0, drag=1.5, parent=root, spin=0.6,
                sv=np.stack([np.ones(N), rng.uniform(0.5, 1, N), np.ones(N)], 1))
    S.cue(32, "sprinkle", dur=1.0)
    cam_el = lambda f: math.radians(lerp(20, 24, ease_io(seg(f, 1, n))))
    cam_d = lambda f: lerp(6.9, 6.4, ease_io(seg(f, 1, n)))
    tgt = Vector((0, 0, 0.82))

    def cam(f):
        return orbit(tgt, cam_d(f), cam_el(f), 0.0), tgt, 50.0
    lines = [(C.FINAL_TEXT[0], 0.105, "cream", 2.17, 1.2),
             (C.FINAL_TEXT[1], 0.15, "gold", 1.93, 1.1),
             (C.FINAL_TEXT[2], 0.30, "cream", 1.58, 1.0)]
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
    sw = ST.area(S.sc, "S7_sweep", (-2.5, 1.2, 1.6), (0, 0, 0.6), 0, (0.25, 3.0), (1.0, 0.85, 0.6))
    for f in S.frames():
        t = seg(f, 36, 90)
        sw.location = (lerp(-2.6, 2.6, ease_io(t)), 1.4, 1.6)
        sw.keyframe_insert("location", frame=f)
        U.key_prop(sw.data, "energy", f, 700 * math.sin(math.pi * t))
    st = S.steam("steam", (0, 0), 0.4, (0.6, 0.85), 14, cam(60)[0], s=(0.3, 0.45))
    key_density(st, S.frames(), lambda f: 0.8)
    S.ambient("herbs_bg", "herb", 36, box=((-2.0, 2.0), (0.6, 3.0), (-0.2, 3.0)), s=(0.008, 0.015))
    S.ambient("parm_bg", "parm", 26, box=((-2.0, 2.0), (0.6, 3.0), (-0.2, 3.0)), s=(0.01, 0.02))
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0, 0.4), k=0.42, rim=0.8, top=0.7)
    S.cue(1, "boom")
    S.cue(1, "simmer", dur=n / C.FPS, level=0.5)
    S.ov(type="sparkle", t0=40, t1=n)
    return S


BUILDERS = {
    "S1_intro": shot_intro,
    "S2_ingredients": shot_ingredients,
    "S3_soffritto": shot_soffritto,
    "S4_ragu": shot_ragu,
    "S5_boil": shot_boil,
    "S6_toss": shot_toss,
    "S7_final": shot_final,
}
