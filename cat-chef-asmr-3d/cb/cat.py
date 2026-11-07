"""Chef Cat: an original cartoon chef, an orange tabby in a white toque and a
red neckerchief, with rubber-hose arms so its paws can reach anything.

Every part is built procedurally.  `Cat.animate(frames, pose)` keys all parts
from a per-frame pose function returning a dict:

    root   world position of the cat's base      yaw   turn about Z
    bob    body lift (cat units)                  lean  forward lean (rad)
    head   (nod, tilt, turn) Euler                look  world point the eyes aim at
    blink  0..1 (1 = closed)                      open  mouth open 0..1
    tongue 0..1 (licking)                         ears  ear twitch -1..1
    wink   0..1 closes the cat's right eye only
    L / R  (world paw position, world paw Euler); omitted -> resting paw

The cat faces -Y in its own space.  1 cat unit * K = world units.
"""
import math

import bmesh
import bpy
from mathutils import Vector, Matrix, Euler, Quaternion

from . import util as U, models as MD
from .materials import _new, _bsdf, _coords, _noise, _bump, _finish, cached

NECK_Z = 0.95
HEAD_S = 1.15                      # head is drawn 15 % bigger than modelled
SHOULDER = Vector((0.40, -0.10, 0.76))
EYE = Vector((0.22, -0.43, 0.50))
EYE_R = 0.148
MOUTH = Vector((0.0, -0.60, 0.25))


# --------------------------------------------------------------- materials --
@cached
def fur(kind="body"):
    m, nb, out = _new(f"cat_fur_{kind}")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 4.0, 4, 0.55)
    fine, _ = _noise(nb, co, 150.0, 2, 0.6)
    wave = nb.node("ShaderNodeTexWave", {"wave_type": "BANDS",
                                          "bands_direction": "Z" if kind == "body" else "X"})
    nb.set(nb.sock(wave, "Vector"), co)
    nb.set(nb.sock(wave, "Scale"), 3.0 if kind == "body" else 5.0)
    nb.set(nb.sock(wave, "Distortion"), 4.0)
    nb.set(nb.sock(wave, "Detail"), 2.0)
    stripe = nb.smoothstep(0.62, 0.86, nb.out(wave, "Fac"))
    if kind == "head":
        x, y, z = nb.sep(co)
        stripe = nb.mul(stripe, nb.mul(nb.smoothstep(0.62, 0.85, z), nb.smoothstep(0.2, -0.3, y)))
    base = nb.mix_rgb(n1, (0.90, 0.47, 0.15), (0.96, 0.57, 0.22))
    col = nb.mix_rgb(nb.mul(stripe, 0.75), base, (0.66, 0.27, 0.06))
    bs = _bsdf(nb, Base_Color=col, Roughness=0.62, Sheen_Weight=0.8, Sheen_Roughness=0.35,
               Sheen_Tint=(1.0, 0.85, 0.65), Normal=_bump(nb, fine, 0.25, 0.004))
    _finish(nb, out, bs)
    return m


@cached
def cream():
    m, nb, out = _new("cat_cream")
    co = _coords(nb)
    fine, _ = _noise(nb, co, 150.0, 2, 0.6)
    _finish(nb, out, _bsdf(nb, Base_Color=(0.98, 0.92, 0.82), Roughness=0.6, Sheen_Weight=0.8,
                           Sheen_Roughness=0.35, Normal=_bump(nb, fine, 0.2, 0.004)))
    return m


@cached
def flat(name, color, rough=0.45, coat=0.0, emit=0.0):
    m, nb, out = _new(f"cat_{name}")
    kw = dict(Base_Color=color, Roughness=rough, Coat_Weight=coat, Coat_Roughness=0.05)
    if emit:
        kw.update(Emission_Color=color, Emission_Strength=emit)
    _finish(nb, out, _bsdf(nb, **kw))
    return m


@cached
def cloth(color, name):
    m, nb, out = _new(f"cat_cloth_{name}")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 30.0, 3, 0.55)
    weave, _ = _noise(nb, co, 220.0, 1)
    _finish(nb, out, _bsdf(nb, Base_Color=color, Roughness=0.82, Sheen_Weight=0.4,
                           Normal=_bump(nb, nb.add(n1, nb.mul(weave, 0.3)), 0.15, 0.004)))
    return m


@cached
def eye():
    """Glossy amber iris with a big round pupil on the local -Y axis."""
    m, nb, out = _new("cat_eye")
    co = _coords(nb)
    n = nb.vm("NORMALIZE", co)
    x, y, z = nb.sep(n)
    d = nb.m("SQRT", nb.add(nb.mul(x, x), nb.mul(z, z)))
    front = nb.smoothstep(0.1, -0.2, y)
    iris = nb.mix_rgb(nb.smoothstep(0.2, 0.8, d), (1.0, 0.80, 0.30), (0.80, 0.46, 0.08))
    col = nb.mix_rgb(nb.mul(nb.smoothstep(0.78, 0.86, d), front), iris, (0.25, 0.12, 0.03))
    pupil = nb.mul(nb.m("SUBTRACT", 1.0, nb.smoothstep(0.50, 0.54, d)), front)
    col = nb.mix_rgb(pupil, col, (0.01, 0.01, 0.012))
    _finish(nb, out, _bsdf(nb, Base_Color=col, Roughness=0.2, Coat_Weight=1.0, Coat_Roughness=0.02))
    return m


# ---------------------------------------------------------------- geometry --
def _mesh_obj(S, name, bm, mats, parent=None, smooth=True):
    for f in bm.faces:
        f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    o = bpy.data.objects.new(name, me)
    S.coll.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def _sphere(S, name, r, scl, loc, mat, parent, seg=32, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    o = _mesh_obj(S, name, bm, [mat], parent)
    o.location, o.scale, o.rotation_euler = loc, scl, rot
    return o


def _empty(S, name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    S.coll.objects.link(e)
    e.parent = parent
    e.location = loc
    return e


def _curve(S, name, pts, bevel, mat, parent=None, nurbs=True, radii=None):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    cu.resolution_u = 10
    sp = cu.splines.new("NURBS" if nurbs else "POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1.0)
        if radii:
            sp.points[i].radius = radii[i]
    if nurbs:
        sp.order_u = min(4, len(pts))
        sp.use_endpoint_u = True
    cu.materials.append(mat)
    o = bpy.data.objects.new(name, cu)
    S.coll.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def _paw_mesh():
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=1.0,
                                  matrix=Matrix.Diagonal((0.17, 0.19, 0.115, 1.0)))
        for x in (-0.085, 0.0, 0.085):
            bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=0.062,
                                      matrix=Matrix.Translation((x, -0.13 - (0.02 if x == 0 else 0), 0.025)))
        n_fur = len(bm.faces)
        for x, y in ((-0.075, -0.1), (0.0, -0.125), (0.075, -0.1)):
            bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=0.036,
                                      matrix=Matrix.Translation((x, y, -0.098)))
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0,
                                  matrix=Matrix.Translation((0, 0.0, -0.105)) @
                                  Matrix.Diagonal((0.075, 0.06, 0.025, 1.0)))
        for i, f in enumerate(bm.faces):
            f.material_index = 0 if i < n_fur else 1
            f.smooth = True
        me = bpy.data.meshes.new("cat_paw")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(fur("body"))
        me.materials.append(flat("pink", (0.95, 0.52, 0.56), 0.4))
        return me
    return MD._once("cat_paw", mk)


# ------------------------------------------------------------------- cat ----
class Cat:
    def __init__(self, S, prefix="cat", K=1.27, home=(0, 2.3, 0), yaw=0.0):
        self.S, self.K, self.home, self.yaw = S, K, Vector(home), yaw
        n = f"{S.name}_{prefix}"
        FB, FH, CR = fur("body"), fur("head"), cream()
        PINK = flat("pink", (0.95, 0.52, 0.56), 0.4)
        NOSE = flat("nose", (0.92, 0.45, 0.50), 0.3, coat=0.5)
        DARK = flat("dark", (0.06, 0.03, 0.03), 0.5)
        MIN = flat("mouth_in", (0.32, 0.05, 0.06), 0.5)
        WHITE = cloth((0.95, 0.95, 0.93), "white")
        RED = cloth((0.78, 0.07, 0.05), "red")
        HL = flat("highlight", (1.0, 1.0, 1.0), 0.2, emit=4.0)
        WH = flat("whisker", (0.97, 0.95, 0.92), 0.4)
        self.root = _empty(S, n)
        self.root.scale = (K, K, K)
        self.body = _empty(S, n + "_body", self.root)
        prof = [(0, 0), (0.5, 0.0), (0.62, 0.08), (0.67, 0.28), (0.62, 0.52), (0.5, 0.74), (0.34, 0.9), (0.2, 0.99),
                (0, 1.02)]
        me = MD.revolve_mesh(n + "_torso", prof, 48)
        for pl in me.polygons:
            pl.use_smooth = True
        me.materials.append(FB)
        o = bpy.data.objects.new(n + "_torso", me)
        S.coll.objects.link(o)
        o.parent = self.body
        _sphere(S, n + "_belly", 1.0, (0.36, 0.17, 0.38), (0, -0.5, 0.42), CR, self.body)
        for s in (-1, 1):
            _sphere(S, n + f"_foot{s}", 1.0, (0.17, 0.24, 0.11), (s * 0.3, -0.5, 0.07), CR, self.body)
        ring = [(0.33 + 0.075 * math.cos(t), 0.07 * math.sin(t)) for t in [2 * math.pi * k / 16 for k in range(17)]]
        me = MD.revolve_mesh(n + "_scarf", ring, 48, closed=False)
        for pl in me.polygons:
            pl.use_smooth = True
        me.materials.append(RED)
        sc = bpy.data.objects.new(n + "_scarf", me)
        S.coll.objects.link(sc)
        sc.parent = self.body
        sc.location = (0, 0, 0.9)
        sc.scale = (1.0, 1.0, 0.85)
        for s in (-1, 1):
            _sphere(S, n + f"_knot{s}", 1.0, (0.08, 0.05, 0.06), (s * 0.07, -0.37, 0.86), RED, self.body,
                    rot=(0, s * 0.5, 0))
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=3, radius1=0.16, radius2=0.0, depth=0.24,
                              matrix=Matrix.Rotation(math.pi, 4, "X"))
        fl = _mesh_obj(S, n + "_flap", bm, [RED], self.body, smooth=False)
        fl.location, fl.scale, fl.rotation_euler = (0, -0.36, 0.72), (1.0, 0.3, 1.0), (0.25, 0, math.pi / 6)
        bv = fl.modifiers.new("Bevel", "BEVEL")
        bv.width, bv.segments = 0.02, 2
        # ---- head ---------------------------------------------------------
        self.neck = _empty(S, n + "_neck", self.body, (0, 0, NECK_Z))
        self.head = _empty(S, n + "_head", self.neck)
        self.head.scale = (HEAD_S,) * 3
        H = self.head
        _sphere(S, n + "_skull", 0.55, (1.08, 0.95, 0.92), (0, 0, 0.45), FH, H, seg=48)
        for s in (-1, 1):
            _sphere(S, n + f"_cheek{s}", 0.25, (1.1, 0.9, 0.85), (s * 0.25, -0.33, 0.33), FH, H)
            _sphere(S, n + f"_muzzle{s}", 0.16, (1.0, 0.85, 0.8), (s * 0.095, -0.46, 0.29), CR, H)
        _sphere(S, n + "_chin", 0.09, (1.0, 0.9, 0.8), (0, -0.45, 0.19), CR, H)
        _sphere(S, n + "_nose", 0.055, (1.25, 0.75, 0.8), (0, -0.585, 0.385), NOSE, H)
        self.smile = _empty(S, n + "_smile", H, (0, -0.6, 0.27))
        w = [(-0.11, 0.012, -0.0), (-0.055, -0.006, -0.03), (0.0, -0.002, 0.0), (0.055, -0.006, -0.03),
             (0.11, 0.012, 0.0)]
        _curve(S, n + "_mouthline", w, 0.0085, DARK, self.smile)
        _curve(S, n + "_philtrum", [(0, 0.0, 0.08), (0, -0.003, 0.0)], 0.0075, DARK, self.smile, nurbs=False)
        self.mouth = _empty(S, n + "_mouth", H, (0, -0.565, 0.235))
        _sphere(S, n + "_mouth_in", 1.0, (0.085, 0.05, 0.075), (0, 0, 0), MIN, self.mouth)
        self.tongue = _empty(S, n + "_tongue", H, (0, -0.6, 0.2))
        _sphere(S, n + "_tongue_m", 1.0, (0.05, 0.075, 0.022), (0, -0.02, 0), PINK, self.tongue)
        self.eyes = []
        for s in (-1, 1):
            piv = _empty(S, n + f"_eyepiv{s}", H, (s * EYE.x, EYE.y, EYE.z))
            e = _sphere(S, n + f"_eye{s}", EYE_R, (1.0, 0.78, 1.0), (0, 0, 0), eye(), piv)
            e.rotation_mode = "QUATERNION"
            for k, (hx, hz, hr) in enumerate(((-0.05, 0.055, 0.03), (0.04, -0.04, 0.016))):
                hy = -0.78 * math.sqrt(max(0.0, EYE_R ** 2 - hx * hx - hz * hz)) + 0.004
                _sphere(S, n + f"_hl{s}{k}", hr, (1, 0.35, 1), (hx, hy, hz), HL, piv, seg=12)
            self.eyes.append((s, piv, e))
        self.ears = []
        for s in (-1, 1):
            piv = _empty(S, n + f"_earpiv{s}", H, (s * 0.37, 0.03, 0.86))
            piv.rotation_euler = (0, s * 0.42, 0)
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.2, radius2=0.012, depth=0.36,
                                  matrix=Matrix.Translation((0, 0, 0.12)))
            ear = _mesh_obj(S, n + f"_ear{s}", bm, [FH], piv)
            ear.scale = (1.0, 0.5, 1.0)
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.13, radius2=0.008, depth=0.27,
                                  matrix=Matrix.Translation((0, 0, 0.1)))
            inn = _mesh_obj(S, n + f"_earin{s}", bm, [PINK], piv)
            inn.location, inn.scale = (0, -0.06, 0.0), (1.0, 0.35, 1.0)
            self.ears.append((s, piv))
        for s in (-1, 1):
            for k, dz in enumerate((-0.035, 0.0, 0.035)):
                a = Vector((s * 0.17, -0.57, 0.3 + dz))
                b = Vector((s * 0.66, -0.48, 0.33 + dz * 2.6))
                m_ = a.lerp(b, 0.5) + Vector((0, 0, 0.02))
                _curve(S, n + f"_whisk{s}{k}", [a, m_, b], 0.0055, WH, H, radii=[1.0, 0.8, 0.3])
        hat = _empty(S, n + "_hat", H, (0, 0.05, 0.86))
        hat.rotation_euler = (0.14, 0, 0)
        me = MD.revolve_mesh(n + "_band", [(0, 0), (0.335, 0), (0.34, 0.17), (0, 0.17)], 48)
        me.materials.append(WHITE)
        bo = bpy.data.objects.new(n + "_band", me)
        S.coll.objects.link(bo)
        bo.parent = hat
        puff = [(0, 0.14), (0.31, 0.14), (0.42, 0.24), (0.48, 0.38), (0.46, 0.52), (0.37, 0.62), (0.2, 0.67),
                (0, 0.68)]
        me = MD.revolve_mesh(n + "_puff", puff, 64, rfn=lambda th, z: 1 + 0.07 * math.cos(6 * th) * min(1.0, (z - 0.14) * 4))
        for pl in me.polygons:
            pl.use_smooth = True
        me.materials.append(WHITE)
        po = bpy.data.objects.new(n + "_puff", me)
        S.coll.objects.link(po)
        po.parent = hat
        # ---- tail (body space) ------------------------------------------------
        self.tail_pts = [Vector(p) for p in ((0, 0.5, 0.1), (0.25, 0.78, 0.18), (0.42, 0.86, 0.5), (0.38, 0.8, 0.85),
                                             (0.25, 0.72, 1.05))]
        self.tail = _curve(S, n + "_tail", self.tail_pts, 0.075, FB, self.body, radii=[1.0, 0.95, 0.85, 0.75, 0.55])
        # ---- arms (world space) and paws ------------------------------------
        self.arms, self.paws = {}, {}
        for side, s in (("L", -1), ("R", 1)):
            self.arms[side] = _curve(S, n + f"_arm{side}", [(0, 0, 0)] * 4, 0.085 * K, FB)
            pw = bpy.data.objects.new(n + f"_paw{side}", _paw_mesh())
            S.coll.objects.link(pw)
            pw.scale = (K, K, K)
            self.paws[side] = pw

    # ------------------------------------------------------------- matrices ---
    def body_matrix(self, p):
        K = self.K
        root = Vector(p.get("root", self.home))
        yaw = p.get("yaw", self.yaw)
        Mr = Matrix.Translation(root) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Diagonal((K, K, K, 1.0))
        return Mr @ Matrix.Translation((0, 0, p.get("bob", 0.0))) @ \
            Euler((p.get("lean", 0.0), 0, p.get("sway", 0.0))).to_matrix().to_4x4()

    def head_matrix(self, p):
        return self.body_matrix(p) @ Matrix.Translation((0, 0, NECK_Z)) @ \
            Euler(p.get("head", (0, 0, 0))).to_matrix().to_4x4() @ Matrix.Diagonal((HEAD_S,) * 3 + (1.0,))

    def mouth_world(self, p):
        return self.head_matrix(p) @ MOUTH

    def rest_paw(self, p, side):
        s = -1 if side == "L" else 1
        Mb = self.body_matrix(p)
        return Mb @ Vector((s * 0.4, -0.72, 0.16)), (0, 0, p.get("yaw", self.yaw))

    # -------------------------------------------------------------- animate ---
    def animate(self, frames, pose):
        K = self.K
        for f in frames:
            p = pose(f)
            yaw = p.get("yaw", self.yaw)
            U.key(self.root, f, loc=Vector(p.get("root", self.home)), rot=(0, 0, yaw))
            U.key(self.body, f, loc=(0, 0, p.get("bob", 0.0)), rot=(p.get("lean", 0.0), 0, p.get("sway", 0.0)))
            U.key(self.head, f, rot=p.get("head", (0, 0, 0)))
            Mb = self.body_matrix(p)
            Mh = self.head_matrix(p)
            look = p.get("look")
            b = p.get("blink", 0.0)
            wk = p.get("wink", 0.0)
            for s, piv, e in self.eyes:
                bb = max(b, wk) if s < 0 else b
                U.key(piv, f, scl=(1.0, 1.0, max(0.07, 1 - 0.93 * bb)))
                q = Quaternion()
                if look is not None:
                    ew = Mh @ Vector((s * EYE.x, EYE.y, EYE.z))
                    d = (Mh.to_3x3().inverted() @ (Vector(look) - ew)).normalized()
                    q = Vector((0, -1, 0)).rotation_difference(d)
                    if q.angle > 0.55:
                        q = Quaternion(q.axis, 0.55)
                U.key(e, f, quat=q)
            op = p.get("open", 0.0)
            U.key(self.mouth, f, scl=max(1e-3, op))
            U.key(self.smile, f, scl=max(1e-3, 1 - min(1.0, op * 1.6)))
            tg = p.get("tongue", 0.0)
            U.key(self.tongue, f, loc=(0, -0.6 - 0.05 * tg, 0.2 + 0.02 * op), scl=max(1e-3, tg))
            ew_ = p.get("ears", 0.0)
            for s, piv in self.ears:
                U.key(piv, f, rot=(0.18 * ew_, s * (0.42 + 0.12 * ew_), s * 0.1 * ew_))
            ph = p.get("tail", f * 0.12)
            sp = self.tail.data.splines[0]
            for i, tp in enumerate(self.tail_pts):
                k = i / (len(self.tail_pts) - 1)
                off = Vector((0.18 * k * k * math.sin(ph - 1.2 * k), 0.0, 0.05 * k * math.cos(ph * 0.7)))
                sp.points[i].co = (*(tp + off), 1.0)
                sp.points[i].keyframe_insert("co", frame=f)
            for side, s in (("L", -1), ("R", 1)):
                pos, rot = p.get(side) or self.rest_paw(p, side)
                pos = Vector(pos)
                U.key(self.paws[side], f, loc=pos, rot=rot)
                Sw = Mb @ Vector((s * SHOULDER.x, SHOULDER.y, SHOULDER.z))
                dW = Sw - pos
                W = pos + dW.normalized() * 0.1 * K if dW.length > 1e-6 else pos
                L = (W - Sw).length
                out = (Mb.to_3x3() @ Vector((s, 0, 0))).normalized()
                P1 = Sw.lerp(W, 0.33) + out * 0.12 * L + Vector((0, 0, -0.07 * L))
                P2 = Sw.lerp(W, 0.7) + out * 0.07 * L + Vector((0, 0, -0.05 * L))
                spl = self.arms[side].data.splines[0]
                for i, q in enumerate((Sw, P1, P2, W)):
                    spl.points[i].co = (*q, 1.0)
                    spl.points[i].keyframe_insert("co", frame=f)


# ------------------------------------------------------------ pose helpers --
def blinks(f, times, dur=4):
    """Blink value at frame f for blinks starting at the given frames."""
    for t in times:
        if t <= f < t + dur:
            u = (f - t) / dur
            return math.sin(math.pi * u) ** 0.6
    return 0.0


def bump(f, t0, t1, t2, t3):
    """0 -> 1 between t0..t1, hold, 1 -> 0 between t2..t3 (smooth)."""
    return U.smooth(U.seg(f, t0, t1)) * (1 - U.smooth(U.seg(f, t2, t3)))
