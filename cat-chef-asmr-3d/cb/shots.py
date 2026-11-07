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
from mathutils import Vector, Euler, Quaternion, Matrix
import bmesh

import config as C
from . import util as U, materials as M, models as MD, stage as ST, fx, cat as CT
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

    def cue(self, f, kind, pos=None, **kw):
        """Sound cue at shot frame f.  pos (world point) pans it to where the
        event is on screen; kw 'items' = [(frame, pos), ...] for grain clouds."""
        d = dict(f=float(f), kind=kind, **kw)
        if pos is not None:
            d["pos"] = tuple(pos)
        self.cues.append(d)

    def _pan(self, f, pos):
        fi = int(min(max(round(f), 1), self.n))
        pr = self.ct.project(fi, pos)
        if pr is None:
            return 0.0
        return max(-0.9, min(0.9, (pr[0] / C.RES_X - 0.5) * 1.5))

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
        for c in self.cues:
            if "pos" in c:
                c["pan"] = self._pan(c["f"], c.pop("pos"))
            if "items" in c:
                c["items"] = [(float(fi), self._pan(fi, p)) for fi, p in c["items"] if fi <= self.n]
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
                pop=0.0, density=1.0, parent=None, dens=None):
        n = len(p0)
        rng = self.rng
        attrs = dict(p0=p0, vel=vel, per=per, ph=ph, s=s,
                     sv=np.ones((n, 3)) if sv is None else np.broadcast_to(np.asarray(sv, float), (n, 3)),
                     rot=rng.uniform(0, TAU, (n, 3)) if rot is None else rot,
                     spin=rng.normal(0, spin, (n, 3)) if np.isscalar(spin) else spin,
                     wob=np.full(n, wob) if np.isscalar(wob) else wob,
                     wf=np.full(n, wf) if np.isscalar(wf) else wf,
                     dens=rng.uniform(0, 1, n) if dens is None else dens)
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




# ============================================================ CAT CHEF =====
CAT_K = 1.1
PALM_CAM = (-math.pi / 2, 0.0, 0.0)          # palm to camera, fingers up
PALM_UP = (math.pi, 0.0, 0.0)


def cat_head_pos(home, yaw=0.0, K=CAT_K):
    off = Matrix.Rotation(yaw, 3, "Z") @ Vector((0, -0.25 * K, (CT.NECK_Z + 0.5 * CT.HEAD_S) * K))
    return Vector(home) + off


def face_to(home, target, amt=0.5, base=(0.0, 0.0, 0.0), yaw=0.0, K=CAT_K):
    """Head Euler (nod, tilt, turn) that turns the face part-way to a target."""
    d = Vector(target) - cat_head_pos(home, yaw, K)
    turn = (math.atan2(d.x, -d.y) - yaw + math.pi) % TAU - math.pi
    nod = math.atan2(-d.z, math.hypot(d.x, d.y))
    return (base[0] + amt * nod, base[1], base[2] + amt * max(-1.0, min(1.0, turn)))


def idle(f, ph=0.0, k=1.0):
    return dict(bob=0.012 * k * math.sin(f * 0.17 + ph), sway=0.03 * k * math.sin(f * 0.06 + ph), tail=f * 0.13 + ph)


def wob(f, ph=0.0, k=1.0):
    return (0.03 * k * math.sin(f * 0.08 + ph), 0.05 * k * math.sin(f * 0.055 + ph + 1.0), 0.0)


def addv(*vs):
    return tuple(sum(c) for c in zip(*vs))


def path(keys, f):
    """Smooth piecewise interpolation through (frame, vector) keys (holds at ends)."""
    if f <= keys[0][0]:
        return Vector(keys[0][1])
    for (f0, a), (f1, b) in zip(keys[:-1], keys[1:]):
        if f <= f1:
            return Vector(a).lerp(Vector(b), ease_io(seg(f, f0, f1), 2))
    return Vector(keys[-1][1])


def grip(d):
    """Paw Euler with the paw's up axis along d (gripping a handle)."""
    return tuple(Vector(d).normalized().to_track_quat("Z", "Y").to_euler())


B = CT.bump
BL = CT.blinks


# ============================================================ S1 INTRO =====
def shot_intro(name, n):
    S = Shot(name, n, M.backdrop_world("W_intro", center=(0.5, 0.42), radius=0.95), fstop=5.6)
    MD.floor("S1_floor", S.coll, z=0.0)
    srv, wedges, _ = served(S, "S1")
    U.animate(srv, S.frames(), lambda f: dict(rot=(0, 0, -0.3 + 0.008 * f)))
    home = Vector((0, 1.85, 0.0))
    cat = CT.Cat(S, "cat", K=CAT_K, home=home)
    BT = MD.ROUND_BOARD_TOP * PIZZA_SCALE + 0.13
    dive = Vector((0.12, -0.3, SERVE_TOP))
    S.ambient("herbs", "herb", 36, box=((-2.6, 2.6), (-1.0, 3.5), (-0.2, 4.0)), s=(0.008, 0.016))
    S.ambient("cheese", "parm", 26, box=((-2.6, 2.6), (-1.0, 3.5), (-0.2, 4.0)), s=(0.01, 0.02))
    st = S.steam("steam", (0, 0), 0.7, (0.35, 0.7), 14, orbit((0, 0.5, 1.3), 9.0, math.radians(22), 0.0),
                 s=(0.3, 0.45))
    key_density(st, S.frames(), lambda f: 0.6)

    def cam(f):
        t = ease_io(seg(f, 1, 48), 2)
        d = lerp(10.2, 8.8, t)
        el = math.radians(lerp(19, 24, t))
        az = lerp(-0.22, 0.05, t)
        tgt = Vector((0, 0.55, lerp(1.4, 1.3, t)))
        t2 = ease_in(seg(f, 48, 60), 2.4)
        if t2 > 0:
            d = lerp(d, 0.9, t2)
            tgt = tgt.lerp(dive, t2)
            el = lerp(el, math.radians(55), t2)
        return orbit(tgt, d, el, az), tgt, 40.0
    S.camera_path(cam)
    rest = {"L": (-0.95, 0.55, BT), "R": (0.95, 0.55, BT)}
    tada = {"L": (-1.55, 1.0, 1.45), "R": (1.55, 1.0, 1.45)}

    def pose(f):
        p = idle(f)
        look = cam(f)[0] if f < 48 else dive
        p["look"] = look
        hd = face_to(home, look, 0.3)
        nod = 0.2 * B(f, 8, 11, 12, 15)
        tilt = 0.25 * B(f, 16, 19, 23, 27)
        p["head"] = addv(hd, wob(f), (nod, tilt, 0.0))
        p["blink"] = max(BL(f, (4, 52)), 0.75 * B(f, 16, 18, 23, 25))
        p["open"] = 0.3 * B(f, 26, 29, 35, 38) + 0.85 * B(f, 39, 41, 45, 48)
        p["ears"] = B(f, 38, 40, 46, 50)
        for side, s in (("L", -1), ("R", 1)):
            r, t = Vector(rest[side]), Vector(tada[side])
            keys = [(1, r), (25, r), (31, t), (36, t), (42, r if side == "L" else Vector((1.3, 1.0, 2.05))),
                    (47, r if side == "L" else Vector((1.35, 1.0, 1.95))), (54, r)]
            pos = path(keys, f)
            if side == "R" and 41 <= f <= 48:
                pos = pos + Vector((0.12 * math.sin((f - 41) * 1.1), 0, 0))
            up = B(f, 25, 31, 36, 42) if side == "L" else B(f, 25, 31, 48, 54)
            rot = Vector((0, 0, 0)).lerp(Vector(PALM_CAM), up)
            p[side] = (pos, tuple(rot))
        return p
    cat.animate(S.frames(), pose)
    ST.studio_rig(S.sc, (0, 0.6, 0.9), k=0.42, rim=0.8, top=0.7)
    S.ov(type="fade_in", t0=1, t1=10)
    S.ov(type="kinetic", words=list(C.INTRO_WORDS), times=[8, 17, 26], t1=45)
    S.ov(type="subtitle", text="LET'S COOK", t0=38, t1=57)
    S.cue(1, "swell")
    for f in (8, 17, 26):
        S.cue(f, "tick")
    S.cue(39, "meow", pitch=1.0)
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
    S = Shot(name, n, M.backdrop_world("W_ingr", center=(0.5, 0.45), radius=0.95), fstop=11.0)
    rows = [1.75, 0.60, -0.55]
    cols = [-1.02, 0.0, 1.02]
    cam_d = lambda f: lerp(11.2, 10.8, ease_io(seg(f, 1, n)))
    cam_az = lambda f: lerp(-0.05, 0.05, ease_io(seg(f, 1, n)))
    tgt = Vector((0, 0, 0.0))

    def cam_loc(f):
        return orbit(tgt, cam_d(f), math.radians(4), cam_az(f))
    item_pos = []
    for i, (key, label) in enumerate(C.INGREDIENTS):
        e, base_rot = _ingredient(S, key)
        col, row = i % 3, min(i // 3, len(rows) - 1)
        side = -1 if col == 0 else (1 if col == 2 else (-1 if row % 2 else 1))
        g = Vector((cols[col], 0.0, rows[row]))
        fi = 5 + 6 * i
        start = Vector((side * 3.6, -2.0, g.z + 0.9 * math.sin(i * 1.7)))
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
        item_pos.append((fi, pos, hero))

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
    # ---- the chef peeks up from the bottom and watches every ingredient ----
    K2 = 0.95
    home = Vector((0, -1.2, -3.95))
    cat = CT.Cat(S, "cat", K=K2, home=home)
    neck = home.z + CT.NECK_Z * K2
    pz = neck + 0.08

    def pose(f):
        p = idle(f, 0.5)
        cur = None
        for fi, pos, hero in item_pos:
            if f >= fi:
                cur = (fi, pos, hero)
        if f >= 92:
            look = [ip for ip in item_pos if ip[2]][0][1](f)
        elif cur is not None:
            look = cur[1](f)
        else:
            look = cam_loc(f)
        p["look"] = look
        p["head"] = addv(face_to(home, look, 0.45, K=K2), wob(f, 0.5))
        p["blink"] = BL(f, (30, 66))
        p["open"] = 0.55 * B(f, 92, 96, 104, 110)
        p["ears"] = B(f, 92, 95, 102, 106)
        tap = 0.0
        for fi, _, _ in item_pos:
            tap = max(tap, B(f, fi + 12, fi + 14, fi + 15, fi + 18))
        for side, s in (("L", -1), ("R", 1)):
            base = Vector((s * 0.42, home.y - 0.72, pz))
            lift = Vector((0, 0, 0.1 * tap * (1 if (f // 3) % 2 == (s > 0) else 0.4)))
            if side == "R":
                base = base.lerp(Vector((0.55, home.y - 1.1, pz + 0.9)), ease_io(seg(f, 94, 102), 2))
            p[side] = (base + lift, (0.2, 0.0, 0.0))
        return p
    cat.animate(S.frames(), pose)
    ST.studio_rig(S.sc, (0, 0, -0.5), k=0.7, rim=1.0)
    S.ambient("dust", "flour", 30, box=((-2.4, 2.4), (-3.5, 2.0), (-3.6, 3.4)), s=(0.004, 0.009))
    S.camera_path(lambda f: (cam_loc(f), tgt, 50.0))
    S.ov(type="header", num="", text="THE INGREDIENTS", t0=3, t1=89)
    S.cue(92, "whoosh", dur=0.5, up=True)
    S.cue(95, "meow", pitch=1.2)
    return S


# ========================================================== S3 STRETCH =====
def shot_stretch(name, n):
    S = Shot(name, n, M.backdrop_world("W_stretch", center=(0.5, 0.42), inner=(0.08, 0.05, 0.03), radius=0.95),
             fstop=5.6, lens=40)
    rng = S.rng
    MD.floor("S3_floor", S.coll, z=-0.12)
    MD.floured_board("S3_board", S.coll, s=4.6, sy=5.4, cy=0.75)
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

    def ballv(f):
        return 1 - ease_io(seg(f, T_P0, T_P1), 1.8)

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
        U.key_prop(kb["ball"], "value", f, ballv(f))
        U.key_socket(dp["flour"].outputs[0], f, 0.25 + 0.25 * smooth(seg(f, 6, 14)))
    home = Vector((0, 2.1, 0.0))
    cat = CT.Cat(S, "cat", K=CAT_K, home=home)

    def top(f):
        b = ballv(f)
        return SC0 * (TOP + (2 * MD.DOUGH_BALL_R - TOP) * b)

    def sprinkle_paw(f):
        return Vector((0.2 + 0.05 * math.sin(f * 1.7), 0.1 + 0.05 * math.cos(f * 1.3), 1.45))
    PW = 0.115 * CAT_K * 1.0

    def paws(f):
        out = {}
        b = ballv(f)
        for side, s in (("L", -1), ("R", 1)):
            rest = Vector((s * 1.2, 1.05, 0.13))
            ph = 0.0 if s < 0 else math.pi
            knead = Vector((s * (0.16 + 0.5 * (1 - b)), 0.04 * s, top(f) + PW + 0.15 * max(0.0, math.sin(TAU * (f - 15) / 8 + ph))))
            edge = Vector((s * 1.05, -0.05, 0.1))
            up = Vector((s * 0.72, 0.0, 0.95 + 0.25 * height(f) / HPEAK))
            keys = [(1, rest), (12, rest), (16, knead), (42, knead), (46, edge), (49, edge), (53, up), (68, up),
                    (78, rest), (82, rest)]
            if side == "R":
                keys = [(1, sprinkle_paw(1)), (13, sprinkle_paw(13)), (16, knead)] + keys[3:]
            pos = path(keys, f)
            if 16 <= f <= 42:
                pos = knead
            if side == "R" and f <= 13:
                pos = sprinkle_paw(f)
            if side == "R" and f >= 82:
                pat = Vector((0.8, -0.8, 0.13 + 0.22 * (1 - B(f, 84, 86, 87, 89)) * (1 - B(f, 90, 92, 93, 95))))
                pos = path([(82, rest), (85, pat)], f) if f < 85 else pat
                if f >= 96:
                    pos = Vector((0.8, -0.8, 0.13)).lerp(rest, ease_io(seg(f, 96, 103)))
            flip = B(f, 50, 54, 66, 72)
            rot = Vector((0, 0, 0)).lerp(Vector(PALM_UP), flip)
            out[side] = (pos, tuple(rot))
        return out

    def pose(f):
        p = idle(f)
        if f <= 14:
            look = Vector((0, 0, 0.5))
        elif f < 44:
            look = Vector((0, 0, top(f)))
        elif f < 78:
            look = Vector((0, 0, height(f) + 0.05))
        elif f < 96:
            look = Vector((0.8, -0.8, 0.1))
        else:
            look = cam(f)[0]
        p["look"] = look
        sneeze = B(f, 76, 77, 78, 82)
        p["head"] = addv(face_to(home, look, 0.55), wob(f), (0.35 * sneeze, 0.0, 0.0))
        p["blink"] = max(0.45 * B(f, 18, 22, 38, 42), sneeze, BL(f, (8, 60)), 0.7 * B(f, 86, 89, 98, 102))
        p["open"] = 0.6 * B(f, 50, 53, 62, 66) + 0.4 * B(f, 76, 77, 78, 80)
        p["ears"] = B(f, 49, 52, 64, 70) - 0.6 * sneeze
        p["lean"] = 0.12 * B(f, 14, 18, 40, 44) - 0.08 * B(f, 50, 54, 64, 70)
        p.update(paws(f))
        return p
    # flour sprinkle from the chef's paw onto the board and the dough ball
    N = 260
    tg = disc_points(rng, N, 0.0, 1.5, 0.0)
    e = 2 + rng.uniform(0, 10, N)
    p0 = np.array([tuple(sprinkle_paw(x) + Vector((0, 0, -0.1))) for x in e]) + rng.normal(0, 0.06, (N, 3))
    T = rng.uniform(13, 19, N) / C.FPS
    v0 = (tg - p0 + np.stack([np.zeros(N), np.zeros(N), 0.5 * 12.0 * T * T], 1)) / T[:, None]
    rr = np.hypot(tg[:, 0], tg[:, 1])
    land = T * C.FPS
    life = np.where(rr < 0.42, land, 1e5)
    S.ballistic("flour", "flour", p0, v0, e, land, life, 1.0, rng.uniform(0.006, 0.012, N), gravity=12.0, spin=0.3)
    S.cue(1, "grains", mat="flour", items=[(float(a + b), tuple(t)) for a, b, t in zip(e, land, tg)])
    Nb = 160
    th = rng.uniform(0, TAU, Nb)
    r0 = rng.uniform(1.1, 1.3, Nb)
    p0 = np.stack([r0 * np.cos(th), r0 * np.sin(th), rng.uniform(0.01, 0.05, Nb)], 1)
    sp = rng.uniform(0.6, 1.4, Nb)
    v0 = np.stack([sp * np.cos(th), sp * np.sin(th), rng.uniform(0.6, 1.6, Nb)], 1)
    land = fx.landing(p0, v0, 12.0, drag=2.0, floor_z=0.0, max_frames=60)
    eb = T_LAND + rng.uniform(0, 2, Nb)
    S.ballistic("flour_burst", "flour", p0, v0, eb, land, np.full(Nb, 1e5), 1.0,
                rng.uniform(0.006, 0.011, Nb), gravity=12.0, drag=2.0, spin=0.3)
    S.cue(1, "grains", mat="flour", items=[(float(a + b), tuple(q)) for a, b, q in zip(eb, land, p0)])
    # a squish every time a kneading paw lands on the dough
    for side, ph in (("L", 0.0), ("R", math.pi)):
        lift = lambda f, ph=ph: max(0.0, math.sin(TAU * (f - 15) / 8 + ph))
        for f in range(17, 43):
            if lift(f) < 0.02 <= lift(f - 1):
                x = (-1 if side == "L" else 1) * (0.16 + 0.5 * (1 - ballv(f)))
                S.cue(f, "squish", pos=(x, 0.0, top(f)), size=0.8 + 0.4 * (1 - ballv(f)))

    def cam(f):
        tgt = Vector((0, 0.5, 0.7 + 0.25 * height(f)))
        d, el, az, lens = 6.4, math.radians(26), -0.1 + 0.001 * f, 42.0
        t = ease_io(seg(f, 78, n), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0.3, 0.05, 0.45)), t)
            d = lerp(d, 5.6, t)
        return orbit(tgt, d, el, az), tgt, lens
    cat.animate(S.frames(), pose)
    cam0 = cam(1)[0]
    puff = S.steam("puff", (0, 0), 1.25, (0.03, 0.25), 30, cam0, s=(0.35, 0.7), rise=(0.003, 0.007))
    key_density(puff, S.frames(), lambda f: 0.45 * smooth(seg(f, 8, 12)) * (1 - smooth(seg(f, 22, 34)))
                + 0.9 * smooth(seg(f, T_LAND, T_LAND + 3)) * (1 - smooth(seg(f, 88, n))))
    S.cue(18, "purr", dur=0.8, gain=0.7)
    S.cue(T_TOSS, "whoosh", dur=0.5, up=True, gain=0.6)
    S.cue(51, "meow", pitch=1.3, gain=0.6)
    S.cue(T_LAND, "thud", size=0.7, soft=True, pos=(0, 0, 0.05))
    S.cue(T_LAND, "squish", size=1.3, pos=(0, 0, 0.05))
    S.cue(T_LAND + 1, "puff", size=1.0, gain=0.7)
    S.cue(77, "sneeze")
    S.cue(86, "pat", pos=(0.8, -0.8, 0.1))
    S.cue(92, "pat", pos=(0.8, -0.8, 0.1))
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0.5, 0.6), k=0.26, rim=0.7, top=0.45)
    S.header("stretch", 3, 98)
    S.track("rim", lambda f: Vector((0.84, -0.84, 0.08)))
    S.ov(type="callout", text="LEAVE A PUFFY EDGE", track="rim", t0=84, t1=n, dx=-150, dy=250)
    return S


# ============================================================== S4 TOP ======
def shot_top(name, n):
    S = Shot(name, n, M.backdrop_world("W_top", center=(0.5, 0.42), inner=(0.08, 0.05, 0.03), radius=0.95),
             fstop=5.6, lens=40)
    rng = S.rng
    MD.floor("S4_floor", S.coll, z=-0.12)
    MD.floured_board("S4_board", S.coll, s=4.6, sy=5.4, cy=0.75)
    base, dp = raw_base(S, "S4", flour=0.4)
    base.data.shape_keys.key_blocks["ball"].value = 0.0
    home = Vector((0, 2.1, 0.0))
    cat = CT.Cat(S, "cat", K=CAT_K, home=home)
    # ---- 02 SAUCE: the chef drops a dollop off the spoon, then spreads it ----
    T_BLOB, T_HIT, T_SP0, T_SP1, T_OUT = 4, 10, 14, 48, 56
    sauce = MD.pizza_layer("S4_sauce", S.coll, MD.PZ_SAUCE_R, MD.sauce_z, mat=M.pizza_sauce())

    def rad(f):
        return lerp(0.22, 1.0, ease_io(seg(f, T_SP0, T_SP1), 1.4))
    U.animate(sauce, S.frames(), lambda f: dict(loc=(0, 0, TOP), scl=(rad(f), rad(f),
                                                                     lerp(5.0, 1.0, smooth(seg(f, T_HIT, T_SP1))))))
    hide_range(sauce, S.frames(), lambda f: f >= T_HIT)
    spn = MD.spoon("S4_spoon", S.coll)
    HOLD = Vector((0.05, 0.15, 1.15))
    D_HOLD = Vector((0.0, 0.5, 1.0)).normalized()

    def spoon_state(f):
        u = ease_io(seg(f, T_SP0, T_SP1), 1.4)
        r = max(0.0, rad(f) - 0.15)
        a = 0.4 + TAU * 2.3 * u
        c = Vector((r * math.cos(a), r * math.sin(a), TOP + 0.03))
        d = (Vector((math.cos(a), math.sin(a), 0)) * 0.3 + Vector((0.0, 0.45, 1.0))).normalized()
        if f < T_SP0:
            k = ease_io(seg(f, T_BLOB + 1, T_SP0), 2)
            c, d = HOLD.lerp(c, k), D_HOLD.lerp(d, k).normalized()
        if f > T_SP1:
            k = ease_io(seg(f, T_SP1, T_OUT), 2)
            c = c.lerp(Vector((1.6, 1.0, 1.4)), k)
        return c, d
    U.animate(spn, S.frames(), lambda f: dict(loc=spoon_state(f)[0],
                                              rot=tuple(spoon_state(f)[1].to_track_quat("Z", "Y").to_euler())))
    hide_range(spn, S.frames(), lambda f: f <= T_OUT)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.16)
    for fc in bm.faces:
        fc.smooth = True
    me = bpy.data.meshes.new("S4_blob")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M.pizza_sauce())
    blob = MD.new_obj("S4_blob", me, S.coll)
    U.animate(blob, S.frames(), lambda f: dict(
        loc=tuple(Vector((HOLD.x, HOLD.y, HOLD.z - 0.12)).lerp(Vector((0, 0, TOP + 0.1)), ease_in(seg(f, T_BLOB, T_HIT), 2))),
        scl=(0.9, 0.9, lerp(1.35, 1.0, seg(f, T_BLOB, T_HIT)))))
    hide_range(blob, S.frames(), lambda f: 1 <= f < T_HIT)
    S.cue(T_HIT, "splat", pos=(0, 0, TOP))
    amps = [(spoon_state(f + 1)[0] - spoon_state(f)[0]).length for f in range(T_SP0, T_SP1 + 1)]
    S.cue(T_SP0, "smear", amps=amps, pos=(0, 0, TOP))
    S.header("sauce", 3, 54)
    # ---- 03 TOP: mozzarella showered from both paws -----------------------
    T_M0, T_M1 = 56, 80

    def sprinkle(side, f):
        s = -1 if side == "L" else 1
        a = (f - T_M0) * 0.32 + (0 if s < 0 else math.pi * 0.6)
        return Vector((s * 0.45 + 0.32 * math.cos(a), -0.05 + 0.38 * math.sin(a), 1.05 + 0.05 * math.sin(f * 1.9)))
    pts, s, sv, rot = shred_layout()
    N = len(pts)
    e = T_M0 + 1 + rng.uniform(0, T_M1 - T_M0 - 6, N)
    side_of = np.where(pts[:, 0] < 0, "L", "R")
    p0 = np.array([tuple(sprinkle(sd, ee) + Vector((0, 0, -0.12))) for sd, ee in zip(side_of, e)]) + \
        rng.normal(0, 0.07, (N, 3))
    T = rng.uniform(9, 13, N) / C.FPS
    v0 = (pts - p0 + np.stack([np.zeros(N), np.zeros(N), 0.5 * 30.0 * T * T], 1)) / T[:, None]
    S.ballistic("shreds", "shred", p0, v0, e, T * C.FPS, np.full(N, 1e5), 1.0, s, sv=sv, spin=0.2, final_rot=rot)
    S.cue(T_M0, "grains", mat="cheese", items=[(float(a + b * C.FPS), tuple(q)) for a, b, q in zip(e, T, pts)])
    # ---- pepperoni dealt one by one from the right paw ---------------------
    ppts, prot = pep_layout(TOP + 0.036)
    Np = len(ppts)
    order = np.argsort(np.mod(np.arctan2(ppts[:, 1], ppts[:, 0]) + 1.2, TAU) + 0.3 * np.hypot(ppts[:, 0], ppts[:, 1]))
    ep = np.empty(Np)
    ep[order] = 84 + np.arange(Np) * 1.05
    deal_keys = [(ep[i], Vector(ppts[i]) + Vector((0, 0.08, 0.5))) for i in order]

    def deal(f):
        return path(deal_keys, f)
    origin = np.array([tuple(deal(ep[i]) + Vector((0, 0, -0.1))) for i in range(Np)])
    Tp = rng.uniform(6, 8, Np) / C.FPS
    v0 = (ppts - origin + np.stack([np.zeros(Np), np.zeros(Np), 0.5 * 30.0 * Tp * Tp], 1)) / Tp[:, None]
    spin = np.stack([rng.normal(0, 0.15, Np), rng.normal(0, 0.15, Np), rng.normal(0, 0.08, Np)], 1)
    S.ballistic("pep", "pep", origin, v0, ep, Tp * C.FPS, np.full(Np, 1e5), 1.0, np.full(Np, MD.PEP_R),
                spin=spin, final_rot=prot)
    for i in range(Np):
        S.cue(ep[i] + Tp[i] * C.FPS, "plop", pos=tuple(ppts[i]))
    # ---- oregano rubbed from the paw ------------------------------------------
    def rub(f):
        return Vector((0.1 + 0.06 * math.sin(f * 1.6), -0.1 + 0.05 * math.cos(f * 1.2), 1.2))
    opts, osz = oregano_layout(TOP + 0.033)
    No = len(opts)
    eo = 114 + rng.uniform(0, 8, No)
    p0 = np.array([tuple(rub(x) + Vector((0, 0, -0.1))) for x in eo]) + rng.normal(0, 0.05, (No, 3))
    To = rng.uniform(10, 14, No) / C.FPS
    v0 = (opts - p0 + np.stack([np.zeros(No), np.zeros(No), 0.5 * 30.0 * To * To], 1)) / To[:, None]
    S.ballistic("oregano", "oregano", p0, v0, eo, To * C.FPS, np.full(No, 1e5), 1.0, osz, spin=0.3)
    S.cue(114, "grains", mat="herb", items=[(float(a + b * C.FPS), tuple(q)) for a, b, q in zip(eo, To, opts)])
    S.header("top", 56, 130)

    def cam(f):
        tgt = Vector((0, 0.4, 0.62))
        d, el, az, lens = 6.3, math.radians(34), -0.12 + 0.0011 * f, 42.0
        t = ease_io(seg(f, 108, n), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0.05, 0.25, 0.55)), t)
            d = lerp(d, 5.7, t)
        return orbit(tgt, d, el, az), tgt, lens

    def pose(f):
        p = idle(f)
        rest = {"L": Vector((-1.2, 1.05, 0.13)), "R": Vector((1.2, 1.05, 0.13))}
        c, d = spoon_state(f)
        if f <= T_OUT + 2:
            look = c
        elif T_M0 <= f <= T_M1 + 2:
            look = sprinkle("R", f) + Vector((0, 0, -0.9))
        elif 82 <= f <= 112:
            look = deal(f) + Vector((0, 0, -0.4))
        elif 112 < f <= 124:
            look = Vector((0, 0, 0.1))
        else:
            look = cam(f)[0]
        p["look"] = look
        p["head"] = addv(face_to(home, look, 0.5), wob(f))
        p["tongue"] = 0.7 * B(f, T_SP0, T_SP0 + 4, T_SP1 - 4, T_SP1) + 0.6 * B(f, 86, 90, 106, 110)
        p["blink"] = max(BL(f, (26, 70, 98)), 0.75 * B(f, 125, 127, 131, 134))
        p["open"] = 0.5 * B(f, 125, 127, 130, 133)
        p["lean"] = 0.1 * B(f, 12, 16, 46, 52) + 0.08 * B(f, 82, 86, 108, 112)
        p["ears"] = B(f, 124, 126, 130, 134)
        # right paw: spoon -> sprinkle -> deal -> rub -> ta-da
        if f <= T_OUT:
            rp = c + d * 1.3
            rr = grip(d)
        else:
            k_m = B(f, T_OUT, T_M0, T_M1, T_M1 + 3)
            pos = rest["R"].lerp(sprinkle("R", f), k_m)
            if 80 < f <= 112:
                pos = rest["R"].lerp(deal(f), B(f, 80, 84, 109, 112))
            if 110 < f <= 126:
                pos = rest["R"].lerp(rub(f), B(f, 110, 114, 122, 125))
            if f > 124:
                pos = rest["R"].lerp(Vector((1.45, 1.1, 1.15)), B(f, 124, 128, 140, 141))
            rp = pos
            rr = tuple(Vector((0, 0, 0)).lerp(Vector(PALM_CAM), B(f, 124, 128, 140, 141)))
        p["R"] = (rp, rr)
        lp = rest["L"].lerp(sprinkle("L", f), B(f, T_OUT, T_M0, T_M1, T_M1 + 3))
        if f > 124:
            lp = rest["L"].lerp(Vector((-1.45, 1.1, 1.15)), B(f, 124, 128, 140, 141))
        p["L"] = (lp, tuple(Vector((0, 0, 0)).lerp(Vector(PALM_CAM), B(f, 124, 128, 140, 141))))
        return p
    cat.animate(S.frames(), pose)
    S.cue(126, "meow", pitch=1.1, gain=0.6)
    S.track("mozz", lambda f: Vector((0.55, -0.45, TOP + 0.03)))
    S.ov(type="label", text="MOZZARELLA", track="mozz", t0=70, t1=104, side="right")
    early = np.where(ep < 94)[0]
    front = int(early[np.argmin(ppts[early, 1] + 0.3 * np.abs(ppts[early, 0]))])
    fp = Vector(ppts[front])
    S.track("pep", lambda f: fp + Vector((0, 0, 0.01)))
    S.ov(type="label", text="PEPPERONI", track="pep", t0=max(98, ep[front] + 10), t1=n, side="left")
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0.5, 0.6), k=0.27, rim=0.6, top=0.6)
    return S


# ============================================================= S5 BAKE ======
def shot_bake(name, n):
    S = Shot(name, n, M.backdrop_world("W_bake", center=(0.5, 0.35), inner=(0.03, 0.02, 0.015), radius=0.9),
             fstop=4.0, lens=30)
    rng = S.rng
    MD.floor("S5_ground", S.coll, z=-1.3)
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
    ST.area(S.sc, "S5_fill", (0.8, 1.8, 2.6), REST, 380, (2.0, 2.0), (1.0, 0.9, 0.8))
    ST.area(S.sc, "S5_top", (0.6, -0.9, 3.6), REST, 200, (2.0, 2.0), (1.0, 0.9, 0.8))
    ST.area(S.sc, "S5_glow", (0.0, -2.7, 0.35), (0, -4.6, 0.4), 55, (1.4, 0.6), (1.0, 0.62, 0.32))
    ST.area(S.sc, "S5_catkey", (-1.8, -7.0, 2.4), (0, -4.6, 0.3), 110, (2.0, 2.0), (1.0, 0.92, 0.85))
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
    bper, bph, bdens = rng.uniform(14, 26, 70), rng.uniform(0, 26, 70), rng.uniform(0, 1, 70)
    bub = S.looping("bubbles", "cbubble", bpts, np.zeros_like(bpts), bper, bph,
                    rng.uniform(0.02, 0.04, 70), sv=(1, 1, 0.65), pop=1.0, density=0.0, parent=pz, dens=bdens)
    bdensity = lambda f: 0.75 * smooth(seg(f, 50, 62))
    key_density(bub, S.frames(), bdensity)
    for i in range(70):
        k = 0
        while True:
            fp = k * bper[i] - bph[i] + 0.92 * bper[i]
            k += 1
            if fp > n:
                break
            if fp >= 50 and bdens[i] < bdensity(fp):
                S.cue(fp, "bubblepop", pitch=float(rng.uniform(0.7, 1.5)),
                      pos=tuple(Vector((0.0, -0.55, 0.0)) + Vector(bpts[i])))
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
    pl = MD.peel("S5_peel", S.coll, L=2.2)
    T_IN1, T_OUT0, T_OUT1 = 20, 24, 34

    def peel_y(f):
        y = lerp(-2.7, REST.y, ease_out(seg(f, 1, T_IN1), 2.5))
        return lerp(y, -6.2, ease_in(seg(f, T_OUT0, T_OUT1), 2.0))
    U.animate(pl, S.frames(), lambda f: dict(loc=(0, peel_y(f), 0.012)))
    hide_tree(pl, S.frames(), lambda f: f <= T_OUT1 + 1)
    U.animate(pz, S.frames(), lambda f: dict(loc=(0, peel_y(f), 0.012) if f < T_OUT0 else tuple(REST)))
    # ---- the chef pushes it in, then peeks into the oven -------------------
    GZ = -1.3
    cat = CT.Cat(S, "cat", K=CAT_K, home=(0, -4.75, GZ), yaw=math.pi)

    def grip_end(f):
        return peel_y(f) - 3.9 + 0.15

    def root_y(f):
        if f <= T_OUT1:
            return min(-4.95, grip_end(f) - 0.75)
        return lerp(min(-4.95, grip_end(T_OUT1) - 0.75), -4.75, ease_io(seg(f, T_OUT1, 46), 2))

    def cam(f):
        ck = [(1, (0.35, 2.45, 1.5)), (36, (0.3, 2.2, 1.45)), (62, (0.25, 1.45, 1.42)), (n, (0.22, 1.2, 1.36))]
        tk = [(1, (0.0, -2.4, 0.45)), (36, (0.0, -2.3, 0.42)), (62, (0.0, -1.7, 0.38)), (n, (0.0, -1.75, 0.36))]
        return spline_path(ck, f), spline_path(tk, f), lerp(30, 32, smooth(seg(f, 36, n)))

    def pose(f):
        root = Vector((0, root_y(f), GZ))
        p = idle(f)
        p["root"] = root
        p["yaw"] = math.pi
        p["lean"] = 0.18 * smooth(seg(f, 40, 50)) + 0.06 * B(f, 2, 6, 18, 22)
        look = REST + Vector((0, 0, 0.1))
        if 82 <= f <= 92:
            look = cam(f)[0]
        p["look"] = look
        p["head"] = addv(face_to(root, look, 0.45, yaw=math.pi), wob(f))
        p["tongue"] = 0.6 * B(f, 3, 6, 17, 21) + B(f, 66, 69, 75, 79)
        p["open"] = 0.6 * B(f, 92, 95, 101, 105) + 0.2 * B(f, 66, 69, 75, 79)
        p["ears"] = B(f, 92, 95, 101, 105)
        p["blink"] = BL(f, (56, 86))
        ge = grip_end(f)
        hold = [Vector((0.12, ge, 0.2)), Vector((-0.12, ge + 0.55, 0.2))]
        sill = [Vector((0.75, -3.72, 0.2)), Vector((-0.75, -3.72, 0.2))]
        k = smooth(seg(f, T_OUT1, 44))
        for side, h, sl in (("R", hold[0], sill[0]), ("L", hold[1], sill[1])):
            if f <= T_OUT1:
                pos = h
            else:
                h0 = Vector((h.x, grip_end(T_OUT1) + (0.55 if side == "L" else 0.0), 0.2))
                pos = h0.lerp(sl, k) + Vector((0, 0, 0.35 * math.sin(math.pi * k)))
            pos = pos + Vector((0, 0, 0.03 * math.sin(f * 0.5 + (0 if side == "R" else 2)) * smooth(seg(f, 46, 60))))
            p[side] = (pos, (0, 0, math.pi))
        return p
    cat.animate(S.frames(), pose)
    S.camera_path(cam)
    S.cue(1, "crackle", dur=n / C.FPS, gain=0.8)
    S.cue(1, "scrape", amps=[abs(peel_y(f + 1) - peel_y(f)) for f in range(1, T_OUT1 + 2)], pos=(0, -1.6, 0))
    S.cue(T_IN1, "clack", pos=(0, -0.55, 0), gain=0.6)
    S.cue(44, "purr", dur=2.2, gain=0.8)
    S.cue(50, "sizzle_soft", dur=1.9)
    S.cue(93, "meow", pitch=1.15, gain=0.55)
    S.header("bake", 3, 98)
    S.ov(type="haze", t0=30, t1=n, y0=0.45, y1=1.0, amp=1.3)
    S.track("bub", lambda f: Vector((0.35, -0.25, TOP + 0.03)))
    S.ov(type="callout", text="BUBBLING & GOLDEN", track="bub", t0=84, t1=n, dx=-120, dy=260)
    return S


# ============================================================ S6 SLICE ======
def _slice_matrix(P, theta, beta, Cg):
    return (Matrix.Translation(P) @ Matrix.Rotation(theta, 4, "Z") @ Matrix.Rotation(beta, 4, "X") @
            Matrix.Translation(-Vector(Cg)))


def shot_slice(name, n):
    S = Shot(name, n, M.backdrop_world("W_slice", center=(0.5, 0.42), radius=0.95), fstop=5.6, lens=40)
    rng = S.rng
    MD.floor("S6_floor", S.coll, z=0.0)
    MD.round_board("S6_board", S.coll)
    root, wedges, parts = baked_pizza(S, "S6")
    BZ = MD.ROUND_BOARD_TOP
    root.location.z = BZ
    MR = Matrix.Translation((0, 0, BZ))
    home = Vector((0, 2.15, 0.0))
    cat = CT.Cat(S, "cat", K=CAT_K, home=home)
    G = 0.007
    passes = [(0, 6, 15), (2, 18, 27), (1, 30, 38), (3, 40, 48)]

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
    # ---- hero slice (pointing at the chef): lifted by the crust, then bitten
    HK = 4
    Cg = Vector((0, 1.2, 0.1))
    T_P0, T_UP, T_HI, T_BITE = 54, 68, 86, 97
    bite_pose = dict(root=home, lean=0.16, head=(0.12, 0, 0))
    mouth = MR.inverted() @ cat.mouth_world(bite_pose)
    tip_off = Matrix.Rotation(math.pi, 3, "Z") @ Matrix.Rotation(-0.3, 3, "X") @ (Vector((0, 0, TOP + 0.02)) - Cg)
    P_end = mouth - Vector((0, 0.06, 0.02)) - tip_off
    P0 = Cg + gap_disp(HK, n)
    Pk = [(T_P0, P0), (T_UP, Vector((0, 0.85, 1.0))), (T_HI, Vector((0, 0.95, 1.3))), (T_BITE, P_end)]
    Bk = [(T_P0, (0.0, 0.0)), (T_UP, (0.8, 0.0)), (T_HI, (0.95, 0.0)), (T_BITE, (-0.3, 0.0))]
    Tk = [(T_P0, (0.0, 0.0)), (T_HI, (0.15, 0.0)), (T_BITE, (math.pi, 0.0))]

    def slice_m(f):
        if f < T_P0:
            return Matrix.Translation(gap_disp(HK, f))
        return _slice_matrix(path(Pk, f), path(Tk, f)[0], path(Bk, f)[0], Cg)
    for k, w in enumerate(wedges):
        for f in S.frames():
            if k == HK:
                loc, q, _ = slice_m(f).decompose()
                U.key(w, f, loc=loc, quat=q)
            else:
                U.key(w, f, loc=gap_disp(k, f), quat=Quaternion())
    # ---- pizza wheel, pushed away from the chef ----------------------------
    cr, spin = MD.cutter("S6_cutter", S.coll)
    cr.parent = root
    RW, REACH = 0.36, 1.45
    CZ = RW - 0.006
    HAND = Vector((0, -math.cos(0.65), math.sin(0.65)))

    def pass_pts(j):
        c = CUT_OFF + j * DW
        d = Vector((math.cos(c), math.sin(c), 0))
        if d.y > 0:
            d = -d
        a = math.atan2(d.y, d.x)
        return -d * REACH + Vector((0, 0, CZ)), d * REACH + Vector((0, 0, CZ)), a - math.pi / 2

    def cutter_state(f):
        if f < passes[0][1]:
            a, _, rz = pass_pts(passes[0][0])
            u = ease_out(seg(f, 1, passes[0][1]), 2.5)
            return Vector((1.4, 1.2, 1.6)).lerp(a, u), rz, 0.0
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
        u = ease_in(seg(f, passes[-1][2], passes[-1][2] + 6), 2)
        return b.lerp(Vector((1.6, 1.0, 1.4)), u), rz, acc
    for f in S.frames():
        p, rz, dd = cutter_state(f)
        U.key(cr, f, loc=p, rot=(0, 0, rz))
        U.key(spin, f, rot=(-dd / RW, 0, 0))
    hide_tree(cr, S.frames(), lambda f: f <= passes[-1][2] + 6)
    # the wheel's roll follows its speed while it is down; a crunch each
    # time it crosses the crust
    amps = []
    for f in range(1, n + 1):
        p1, _, d1 = cutter_state(f)
        p2, _, d2 = cutter_state(f + 1)
        amps.append(abs(d2 - d1) if p1.z < CZ + 0.05 else 0.0)
    S.cue(1, "roll", amps=amps, pos=(0, 0, BZ))
    for j, t0, t1 in passes:
        for f in range(t0, t1 + 1):
            r0, r1 = cutter_state(f)[0].xy.length, cutter_state(f + 1)[0].xy.length
            for rc in (1.24, 1.0):
                if (r0 - rc) * (r1 - rc) < 0:
                    S.cue(f + 0.5, "crunch", size=0.5 if rc > 1.1 else 0.3,
                          pos=tuple(MR @ cutter_state(f)[0]))

    def cutter_grip(f):
        p, rz, _ = cutter_state(f)
        d = Matrix.Rotation(rz, 3, "Z") @ HAND
        return MR @ (p + d * 1.72), grip(d)
    # ---- molten cheese strings between the hero slice and its neighbours ----
    NS, Kp = 64, 22
    chains, A, BLs, Uu, BRK, RR, SD = [], [], [], [], [], [], []
    for i in range(NS):
        edge = i % 2
        c = CUT_OFF + (HK + edge) * DW
        r = 0.06 + 0.88 * rng.uniform(0, 1) ** 0.85
        z = TOP + 0.013 + rng.uniform(-0.004, 0.006)
        pnt = Vector((r * math.cos(c), r * math.sin(c), z))
        nk = HK - 1 if edge == 0 else HK + 1
        a = pnt + gap_disp(nk, n)
        brk, rr, sd = rng.uniform(0.6, 1.6), rng.uniform(0.45, 1.25), rng.uniform(0, 50)
        chains.append(np.repeat(np.array(a)[None, :], Kp, 0))
        for q in range(Kp):
            A.append(tuple(a))
            BLs.append(tuple(pnt))
            Uu.append(q / (Kp - 1))
            BRK.append(brk)
            RR.append(rr)
            SD.append(sd)
    # a tiny wet snap for every cheese string, on the frame it breaks
    for i in range(NS):
        a, bl, brk = Vector(A[i * Kp]), Vector(BLs[i * Kp]), BRK[i * Kp]
        prev = 0.0
        for f in range(T_P0, n + 1):
            L = ((slice_m(f) @ bl) - a).length
            if prev < brk + 0.12 <= L:
                S.cue(f, "snap", pos=tuple(MR @ ((slice_m(f) @ bl + a) * 0.5)))
                break
            prev = L
    fx.strands_object("S6_strings", S.coll, chains, dict(a=A, bl=BLs, u=Uu, brk=BRK, rr=RR, sd=SD),
                      fx.cheese_pull_group(), {"Slice": wedges[HK], "Radius": 0.014, "Sag": 0.3,
                                               "Material": parts["mozz"]}, parent=root)

    def cam(f):
        tgt = Vector((0, 0.5, 0.75))
        d, el, az, lens = 6.4, math.radians(30), 0.0 + 0.001 * f, 42.0
        t = ease_io(seg(f, 46, 72), 2)
        if t > 0:
            tgt = tgt.lerp(Vector((0.0, 0.95, 1.1)), t)
            d, el, az = lerp(d, 5.2, t), lerp(el, math.radians(12), t), lerp(az, 0.8, t)
        t2 = ease_io(seg(f, 72, 105), 1.5)
        if t2 > 0:
            d -= 0.45 * t2
            az += 0.1 * t2
        t3 = ease_io(seg(f, 100, n), 2)
        if t3 > 0:
            tgt = tgt.lerp(Vector((0.0, 1.3, 1.12)), t3)
            d -= 0.6 * t3
        return orbit(tgt, d, el, az), tgt, lens

    def pose(f):
        p = idle(f)
        chew = 0.06 * math.sin((f - 97) * TAU / 7) * smooth(seg(f, 97, 100)) * (1 - smooth(seg(f, 115, 119))) \
            if f > 97 else 0.0
        p["lean"] = 0.08 * B(f, 4, 8, 46, 50) + 0.16 * smooth(seg(f, T_HI, T_BITE))
        sm = MR @ slice_m(f)
        if f <= 50:
            look = cutter_grip(f)[0] + Vector((0, -0.6, -0.9))
        elif f <= T_HI:
            look = MR @ Vector((0, 0.6, 0.3)) if f > 60 else sm @ Vector((0, 0.6, 0.1))
        else:
            look = sm @ Vector((0, 0.0, 0.1))
        p["look"] = look
        hd = face_to(home, look, 0.4)
        p["head"] = addv(hd, wob(f), (0.12 * smooth(seg(f, T_HI, T_BITE)) + chew, 0, 0))
        p["tongue"] = 0.5 * B(f, 6, 10, 44, 48)
        p["open"] = 0.5 * B(f, 58, 64, 84, 88) + B(f, 86, 91, 93, 96) + \
            (0.22 * max(0.0, math.sin((f - 97) * TAU / 7)) if 97 < f < 118 else 0.0)
        p["ears"] = B(f, 56, 62, 88, 94)
        p["blink"] = max(BL(f, (22, 50)), 0.85 * smooth(seg(f, 94, 97)))
        crust = [sm @ Vector((-0.32, 1.18, 0.14)), sm @ Vector((0.32, 1.18, 0.14))]
        for side, s, ci in (("L", -1, 0), ("R", 1, 1)):
            rest = Vector((s * 1.25, 1.2, BZ + 0.13))
            hold = crust[ci]
            hrot = grip((sm.to_3x3() @ Vector((0, -0.3, 1))).normalized())
            if side == "R" and f <= 48:
                pos, rot = cutter_grip(f)
                if f < 6:
                    pos = rest.lerp(pos, ease_io(seg(f, 1, 6)))
            elif f < 50:
                pos, rot = rest, (0, 0, 0)
            else:
                k = ease_io(seg(f, 48 if side == "R" else 46, T_P0), 2)
                src = cutter_grip(48)[0] if side == "R" else rest
                pos = src.lerp(hold, k)
                rot = hrot if k > 0.5 else (0, 0, 0)
            p[side] = (pos, rot)
        return p
    cat.animate(S.frames(), pose)
    lifts = [(slice_m(f + 1).translation - slice_m(f).translation).length for f in range(T_P0, T_HI + 1)]
    S.cue(T_P0, "stretch", amps=lifts, pos=tuple(MR @ Vector((0, 0.6, 0.3))))
    S.cue(62, "meow", pitch=1.35, gain=0.55)
    S.cue(94, "nom", pos=tuple(cat.mouth_world(bite_pose)))
    for k in range(3):
        S.cue(97 + 3.5 + 7 * k, "chew", pos=tuple(cat.mouth_world(bite_pose)))
    S.cue(106, "purr", dur=0.45, gain=0.8)
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0.6, 0.8), k=0.4, rim=0.8, top=0.7)
    S.header("slice", 3, 50)
    S.track("pull", lambda f: MR @ ((slice_m(f) @ Vector((0, 0.45, 0.12)) + Vector((0, 0.45, 0.12))) * 0.5))
    S.ov(type="callout", text="THE CHEESE PULL", track="pull", t0=72, t1=n, dx=-200, dy=300)
    return S


# =========================================================== S7 FINAL ======
def shot_final(name, n):
    S = Shot(name, n, M.backdrop_world("W_final", center=(0.5, 0.45), inner=(0.11, 0.06, 0.03), radius=0.95),
             fstop=5.6, lens=45)
    rng = S.rng
    MD.floor("S7_floor", S.coll, z=0.0)
    srv, wedges, _ = served(S, "S7", gap=0.008, hero_pull=0.0)
    home = Vector((0, 1.85, 0.0))
    cat = CT.Cat(S, "cat", K=CAT_K, home=home)
    BT = MD.ROUND_BOARD_TOP * PIZZA_SCALE
    # the chef's slice, held up by the left paw
    Cg = Vector((0, 1.2, 0.1))
    Mr = Matrix.Diagonal((PIZZA_SCALE,) * 3 + (1.0,)) @ Matrix.Translation((0, 0, MD.ROUND_BOARD_TOP))

    def slice_world(f):
        Pw = Vector((-1.0, 1.15, 1.45 + 0.03 * math.sin(f * 0.12)))
        R = Matrix.Rotation(-0.55 + 0.05 * math.sin(f * 0.09), 4, "Z") @ Matrix.Rotation(1.2, 4, "X")
        return Matrix.Translation(Pw) @ R @ Matrix.Diagonal((PIZZA_SCALE,) * 3 + (1.0,)) @ Matrix.Translation(-Cg)
    w4 = wedges[4]
    for f in S.frames():
        loc, q, _ = (Mr.inverted() @ slice_world(f)).decompose()
        U.key(w4, f, loc=loc, quat=q)
    bt = MD.ROUND_BOARD_TOP + TOP + 0.045
    leaves = []
    for i, (x, y, rz, L) in enumerate([(0.25, -0.32, 0.6, 0.34), (-0.42, -0.08, 2.7, 0.3), (0.38, 0.35, 4.4, 0.28)]):
        lf = MD.basil_leaf(f"S7_basil{i}", S.coll, L, seed=i + 3)
        lf.parent = srv
        t0 = 10 + 5 * i
        r0 = Euler((0.1, -0.15, rz))

        def fn(f, x=x, y=y, r0=r0, t0=t0):
            u = seg(f, t0, t0 + 10)
            z = bt + 1.6 * (1 - ease_in(u, 2))
            if f > t0 + 10:
                z += 0.02 * impact((f - t0 - 10) / C.FPS, 3.0, 8.0)
            return dict(loc=(x, y, z), rot=(r0.x + 0.6 * (1 - u), r0.y, r0.z + 1.5 * (1 - u)))
        U.animate(lf, S.frames(), fn)
        hide_range(lf, S.frames(), lambda f, t0=t0: f >= t0)
        leaves.append((t0, lambda f, fn=fn: Vector(fn(f)["loc"]) * PIZZA_SCALE))
        S.cue(t0 + 10, "pop", pitch=0.8 + 0.1 * i)

    def rub(f):
        return Vector((0.35 + 0.06 * math.sin(f * 1.7), -0.1 + 0.05 * math.cos(f * 1.3), 1.25))
    N = 260
    e = 28 + rng.uniform(0, 12, N)
    p0 = np.array([tuple(rub(x) + Vector((0, 0, -0.1))) for x in e]) / PIZZA_SCALE + rng.normal(0, 0.05, (N, 3))
    v0 = np.stack([rng.normal(0, 0.15, N), rng.normal(0, 0.15, N), rng.uniform(-0.6, -0.2, N)], 1)
    land = fx.landing(p0, v0, 6.0, drag=1.5, bvh=served_bvh(), floor_z=MD.ROUND_BOARD_TOP, max_frames=80)
    S.ballistic("herbs", "herb", p0, v0, e, land, np.full(N, 1e5), 1.0, rng.uniform(0.009, 0.016, N),
                gravity=6.0, drag=1.5, parent=srv, spin=0.6)
    S.cue(29, "sprinkle", dur=0.6)
    tgt = Vector((0, 0.7, 1.9))
    cam_d = lambda f: lerp(11.2, 10.6, ease_io(seg(f, 1, n)))
    cam_el = lambda f: math.radians(lerp(13, 15, ease_io(seg(f, 1, n))))

    def cam(f):
        return orbit(tgt, cam_d(f), cam_el(f), 0.0), tgt, 45.0
    TY = 2.9
    lines = [(C.FINAL_TEXT[0], 0.16, "cream", 5.02, 1.2),
             (C.FINAL_TEXT[1], 0.25, "gold", 4.64, 1.1),
             (C.FINAL_TEXT[2], 0.52, "cream", 4.06, 1.0)]
    el0 = cam_el(60)
    slams = []
    for j, (txt, size, matk, z, sp) in enumerate(lines):
        o = MD.text3d(f"S7_title{j}", S.coll, txt, C.FONT_BLACK, size=size, extrude=size * 0.12,
                      bevel=size * 0.025, mat=M.text_mat(matk), spacing=sp)
        t0 = 52 + 7 * j

        def fn(f, t0=t0, z=z, j=j):
            t = seg(f, t0, t0 + 13)
            eb = ease_back(t, 2.0)
            s = 0.6 + 0.4 * eb
            fl = 0.012 * math.sin(TAU * (f - t0) / 60.0 + j)
            return dict(loc=(0, TY, z - 0.15 * (1 - ease_out(t)) + fl),
                        rot=(math.pi / 2 - el0 - 1.3 * (1 - eb), 0, 0), scl=(s, s, s))
        U.animate(o, S.frames(), fn)
        hide_range(o, S.frames(), lambda f, t0=t0: f >= t0)
        S.cue(t0, "whoosh", dur=0.25, pitch=0.9 + 0.1 * j)
        S.cue(t0 + 6, "slam", size=0.45 + 0.2 * j)
        slams.append(t0 + 6)

    def pose(f):
        p = idle(f)
        look = cam(f)[0]
        for t0, lp in leaves:
            if t0 - 2 <= f <= t0 + 12:
                look = lp(f)
        if 26 <= f <= 40:
            look = Vector((0.3, -0.1, 0.2))
        p["look"] = look
        p["head"] = addv(face_to(home, look, 0.35), wob(f), (0, 0.15 * B(f, 42, 45, 52, 56), 0))
        p["blink"] = max(BL(f, (8, 88)), 0.8 * B(f, 96, 99, 103, 106))
        p["wink"] = B(f, 43, 45, 50, 53)
        p["open"] = 0.35 * B(f, 2, 4, 6, 8) + 0.35 * B(f, 6, 8, 10, 12) + 0.7 * B(f, 47, 49, 52, 55)
        p["ears"] = max(B(f, s0, s0 + 1, s0 + 2, s0 + 5) for s0 in slams)
        sw = slice_world(f)
        p["L"] = (sw @ Vector((0, 1.18, 0.16)), grip((sw.to_3x3() @ Vector((0, -0.3, 1))).normalized()))
        rest = Vector((1.0, 0.55, BT + 0.13))
        mouth = cat.mouth_world(p) + Vector((0.08, -0.15, -0.02))
        out = Vector((1.45, 1.1, 1.95))
        keys = [(1, rest), (24, rest), (28, rub(28)), (40, rub(40)), (43, mouth), (45, mouth), (50, out),
                (60, out), (70, rest)]
        pos = path(keys, f)
        if 28 <= f <= 40:
            pos = rub(f)
        p["R"] = (pos, tuple(Vector((0, 0, 0)).lerp(Vector(PALM_CAM), B(f, 44, 49, 60, 70))))
        return p
    cat.animate(S.frames(), pose)
    sw = ST.area(S.sc, "S7_sweep", (-2.5, 3.0, 2.6), (0, 0.8, 1.2), 0, (0.25, 3.0), (1.0, 0.85, 0.6))
    for f in S.frames():
        t = seg(f, 40, 95)
        sw.location = (lerp(-2.8, 2.8, ease_io(t)), 3.2, 2.4)
        sw.keyframe_insert("location", frame=f)
        U.key_prop(sw.data, "energy", f, 700 * math.sin(math.pi * t))
    st = S.steam("steam", (0, 0), 0.7, (0.3, 0.6), 12, cam(60)[0], s=(0.3, 0.45))
    key_density(st, S.frames(), lambda f: 0.6)
    S.ambient("herbs_bg", "herb", 36, box=((-2.6, 2.6), (1.0, 4.0), (-0.2, 5.0)), s=(0.008, 0.015))
    S.ambient("cheese_bg", "parm", 24, box=((-2.6, 2.6), (1.0, 4.0), (-0.2, 5.0)), s=(0.01, 0.02))
    S.camera_path(cam)
    ST.studio_rig(S.sc, (0, 0.8, 1.0), k=0.42, rim=0.8, top=0.7)
    S.cue(1, "boom")
    S.cue(3, "nom")
    S.cue(48, "meow", pitch=1.05)
    S.cue(97, "purr", dur=0.3)
    S.ov(type="sparkle", t0=46, t1=n)
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
