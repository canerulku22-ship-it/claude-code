"""Procedural CGI food and prop materials (Cycles)."""
import bpy
from .util import NB

_cache = {}


def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    nb = NB(nt, srgb=True)
    out = nb.node("ShaderNodeOutputMaterial")
    return m, nb, out


def _bsdf(nb, **kw):
    n = nb.node("ShaderNodeBsdfPrincipled")
    n.subsurface_method = "BURLEY"   # much cheaper than random walk on CPU
    for k, v in kw.items():
        nb.set(nb.sock(n, k.replace("_", " ")), v)
    return n


def _coords(nb, kind="Object"):
    return nb.out(nb.node("ShaderNodeTexCoord"), kind)


def _noise(nb, vec, scale, detail=4.0, rough=0.5, distortion=0.0, w=None, dims="3D"):
    n = nb.node("ShaderNodeTexNoise", {"noise_dimensions": dims if w is None else "4D"})
    nb.set(nb.sock(n, "Vector"), vec)
    nb.set(nb.sock(n, "Scale"), scale)
    nb.set(nb.sock(n, "Detail"), detail)
    nb.set(nb.sock(n, "Roughness"), rough)
    nb.set(nb.sock(n, "Distortion"), distortion)
    if w is not None:
        nb.set(nb.sock(n, "W"), w)
    return n.outputs[0], n.outputs[1]


def _voronoi(nb, vec, scale, feature="F1", rnd=1.0):
    n = nb.node("ShaderNodeTexVoronoi", {"feature": feature})
    nb.set(nb.sock(n, "Vector"), vec)
    nb.set(nb.sock(n, "Scale"), scale)
    nb.set(nb.sock(n, "Randomness"), rnd)
    return nb.sock(n, "Distance", out=True)


def _bump(nb, height, strength=0.3, distance=0.02, normal=None):
    n = nb.node("ShaderNodeBump")
    nb.set(nb.sock(n, "Height"), height)
    nb.set(nb.sock(n, "Strength"), strength)
    nb.set(nb.sock(n, "Distance"), distance)
    if normal is not None:
        nb.set(nb.sock(n, "Normal"), normal)
    return nb.sock(n, "Normal", out=True)


def _attr(nb, name, kind="GEOMETRY"):
    n = nb.node("ShaderNodeAttribute", {"attribute_type": kind, "attribute_name": name})
    return n.outputs[2]


def _finish(nb, out, shader):
    nb.set(nb.sock(out, "Surface"), nb.out(shader) if isinstance(shader, bpy.types.Node) else shader)


def cached(fn):
    def w(*a, **k):
        key = (fn.__name__,) + a + tuple(sorted(k.items()))
        if key not in _cache:
            _cache[key] = fn(*a, **k)
        return _cache[key]
    return w


# --------------------------------------------------------------- chicken ---
def chicken(name):
    """Animated chicken material.  Returns (material, {param: value_node}).

    season 0..1  spice flecks appear
    wet    0..1  egg-wash gloss
    coat   0..1  flour dredge (pale, matte; GN crust displacement in sync)
    fry    0..1  pale -> golden -> deep golden brown, oily sheen
    """
    m, nb, out = _new(name)
    p = {k: nb.value(0.0, k) for k in ("season", "wet", "coat", "fry")}
    S, W, C, F = (nb.out(p[k]) for k in ("season", "wet", "coat", "fry"))
    co = _coords(nb)
    crag = _attr(nb, "crag")
    n1, _ = _noise(nb, co, 7.0, 5, 0.55)
    n2, _ = _noise(nb, co, 40.0, 3, 0.6)

    # raw breast meat with subtle fibre streaks
    wave = nb.node("ShaderNodeTexWave", {"wave_type": "BANDS", "bands_direction": "X"})
    nb.set(nb.sock(wave, "Vector"), co)
    nb.set(nb.sock(wave, "Scale"), 6.0)
    nb.set(nb.sock(wave, "Distortion"), 14.0)
    nb.set(nb.sock(wave, "Detail"), 6.0)
    nb.set(nb.sock(wave, "Detail Roughness"), 0.7)
    fib = nb.mul(wave.outputs[1], nb.smoothstep(0.3, 0.7, n1))
    raw = nb.mix_rgb(n1, (0.95, 0.66, 0.60), (0.88, 0.52, 0.48))
    raw = nb.mix_rgb(nb.mul(fib, 0.18), raw, (0.97, 0.72, 0.66))

    # seasoning flecks (paprika + pepper)
    sp1 = nb.m("LESS_THAN", _voronoi(nb, co, 55.0), 0.16)
    sp2 = nb.m("LESS_THAN", _voronoi(nb, nb.vadd(co, (3.1, 1.7, 0.2)), 75.0), 0.12)
    seasoned = nb.mix_rgb(nb.mul(sp1, S), raw, (0.62, 0.16, 0.03))
    seasoned = nb.mix_rgb(nb.mul(sp2, S), seasoned, (0.06, 0.035, 0.02))
    seasoned = nb.mix_rgb(nb.mul(S, 0.25), seasoned, (0.85, 0.40, 0.22))
    # egg wash tint
    seasoned = nb.mix_rgb(nb.mul(W, 0.35), seasoned, (0.96, 0.70, 0.28))

    # coating -> frying colour ramp driven by a browning value
    vary = nb.add(nb.mul(crag, 0.28), nb.mul(nb.sub(n1, 0.5), 0.3))
    brown = nb.mul(F, nb.add(0.66, vary))
    fried = nb.ramp(brown, [(0.0, (0.95, 0.93, 0.88)), (0.22, (0.94, 0.84, 0.58)),
                            (0.45, (0.92, 0.70, 0.33)), (0.65, (0.84, 0.57, 0.22)),
                            (0.85, (0.73, 0.45, 0.15)), (1.05, (0.58, 0.33, 0.10))])
    # flour flecks of seasoning still show through the coating
    fried = nb.mix_rgb(nb.mul(nb.mul(sp1, S), nb.m("SUBTRACT", 1.0, F)), fried, (0.86, 0.52, 0.32))
    # crevices a touch darker, ridges catch more colour
    fried = nb.mix_rgb(nb.mul(nb.m("SUBTRACT", 1.0, crag), nb.mul(F, 0.35)), fried, (0.72, 0.58, 0.42), "MULTIPLY")
    col = nb.mix_rgb(C, seasoned, fried)

    rough_raw = nb.mixf(W, 0.34, 0.12)
    rough_coat = nb.mixf(F, 0.95, nb.mixf(crag, 0.62, 0.42))
    rough = nb.mixf(C, rough_raw, rough_coat)
    coat_w = nb.add(nb.mul(nb.mul(W, 0.8), nb.m("SUBTRACT", 1.0, C)), nb.mul(nb.mul(F, crag), 0.18))
    sss = nb.add(nb.mul(nb.m("SUBTRACT", 1.0, C), 0.3), nb.mul(F, 0.03))
    h = nb.add(nb.mul(n2, nb.add(0.15, nb.mul(C, 0.6))), nb.mul(fib, nb.mul(nb.m("SUBTRACT", 1.0, C), 0.12)))
    nrm = _bump(nb, h, 0.4, 0.006)
    bs = _bsdf(nb, Base_Color=col, Roughness=rough, Coat_Weight=coat_w, Coat_Roughness=0.15,
               Subsurface_Weight=sss, Subsurface_Radius=(1.0, 0.45, 0.25), Subsurface_Scale=0.03,
               Sheen_Weight=nb.mul(C, nb.m("SUBTRACT", 1.0, F)), Normal=nrm)
    _finish(nb, out, bs)
    return m, p


# ------------------------------------------------------------- particles ---
@cached
def spice():
    m, nb, out = _new("spice")
    r = nb.out(nb.node("ShaderNodeObjectInfo"), "Random")
    col = nb.ramp(r, [(0.0, (0.05, 0.03, 0.02)), (0.3, (0.05, 0.03, 0.02)), (0.31, (0.60, 0.14, 0.03)),
                      (0.75, (0.75, 0.25, 0.05)), (0.76, (0.80, 0.55, 0.20)), (1.0, (0.80, 0.55, 0.2))],
                  "CONSTANT")
    _finish(nb, out, _bsdf(nb, Base_Color=col, Roughness=0.7))
    return m


@cached
def droplet(color=(0.80, 0.52, 0.12)):
    m, nb, out = _new("droplet")
    _finish(nb, out, _bsdf(nb, Base_Color=color, Roughness=0.03, Coat_Weight=1.0, Coat_Roughness=0.0,
                           Specular_IOR_Level=1.0))
    return m


@cached
def steam():
    """Soft sprite: alpha from radial falloff * animated noise * instance age."""
    m, nb, out = _new("steam")
    co = _coords(nb)
    rnd = nb.out(nb.node("ShaderNodeObjectInfo"), "Random")
    u = _attr(nb, "u", "INSTANCER")
    x, y, _ = nb.sep(co)
    r = nb.m("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    fall = nb.m("SUBTRACT", 1.0, nb.smoothstep(0.08, 0.5, r))
    n1, _ = _noise(nb, nb.vscale(co, 1.0), 2.5, 5, 0.6, distortion=0.6, w=nb.add(nb.mul(rnd, 10.0), nb.mul(u, 1.5)))
    wisp = nb.smoothstep(0.42, 0.75, n1)
    life = nb.m("SINE", nb.mul(u, 3.14159))
    a = nb.mul(nb.mul(nb.mul(fall, wisp), life), 0.32)
    tr = nb.node("ShaderNodeBsdfTransparent")
    # emission-only: no light sampling per transparent layer (cheap on CPU)
    df = nb.node("ShaderNodeEmission")
    nb.set(nb.sock(df, "Color"), (1.0, 0.94, 0.86))
    nb.set(nb.sock(df, "Strength"), 0.55)
    mix = nb.node("ShaderNodeMixShader")
    nb.set(mix.inputs[0], a)
    nb.links.new(tr.outputs[0], mix.inputs[1])
    nb.links.new(df.outputs[0], mix.inputs[2])
    _finish(nb, out, mix)
    return m


# ---------------------------------------------------------------- props ----
@cached
def wood():
    m, nb, out = _new("wood")
    co = _coords(nb)
    grain, _ = _noise(nb, nb.vmul(co, (0.5, 16.0, 0.5)), 2.0, 6, 0.62, distortion=1.4)
    n1, _ = _noise(nb, co, 3.0, 4)
    g = nb.add(nb.mul(grain, 0.75), nb.mul(n1, 0.25))
    col = nb.ramp(g, [(0.25, (0.42, 0.24, 0.12)), (0.5, (0.58, 0.37, 0.20)), (0.75, (0.70, 0.50, 0.30))])
    _finish(nb, out, _bsdf(nb, Base_Color=col, Roughness=0.55, Coat_Weight=0.1,
                           Normal=_bump(nb, grain, 0.08, 0.01)))
    return m


@cached
def slate():
    m, nb, out = _new("slate")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 3.0, 6, 0.6)
    n2, _ = _noise(nb, co, 60.0, 2)
    col = nb.mix_rgb(n1, (0.10, 0.098, 0.096), (0.17, 0.16, 0.15))
    _finish(nb, out, _bsdf(nb, Base_Color=col, Roughness=nb.add(0.38, nb.mul(n1, 0.3)),
                           Normal=_bump(nb, n2, 0.08, 0.01)))
    return m


@cached
def stoneware(color=(0.23, 0.21, 0.20)):
    m, nb, out = _new("stoneware")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 40.0, 3)
    _finish(nb, out, _bsdf(nb, Base_Color=color, Roughness=0.55, Coat_Weight=0.12, Coat_Roughness=0.3,
                           Normal=_bump(nb, n1, 0.08, 0.01)))
    return m


@cached
def cast_iron():
    m, nb, out = _new("cast_iron")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 30.0, 5)
    _finish(nb, out, _bsdf(nb, Base_Color=(0.14, 0.14, 0.15), Metallic=0.6, Roughness=nb.add(0.35, nb.mul(n1, 0.2)),
                           Normal=_bump(nb, n1, 0.2, 0.01)))
    return m


@cached
def steel():
    m, nb, out = _new("steel")
    _finish(nb, out, _bsdf(nb, Base_Color=(0.85, 0.85, 0.86), Metallic=1.0, Roughness=0.22))
    return m


@cached
def shaker_cap():
    m, nb, out = _new("shaker_cap")
    co = _coords(nb)
    holes = nb.m("LESS_THAN", _voronoi(nb, co, 30.0, rnd=0.0), 0.12)
    col = nb.mix_rgb(holes, (0.8, 0.8, 0.82), (0.02, 0.02, 0.02))
    _finish(nb, out, _bsdf(nb, Base_Color=col, Metallic=nb.m("SUBTRACT", 1.0, holes), Roughness=0.28))
    return m


@cached
def plastic(color, rough=0.3):
    m, nb, out = _new("plastic")
    _finish(nb, out, _bsdf(nb, Base_Color=color, Roughness=rough, Coat_Weight=0.4, Coat_Roughness=0.1,
                           Subsurface_Weight=0.15, Subsurface_Radius=(1, 0.7, 0.5), Subsurface_Scale=0.02))
    return m


@cached
def oil():
    m, nb, out = _new("oil")
    co = _coords(nb)
    _, _, z = nb.sep(co)
    x, y, _ = nb.sep(co)
    r = nb.m("SQRT", nb.add(nb.mul(x, x), nb.mul(y, y)))
    col = nb.mix_rgb(nb.smoothstep(0.2, 0.9, r), (0.40, 0.27, 0.08), (0.20, 0.13, 0.04))
    _finish(nb, out, _bsdf(nb, Base_Color=col, Roughness=0.03, Specular_IOR_Level=1.0, Coat_Weight=0.8,
                           Coat_Roughness=0.01))
    return m


@cached
def text_mat(kind):
    m, nb, out = _new("text_" + kind)
    if kind == "gold":
        bs = _bsdf(nb, Base_Color=(1.0, 0.74, 0.22), Metallic=0.55, Roughness=0.28, Coat_Weight=0.4,
                   Emission_Color=(1.0, 0.70, 0.20), Emission_Strength=0.55)
    elif kind == "red":
        bs = _bsdf(nb, Base_Color=(0.80, 0.07, 0.03), Roughness=0.3, Coat_Weight=0.6, Coat_Roughness=0.05)
    else:
        bs = _bsdf(nb, Base_Color=(1.0, 0.94, 0.84), Roughness=0.35, Coat_Weight=0.3,
                   Emission_Color=(1.0, 0.94, 0.84), Emission_Strength=0.15)
    _finish(nb, out, bs)
    return m


# ---------------------------------------------------------------- pasta ----
def pasta(name):
    """Spaghetti.  Returns (material, {param: value_node}).

    cook   0..1  dry, translucent golden -> cooked, soft creamy and wet
    sauce  0..1  tomato sauce spreads over the strands in organic patches
    """
    m, nb, out = _new(name)
    p = {k: nb.value(0.0, k) for k in ("cook", "sauce")}
    K, S = nb.out(p["cook"]), nb.out(p["sauce"])
    co = _coords(nb)
    n1, _ = _noise(nb, co, 9.0, 3, 0.5)
    n2, _ = _noise(nb, co, 7.0, 4, 0.55)
    dry = nb.mix_rgb(n1, (0.93, 0.74, 0.38), (0.98, 0.84, 0.50))
    cooked = nb.mix_rgb(n1, (0.95, 0.80, 0.50), (0.99, 0.89, 0.64))
    col = nb.mix_rgb(K, dry, cooked)
    # sauce coverage grows from the noise valleys outwards
    cov = nb.smoothstep(-0.12, 0.12, nb.sub(nb.mul(S, 1.25), n2))
    sc = nb.mix_rgb(n1, (0.52, 0.08, 0.02), (0.70, 0.17, 0.04))
    herb = nb.m("LESS_THAN", _voronoi(nb, nb.vscale(co, 1.0), 60.0), 0.05)
    sc = nb.mix_rgb(nb.mul(herb, 0.85), sc, (0.12, 0.20, 0.04))
    col = nb.mix_rgb(cov, col, sc)
    rough = nb.mixf(cov, nb.mixf(K, 0.42, 0.26), 0.16)
    bs = _bsdf(nb, Base_Color=col, Roughness=rough, Coat_Weight=nb.add(nb.mul(K, 0.35), nb.mul(cov, 0.45)),
               Coat_Roughness=0.08, Subsurface_Weight=nb.mixf(cov, 0.35, 0.15),
               Subsurface_Radius=(1.0, 0.75, 0.35), Subsurface_Scale=0.015,
               Normal=_bump(nb, n1, 0.08, 0.004))
    _finish(nb, out, bs)
    return m, p


@cached
def tomato_sauce():
    m, nb, out = _new("tomato_sauce")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 5.0, 5, 0.6)
    n2, _ = _noise(nb, co, 22.0, 3, 0.5)
    chunk = nb.smoothstep(0.55, 0.7, n2)
    col = nb.mix_rgb(n1, (0.46, 0.05, 0.015), (0.66, 0.13, 0.03))
    col = nb.mix_rgb(nb.mul(chunk, 0.6), col, (0.74, 0.22, 0.05))
    herb = nb.m("LESS_THAN", _voronoi(nb, co, 34.0), 0.07)
    col = nb.mix_rgb(nb.mul(herb, 0.9), col, (0.10, 0.17, 0.03))
    oilsheen = nb.smoothstep(0.62, 0.75, n1)
    col = nb.mix_rgb(nb.mul(oilsheen, 0.35), col, (0.90, 0.38, 0.06))
    bs = _bsdf(nb, Base_Color=col, Roughness=nb.mixf(chunk, 0.3, 0.5), Coat_Weight=0.3, Coat_Roughness=0.12,
               Subsurface_Weight=0.25, Subsurface_Radius=(1.0, 0.25, 0.1), Subsurface_Scale=0.02,
               Normal=_bump(nb, nb.add(n2, nb.mul(chunk, 0.8)), 0.25, 0.01))
    _finish(nb, out, bs)
    return m


def seared_chicken(name):
    """Chicken cubes.  Returns (material, {param: value_node}).

    season 0..1  paprika dusting, herb and pepper flecks
    sear   0..1  raw pink -> golden -> deep caramelised edges (pointiness)
    sauce  0..1  tomato glaze in patches
    """
    m, nb, out = _new(name)
    p = {k: nb.value(0.0, k) for k in ("season", "sear", "sauce")}
    S, R, Q = (nb.out(p[k]) for k in ("season", "sear", "sauce"))
    co = _coords(nb)
    n1, _ = _noise(nb, co, 6.0, 5, 0.55)
    n2, _ = _noise(nb, co, 30.0, 3, 0.6)
    geo = nb.node("ShaderNodeNewGeometry")
    edge = nb.smoothstep(0.5, 0.58, nb.sock(geo, "Pointiness", out=True))
    raw = nb.mix_rgb(n1, (0.96, 0.70, 0.64), (0.90, 0.56, 0.52))
    dust = nb.mix_rgb(n2, (0.86, 0.42, 0.20), (0.92, 0.55, 0.30))
    col = nb.mix_rgb(nb.mul(S, 0.8), raw, dust)
    fl1 = nb.m("LESS_THAN", _voronoi(nb, co, 70.0), 0.12)
    fl2 = nb.m("LESS_THAN", _voronoi(nb, nb.vadd(co, (2.3, 0.7, 1.1)), 90.0), 0.10)
    col = nb.mix_rgb(nb.mul(fl1, S), col, (0.16, 0.24, 0.06))
    col = nb.mix_rgb(nb.mul(fl2, S), col, (0.05, 0.035, 0.025))
    br = nb.mul(R, nb.add(0.55, nb.add(nb.mul(edge, 0.45), nb.mul(nb.sub(n1, 0.5), 0.4))))
    seared = nb.ramp(br, [(0.0, (0.94, 0.80, 0.66)), (0.3, (0.90, 0.64, 0.36)), (0.55, (0.78, 0.47, 0.20)),
                          (0.8, (0.62, 0.33, 0.11)), (1.05, (0.42, 0.20, 0.06))])
    seared = nb.mix_rgb(nb.mul(nb.mul(fl2, S), 0.9), seared, (0.06, 0.04, 0.03))
    col = nb.mix_rgb(nb.smoothstep(0.0, 0.35, R), col, seared)
    cov = nb.smoothstep(-0.1, 0.1, nb.sub(nb.mul(Q, 1.2), n1))
    col = nb.mix_rgb(cov, col, (0.56, 0.10, 0.03))
    rough = nb.mixf(R, 0.32, 0.5)
    rough = nb.mixf(cov, rough, 0.2)
    bs = _bsdf(nb, Base_Color=col, Roughness=rough, Coat_Weight=nb.add(nb.mul(R, 0.25), nb.mul(cov, 0.4)),
               Coat_Roughness=0.15, Subsurface_Weight=nb.mixf(R, 0.3, 0.05),
               Subsurface_Radius=(1.0, 0.45, 0.25), Subsurface_Scale=0.02,
               Normal=_bump(nb, nb.add(n2, nb.mul(n1, 0.5)), 0.3, 0.006))
    _finish(nb, out, bs)
    return m, p


# --------------------------------------------------------------- produce ---
@cached
def garlic_skin():
    m, nb, out = _new("garlic_skin")
    co = _coords(nb)
    wave = nb.node("ShaderNodeTexWave", {"wave_type": "BANDS", "bands_direction": "Z"})
    nb.set(nb.sock(wave, "Vector"), co)
    nb.set(nb.sock(wave, "Scale"), 4.0)
    nb.set(nb.sock(wave, "Distortion"), 6.0)
    n1, _ = _noise(nb, co, 12.0, 4)
    col = nb.mix_rgb(nb.mul(nb.smoothstep(0.6, 0.9, wave.outputs[1]), 0.6), (0.95, 0.91, 0.85), (0.78, 0.60, 0.68))
    _finish(nb, out, _bsdf(nb, Base_Color=col, Roughness=0.45, Sheen_Weight=0.4, Subsurface_Weight=0.3,
                           Subsurface_Radius=(1, 0.9, 0.7), Subsurface_Scale=0.02, Normal=_bump(nb, n1, 0.15, 0.005)))
    return m


@cached
def garlic_flesh():
    m, nb, out = _new("garlic_flesh")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 40.0, 3)
    _finish(nb, out, _bsdf(nb, Base_Color=nb.mix_rgb(n1, (0.97, 0.92, 0.74), (0.94, 0.86, 0.62)), Roughness=0.35,
                           Subsurface_Weight=0.45, Subsurface_Radius=(1, 0.9, 0.6), Subsurface_Scale=0.02))
    return m


@cached
def onion_skin():
    m, nb, out = _new("onion_skin")
    co = _coords(nb)
    wave = nb.node("ShaderNodeTexWave", {"wave_type": "BANDS", "bands_direction": "Z"})
    nb.set(nb.sock(wave, "Vector"), co)
    nb.set(nb.sock(wave, "Scale"), 7.0)
    nb.set(nb.sock(wave, "Distortion"), 4.0)
    n1, _ = _noise(nb, co, 5.0, 4)
    col = nb.ramp(nb.add(nb.mul(wave.outputs[1], 0.35), nb.mul(n1, 0.65)),
                  [(0.2, (0.86, 0.58, 0.30)), (0.55, (0.74, 0.44, 0.18)), (0.85, (0.56, 0.30, 0.12))])
    _finish(nb, out, _bsdf(nb, Base_Color=col, Roughness=0.38, Coat_Weight=0.25, Coat_Roughness=0.2,
                           Normal=_bump(nb, wave.outputs[1], 0.08, 0.005)))
    return m


@cached
def onion_flesh():
    m, nb, out = _new("onion_flesh")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 15.0, 2)
    _finish(nb, out, _bsdf(nb, Base_Color=nb.mix_rgb(n1, (0.96, 0.94, 0.86), (0.93, 0.90, 0.78)), Roughness=0.2,
                           Coat_Weight=0.4, Coat_Roughness=0.05, Subsurface_Weight=0.6,
                           Subsurface_Radius=(1, 1, 0.8), Subsurface_Scale=0.02))
    return m


@cached
def basil():
    m, nb, out = _new("basil")
    co = _coords(nb)
    rad = _attr(nb, "rad")
    n1, _ = _noise(nb, co, 14.0, 4, 0.6)
    vein = nb.m("SUBTRACT", 1.0, nb.smoothstep(0.0, 0.08, nb.m("ABSOLUTE", _attr(nb, "vx"))))
    col = nb.ramp(nb.add(nb.mul(rad, 0.5), nb.mul(n1, 0.5)),
                  [(0.1, (0.22, 0.50, 0.10)), (0.5, (0.13, 0.40, 0.06)), (0.9, (0.08, 0.30, 0.04))])
    col = nb.mix_rgb(nb.mul(vein, 0.5), col, (0.40, 0.62, 0.20))
    bs = _bsdf(nb, Base_Color=col, Roughness=0.3, Coat_Weight=0.3, Coat_Roughness=0.1, Subsurface_Weight=0.2,
               Subsurface_Radius=(0.4, 1.0, 0.2), Subsurface_Scale=0.01, Normal=_bump(nb, nb.add(n1, vein), 0.2, 0.004))
    tr = nb.node("ShaderNodeBsdfTranslucent")
    nb.set(nb.sock(tr, "Color"), col)
    mix = nb.node("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.15
    nb.links.new(bs.outputs[0], mix.inputs[1])
    nb.links.new(tr.outputs[0], mix.inputs[2])
    _finish(nb, out, mix)
    return m


@cached
def parmesan(rind=False):
    m, nb, out = _new("parmesan_rind" if rind else "parmesan")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 8.0, 4)
    crumbs = _voronoi(nb, co, 45.0)
    if rind:
        col = nb.mix_rgb(n1, (0.82, 0.60, 0.26), (0.70, 0.48, 0.18))
    else:
        col = nb.mix_rgb(n1, (0.99, 0.91, 0.64), (0.96, 0.84, 0.52))
    _finish(nb, out, _bsdf(nb, Base_Color=col, Roughness=0.6, Subsurface_Weight=0.25,
                           Subsurface_Radius=(1, 0.85, 0.5), Subsurface_Scale=0.015,
                           Normal=_bump(nb, nb.add(crumbs, nb.mul(n1, 0.5)), 0.35, 0.006)))
    return m


@cached
def herb():
    m, nb, out = _new("herb")
    r = nb.out(nb.node("ShaderNodeObjectInfo"), "Random")
    col = nb.ramp(r, [(0.0, (0.10, 0.22, 0.04)), (0.6, (0.20, 0.34, 0.08)), (0.61, (0.55, 0.12, 0.03)),
                      (1.0, (0.70, 0.18, 0.04))], "CONSTANT")
    _finish(nb, out, _bsdf(nb, Base_Color=col, Roughness=0.6))
    return m


@cached
def salt():
    m, nb, out = _new("salt")
    _finish(nb, out, _bsdf(nb, Base_Color=(0.98, 0.98, 0.97), Roughness=0.15, Transmission_Weight=0.5, IOR=1.54))
    return m


# ------------------------------------------------------------ tableware ----
@cached
def ceramic(color=(0.80, 0.79, 0.76)):
    m, nb, out = _new("ceramic")
    co = _coords(nb)
    n1, _ = _noise(nb, co, 30.0, 2)
    _finish(nb, out, _bsdf(nb, Base_Color=color, Roughness=0.22, Coat_Weight=0.5, Coat_Roughness=0.05,
                           Subsurface_Weight=0.05, Subsurface_Radius=(1, 1, 1), Subsurface_Scale=0.01,
                           Normal=_bump(nb, n1, 0.02, 0.005)))
    return m


@cached
def brushed_steel():
    m, nb, out = _new("brushed_steel")
    co = _coords(nb)
    n1, _ = _noise(nb, nb.vmul(co, (1.0, 1.0, 40.0)), 3.0, 3)
    _finish(nb, out, _bsdf(nb, Base_Color=(0.86, 0.86, 0.87), Metallic=1.0, Roughness=nb.add(0.3, nb.mul(n1, 0.08))))
    return m


@cached
def water():
    m, nb, out = _new("water")
    _finish(nb, out, _bsdf(nb, Base_Color=(0.95, 0.97, 1.0), Roughness=0.04, Transmission_Weight=1.0, IOR=1.33))
    return m


@cached
def glass(color=(0.86, 0.94, 0.75)):
    m, nb, out = _new("glass")
    _finish(nb, out, _bsdf(nb, Base_Color=color, Roughness=0.02, Transmission_Weight=1.0, IOR=1.5,
                           Coat_Weight=0.5, Coat_Roughness=0.0))
    return m


@cached
def olive_oil():
    m, nb, out = _new("olive_oil")
    _finish(nb, out, _bsdf(nb, Base_Color=(0.96, 0.80, 0.22), Roughness=0.05, Transmission_Weight=0.45, IOR=1.47,
                           Subsurface_Weight=0.1, Subsurface_Radius=(1, 0.8, 0.2), Subsurface_Scale=0.05))
    return m


@cached
def water_bubble():
    m, nb, out = _new("water_bubble")
    _finish(nb, out, _bsdf(nb, Base_Color=(0.95, 0.97, 1.0), Roughness=0.03, Transmission_Weight=0.9, IOR=1.33,
                           Coat_Weight=1.0, Coat_Roughness=0.0))
    return m


@cached
def sauce_drop():
    m, nb, out = _new("sauce_drop")
    _finish(nb, out, _bsdf(nb, Base_Color=(0.56, 0.08, 0.02), Roughness=0.2, Coat_Weight=0.5, Coat_Roughness=0.05,
                           Subsurface_Weight=0.3, Subsurface_Radius=(1.0, 0.25, 0.1), Subsurface_Scale=0.02))
    return m


# ----------------------------------------------------------------- world ---
def backdrop_world(name, center=(0.5, 0.56), inner=(0.085, 0.05, 0.028), outer=(0.006, 0.005, 0.005),
                   ambient=(0.02, 0.018, 0.016), ambient_strength=1.0, radius=0.75):
    """Dark studio backdrop with a warm glow behind the subject (camera rays
    only) and a dim ambient for lighting."""
    w = bpy.data.worlds.new(name)
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    nb = NB(nt)
    out = nb.node("ShaderNodeOutputWorld")
    win = nb.out(nb.node("ShaderNodeTexCoord"), "Window")
    x, y, _ = nb.sep(win)
    dx = nb.mul(nb.sub(x, center[0]), 0.5625)
    dy = nb.sub(y, center[1])
    d = nb.m("SQRT", nb.add(nb.mul(dx, dx), nb.mul(dy, dy)))
    g = nb.m("POWER", nb.m("SUBTRACT", 1.0, nb.smoothstep(0.0, radius, d)), 1.6)
    col = nb.mix_rgb(g, outer, inner)
    lp = nb.out(nb.node("ShaderNodeLightPath"), "Is Camera Ray")
    amb = tuple(c * ambient_strength for c in ambient)
    col = nb.mix_rgb(lp, amb, col)
    bg = nb.node("ShaderNodeBackground")
    nb.set(nb.sock(bg, "Color"), col)
    nb.links.new(bg.outputs[0], nb.sock(out, "Surface"))
    # expose glow colour for animation
    w["glow"] = 1.0
    return w
