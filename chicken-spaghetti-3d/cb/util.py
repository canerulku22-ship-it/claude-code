"""Shared helpers: easing curves, keyframing, a tiny node-graph DSL and a
pinhole projection used to track 3D anchors for the 2D motion graphics."""
import math
import bpy
from mathutils import Vector, Quaternion, Matrix

FPS = 30


# ------------------------------------------------------------------ easing --
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def vlerp(a, b, t):
    return Vector(a).lerp(Vector(b), t)


def seg(f, f0, f1):
    if f1 == f0:
        return 1.0 if f >= f0 else 0.0
    return clamp((f - f0) / float(f1 - f0))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def smoother(t):
    t = clamp(t)
    return t * t * t * (t * (t * 6 - 15) + 10)


def ease_out(t, p=3):
    t = clamp(t)
    return 1 - (1 - t) ** p


def ease_in(t, p=3):
    t = clamp(t)
    return t ** p


def ease_io(t, p=3):
    t = clamp(t)
    return 0.5 * (2 * t) ** p if t < 0.5 else 1 - 0.5 * (2 * (1 - t)) ** p


def ease_back(t, s=1.70158):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_elastic(t, period=0.4):
    t = clamp(t)
    if t in (0.0, 1.0):
        return t
    return 2 ** (-10 * t) * math.sin((t - period / 4) * 2 * math.pi / period) + 1


def impact(ts, freq=3.2, decay=7.0):
    """Damped cosine used for squash after an impact; ts = seconds since hit."""
    if ts < 0:
        return 0.0
    return math.exp(-decay * ts) * math.cos(2 * math.pi * freq * ts)


def squash_scale(amount):
    """Volume-preserving (sx, sy, sz) for vertical squash amount (+ = flatter)."""
    sz = max(0.2, 1.0 - amount)
    sxy = 1.0 / math.sqrt(sz)
    return (sxy, sxy, sz)


# -------------------------------------------------------------- keyframing --
def key(obj, f, loc=None, rot=None, scl=None, quat=None, hide=None):
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert("location", frame=f)
    if rot is not None:
        obj.rotation_euler = rot
        obj.keyframe_insert("rotation_euler", frame=f)
    if quat is not None:
        obj.rotation_quaternion = quat
        obj.keyframe_insert("rotation_quaternion", frame=f)
    if scl is not None:
        if not hasattr(scl, "__len__"):
            scl = (scl, scl, scl)
        obj.scale = scl
        obj.keyframe_insert("scale", frame=f)
    if hide is not None:
        obj.hide_render = hide
        obj.hide_viewport = hide
        obj.keyframe_insert("hide_render", frame=f)
        obj.keyframe_insert("hide_viewport", frame=f)


def animate(obj, frames, fn):
    """fn(f) -> dict(loc=, rot=, scl=, hide=) ; keyed on every frame."""
    for f in frames:
        key(obj, f, **fn(f))


def key_socket(sock, f, v):
    sock.default_value = v
    sock.keyframe_insert("default_value", frame=f)


def key_prop(owner, prop, f, v):
    setattr(owner, prop, v)
    owner.keyframe_insert(prop, frame=f)


def set_linear_keys():
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"


# ------------------------------------------------------------- node DSL -----
def to_lin(c):
    """sRGB (display) colour -> linear (what Blender stores)."""
    def f(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    c = tuple(c)
    return tuple(f(x) for x in c[:3]) + c[3:]


class NB:
    """Minimal helper to build shader / geometry node graphs from Python.
    With srgb=True literal colours on colour sockets / ramps are given in
    sRGB and converted to linear."""

    def __init__(self, tree, srgb=False):
        self.srgb = srgb
        self.tree = tree
        self.nodes = tree.nodes
        self.links = tree.links
        self._x = 0

    @staticmethod
    def sock(node, key, out=False):
        coll = node.outputs if out else node.inputs
        if isinstance(key, int):
            return coll[key]
        cands = [s for s in coll if s.name == key or s.identifier == key]
        en = [s for s in cands if getattr(s, "enabled", True) and not getattr(s, "hide", False)]
        if en:
            return en[0]
        if cands:
            return cands[0]
        raise KeyError(f"{node.bl_idname} has no socket {key!r}: {[s.name for s in coll]}")

    def set(self, sock, v):
        if v is None:
            return
        if isinstance(v, bpy.types.NodeSocket):
            self.links.new(v, sock)
            return
        if isinstance(v, bpy.types.Node):
            self.links.new(v.outputs[0], sock)
            return
        dv = sock.default_value
        if self.srgb and sock.type == "RGBA" and hasattr(v, "__len__"):
            v = to_lin(v)
        if hasattr(dv, "__len__") and not isinstance(v, (str, bpy.types.ID)):
            if not hasattr(v, "__len__"):
                v = [v] * len(dv)
            v = list(v)
            if len(v) == 3 and len(dv) == 4:
                v = v + [1.0]
            sock.default_value = v[: len(dv)]
        else:
            sock.default_value = v

    def node(self, bl_idname, props=None, **inputs):
        n = self.nodes.new(bl_idname)
        n.location = (self._x, 0)
        self._x += 40
        for k, v in (props or {}).items():
            setattr(n, k, v)
        for k, v in inputs.items():
            self.set(self.sock(n, k.replace("__", " ")), v)
        return n

    def out(self, node, key=0):
        return self.sock(node, key, out=True)

    # math -------------------------------------------------------------
    def m(self, op, a, b=None, c=None, clamp_=False):
        n = self.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp_
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        if c is not None:
            self.set(n.inputs[2], c)
        return n.outputs[0]

    def add(self, a, b): return self.m("ADD", a, b)
    def sub(self, a, b): return self.m("SUBTRACT", a, b)
    def mul(self, a, b): return self.m("MULTIPLY", a, b)
    def div(self, a, b): return self.m("DIVIDE", a, b)
    def mx(self, a, b): return self.m("MAXIMUM", a, b)
    def mn(self, a, b): return self.m("MINIMUM", a, b)
    def clamp01(self, a): return self.m("ADD", a, 0.0, clamp_=True)

    def vm(self, op, a, b=None, scale=None):
        n = self.nodes.new("ShaderNodeVectorMath")
        n.operation = op
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        if scale is not None:
            self.set(self.sock(n, "Scale"), scale)
        if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE"):
            return self.sock(n, "Value", out=True)
        return self.sock(n, "Vector", out=True)

    def vadd(self, a, b): return self.vm("ADD", a, b)
    def vscale(self, a, s): return self.vm("SCALE", a, scale=s)
    def vmul(self, a, b): return self.vm("MULTIPLY", a, b)

    def xyz(self, x=0.0, y=0.0, z=0.0):
        return self.out(self.node("ShaderNodeCombineXYZ", X=x, Y=y, Z=z))

    def sep(self, v):
        n = self.node("ShaderNodeSeparateXYZ", Vector=v)
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def mix_rgb(self, fac, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", {"data_type": "RGBA", "blend_type": blend})
        self.set(self.sock(n, "Factor"), fac)
        self.set(self.sock(n, "A"), a)
        self.set(self.sock(n, "B"), b)
        return self.sock(n, "Result", out=True)

    def mixf(self, fac, a, b):
        n = self.node("ShaderNodeMix", {"data_type": "FLOAT"})
        self.set(self.sock(n, "Factor"), fac)
        self.set(self.sock(n, "A"), a)
        self.set(self.sock(n, "B"), b)
        return self.sock(n, "Result", out=True)

    def ramp(self, fac, stops, interp="LINEAR"):
        """stops: list of (pos, (r,g,b[,a]))"""
        n = self.node("ShaderNodeValToRGB")
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > len(stops):
            cr.elements.remove(cr.elements[-1])
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for el, (p, c) in zip(cr.elements, stops):
            el.position = p
            c = tuple(c) + ((1.0,) if len(c) == 3 else ())
            el.color = to_lin(c) if self.srgb else c
        self.set(n.inputs[0], fac)
        return n.outputs[0]

    def smoothstep(self, e0, e1, x):
        n = self.node("ShaderNodeMapRange", {"interpolation_type": "SMOOTHSTEP"})
        self.set(self.sock(n, "Value"), x)
        self.set(self.sock(n, "From Min"), e0)
        self.set(self.sock(n, "From Max"), e1)
        return self.sock(n, "Result", out=True)

    def value(self, v, label=None):
        n = self.node("ShaderNodeValue")
        n.outputs[0].default_value = v
        if label:
            n.label = label
            n.name = label
        return n


# ---------------------------------------------------------- projection -----
class CamTrack:
    """Per-frame camera record so overlay anchors can be projected exactly."""

    def __init__(self, cam_obj, res=(1080, 1920)):
        self.cam = cam_obj
        self.res = res
        self.frames = {}

    def set(self, f, loc, target, lens, roll=0.0, focus=None):
        loc = Vector(loc)
        target = Vector(target)
        d = target - loc
        q = d.to_track_quat("-Z", "Y")
        if roll:
            q = q @ Quaternion((0, 0, 1), roll)
        prev = self.frames.get(f - 1)
        if prev is not None and prev[1].dot(q) < 0:
            q.negate()
        self.frames[f] = (loc.copy(), q.copy(), lens)
        key(self.cam, f, loc=loc, quat=q)
        key_prop(self.cam.data, "lens", f, lens)
        fd = d.length if focus is None else focus
        key_prop(self.cam.data.dof, "focus_distance", f, fd)

    def project(self, f, p):
        loc, q, lens = self.frames[f]
        m = (Matrix.Translation(loc) @ q.to_matrix().to_4x4()).inverted()
        pc = m @ Vector(p)
        z = -pc.z
        if z <= 1e-4:
            return None
        W, H = self.res
        k = lens / self.cam.data.sensor_height
        u = 0.5 + (pc.x / z) * k * (H / W)
        v = 0.5 + (pc.y / z) * k
        return (u * W, (1 - v) * H, z)
