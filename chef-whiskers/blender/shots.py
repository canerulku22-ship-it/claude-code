"""The 3D chicken burger film, shot by shot. Each shot builds its set in build(), then update(t)
puts everything in place for time t (seconds) before a frame renders. events() lists sound cues."""
import math
import random

import bpy
from mathutils import Euler, Vector

import lib
from lib import arc, back_out, clamp, ease_in, ease_io, ease_out, lerp, seg, smooth, srgb, vlerp, wob

SHOTS = {}


def shot(name, seconds):
    def deco(cls):
        cls.name, cls.seconds = name, seconds
        SHOTS[name] = cls
        return cls
    return deco


# ---------------------------------------------------------------- shared building blocks
def base_set(target=(0, 0, 0.06), counter=True, glow=True, glow_at=(0, 0.9, 0.25), lens=40, fstop=4.0, warm=1.0):
    M = lib.Materials()
    M.bits = lib.principled("bits", srgb(0.8, 0.47, 0.14), rough=0.5, coat=0.3)[0]
    lib.studio(M, counter=counter, glow=glow, glow_at=glow_at)
    lib.lights(target, warm)
    cam, tgt = lib.camera(lens, fstop)
    return M, cam, tgt


def chicken_with_flakes(M, seed=3, flakes=2200, specks=True):
    ch = lib.chicken(M, "chicken", seed)
    flake = lib.blob("flake_shape", M.flake, 1.0, 1, (1.0, 1.0, 0.45), 0.4, seed)
    fl = lib.Points("flakes", flakes, flake, parent=ch)
    samples = lib.surface_samples(ch, flakes, seed + 1)
    rnd = random.Random(seed + 2)
    data = {"ch": ch, "flakes": fl, "fsamples": samples, "frnd": [(rnd.random(), rnd.random(), rnd.random(), rnd.random()) for _ in samples]}
    if specks:
        top = lib.surface_samples(ch, 900, seed + 3, min_nz=0.35)
        sp = {}
        for k, (mat, n) in enumerate([(M.paprika, 380), (M.pepper, 260), (M.garlic, 260)]):
            shape = lib.blob(f"speck_shape{k}", mat, 1.0, 1, (1, 1, 0.6), 0.5, k)
            sp[k] = (lib.Points(f"specks{k}", n, shape, parent=ch), top[k * 300:k * 300 + n] if k < 2 else top[600:600 + n])
        data["specks"] = sp
    return data


def set_chicken(M, data, wet=0.0, coat=0.0, fry=0.0, crust=None):
    lib.set_value(M.chicken, "wet", wet)
    lib.set_value(M.chicken, "coat", coat)
    lib.set_value(M.chicken, "fry", fry)
    lib.set_value(M.flake, "fry", fry)
    data["ch"].data.shape_keys.key_blocks["crust"].value = coat if crust is None else crust


def place_flakes(data, t=None, t0=0.0, t1=1.0, visible=True):
    """Flour flakes fly in from around the chicken and stick between t0 and t1 (or all stuck if t is None)."""
    cos, scales, rots = [], [], []
    for (co, nrm), (a, b, c, d) in zip(data["fsamples"], data["frnd"]):
        final = co + nrm * 0.0002
        if t is None:
            k = 1.0
        else:
            start = t0 + a * (t1 - t0) * 0.85
            k = ease_out(seg(t, start, start + 0.25))
        fly = nrm * (0.03 + 0.03 * b) + Vector(((c - 0.5) * 0.04, (d - 0.5) * 0.04, 0.03))
        cos.append(final + fly * (1 - k))
        scales.append(0.0 if (not visible or k <= 0.0) else (0.0007 + 0.0011 * b) * (0.6 + 0.4 * k))
        rots.append((a * 6, b * 6, c * 6))
    data["flakes"].set(cos, scales, rots)


def place_specks(data, t=None, t0=0.0, t1=1.0, visible=True):
    for k, (pts, samples) in data["specks"].items():
        rnd = random.Random(k + 40)
        cos, scales, rots = [], [], []
        for co, nrm in samples:
            a, b, c = rnd.random(), rnd.random(), rnd.random()
            if t is None:
                drop = 0.0
            else:
                start = t0 + a * (t1 - t0) * 0.8
                drop = 1.0 - ease_in(seg(t, start, start + 0.3))
            cos.append(co + nrm * 0.0004 + Vector(((b - 0.5) * 0.02 * drop, (c - 0.5) * 0.02 * drop, 0.12 * drop)))
            scales.append(0.0 if (not visible or drop >= 0.999) else 0.0006 + 0.0006 * b)
            rots.append((a * 6, b * 6, c * 6))
        pts.set(cos, scales, rots)


REST = {"bottom": 0.0, "sauce": 0.022, "lettuce": 0.027, "chicken": 0.054, "cheese": 0.079, "top": 0.081}


def burger(M, seed=7):
    """Assembled burger: layers parented to an empty; returns (root, layers dict, chicken data)."""
    L = {"bottom": lib.bun_bottom(M, "bun_bottom"), "sauce": lib.sauce_swirl(M), "lettuce": lib.lettuce(M, seed=seed)}
    cd = chicken_with_flakes(M, seed, flakes=2000, specks=False)
    L["chicken"] = cd["ch"]
    L["cheese"] = lib.cheese(M)
    L["top"] = lib.bun_top(M, "bun_top")
    root = lib.group("burger", *L.values())
    for k, o in L.items():
        o.location = (0, 0, REST[k])
    L["chicken"].rotation_euler.z = seed
    L["cheese"].data.shape_keys.key_blocks["melt"].value = 1.0
    set_chicken(M, cd, 0, 1, 1)
    place_flakes(cd)
    return root, L, cd


def bits_cloud(M, name, n, seed):
    shape = lib.blob(name + "_shape", M.bits, 1.0, 1, (1, 0.8, 0.6), 0.6, seed)
    return lib.Points(name, n, shape)


def dust(M, n=40):
    shape = lib.blob("dust_shape", M.dust, 1.0, 1, (1, 1, 1), 0.0, 1)
    return lib.Points("dust", n, shape)


def tag(M, text, size=0.011, dark=False):
    g = lib.label(M, text, size, dark=dark)
    g.scale = (0.0001,) * 3
    return g


def pop_tag(g, cam, t, t0, at, d=0.28):
    s = back_out(seg(t, t0, t0 + d)) if t >= t0 else 0.0
    g.location = at
    g.scale = (max(s, 0.0001),) * 3
    g.hide_render = s <= 0.001
    for c in g.children:
        c.hide_render = s <= 0.001
    lib.face_camera(g, cam)
    g.rotation_euler.rotate_axis("Z", wob(t, t0, 18, 6) * 0.15)


# ---------------------------------------------------------------- 1. intro: the finished burger floats and spins
@shot("b_intro", 2.6)
class Intro:
    def build(self):
        self.M, self.cam, self.tgt = base_set((0, 0, 0.14), counter=False, glow_at=(0, 0.75, 0.16))
        self.root, self.L, self.cd = burger(self.M)
        self.crumbs = bits_cloud(self.M, "crumbs", 70, 2)
        self.dust = dust(self.M)
        self.steam = lib.Sprites("steam", 6, seed=2)

    def update(self, t, D):
        spin = 0.5 + 2.6 * ease_out(seg(t, 0, D)) + t * 0.25
        self.root.location = (0, 0, 0.09 + 0.004 * math.sin(t * 2.2))
        self.root.rotation_euler = (0.12, 0, spin)
        c = Vector((0, 0, 0.15))
        self.crumbs.set(*lib.floaters(70, 3, t, c, (0.24, 0.2, 0.26), 0.0022, 0.05))
        self.dust.set(*lib.floaters(40, 5, t, (0, 0.45, 0.2), (1.2, 0.3, 0.8), 0.003, 0.03))
        push = ease_io(seg(t, 0, D - 0.35)) * 0.8 + 0.2 * ease_in(seg(t, D - 0.35, D))
        lib.shoot(self.cam, self.tgt, vlerp((0, -1.05, 0.22), (0, -0.42, 0.15), push), (0, 0, 0.14), lens=40, fstop=4.0)
        self.steam.rise(t, self.cam, (0, 0, 0.21), amount=0.7, spread=0.06, height=0.1, size=0.07)

    def events(self, D):
        return [{"t": 0, "type": "room", "dur": D}, {"t": 0, "type": "sizzle", "dur": D, "level": 0.15}, {"t": 0.0, "type": "whoosh"}, {"t": 0.4, "type": "sparkle"}, {"t": D - 0.35, "type": "whoosh"}]


# ---------------------------------------------------------------- 2. ingredients fly in and get labels
@shot("b_ingredients", 3.4)
class Ingredients:
    SLOTS = [("BRIOCHE BUNS", (-0.058, 0.17)), ("CHICKEN THIGHS", (0.058, 0.16)), ("FLOUR", (-0.06, 0.055)), ("SEASONING", (0.06, 0.05)),
             ("SAUCE", (-0.06, -0.055)), ("LETTUCE", (0.06, -0.06)), ("CHEESE", (0.0, -0.165))]

    def build(self):
        M = self.M = base_set((0, 0, 0.0), counter=True, glow=False)[0]
        self.cam, self.tgt = bpy.data.objects["cam"], bpy.data.objects["cam_target"]
        top = lib.bun_top(M, "bt", 0.042, 0.026); bot = lib.bun_bottom(M, "bb", 0.042, 0.016)
        bot.location.x, top.location.x = -0.025, 0.025
        buns = lib.group("buns", top, bot)
        cd = chicken_with_flakes(M, 4, flakes=10, specks=False); set_chicken(M, cd, 0, 0, 0); place_flakes(cd, visible=False)
        ch = cd["ch"]; ch.scale = (0.75,) * 3
        flourb = lib.group("flourset", lib.bowl(M, "flour_bowl", M.ceramic_sage, 0.042, 0.03), self._mound(M, 0.036, 0.024))
        seas = self._seasoning(M)
        sauceb = lib.group("sauceset", lib.bowl(M, "sauce_bowl", M.ceramic, 0.034, 0.022), lib.disc("sauce_fill", 0.031, 0.016, 64, 8, M.sauce))
        let = lib.lettuce(M, "leaf", 0.045)
        chz = lib.cheese(M, "chz", 0.07); chz.data.shape_keys.key_blocks["melt"].value = 0.0
        self.items = [buns, ch, flourb, seas, sauceb, let, chz]
        self.tags = [tag(M, name, 0.013) for name, _ in self.SLOTS]
        self.leads = [lib.leader(M, f"lead{i}") for i in range(len(self.SLOTS))]
        rnd = random.Random(9)
        self.from_ = [Vector(((rnd.random() - 0.5) * 0.5, 0.25 + rnd.random() * 0.2, 0.3 + rnd.random() * 0.1)) for _ in self.items]

    def _mound(self, M, R, z):
        m = lib.disc("mound", R, z, 64, 12, M.flour)
        for v in m.data.vertices:
            r = math.hypot(v.co.x, v.co.y) / R
            v.co.z = z + 0.008 * (1 - r * r) + 0.0012 * math.sin(v.co.x * 400) * math.cos(v.co.y * 380)
        return m

    def _seasoning(self, M):
        dish = lib.bowl(M, "seas_dish", M.ceramic_dark, 0.045, 0.012)
        piles = []
        for k, (mat, x, y) in enumerate([(M.paprika, -0.017, 0.008), (M.garlic, 0.017, 0.01), (M.pepper, 0.0, -0.017)]):
            p = lib.disc(f"pile{k}", 0.016, 0.004, 48, 8, mat)
            for v in p.data.vertices:
                r = math.hypot(v.co.x, v.co.y) / 0.016
                v.co.z = 0.004 + 0.009 * max(0.0, 1 - r) ** 1.4
            p.location = (x, y, 0)
            piles.append(p)
        return lib.group("seasoning", dish, *piles)

    def update(self, t, D):
        cam_pos = Vector((0.015 * math.sin(t * 0.8), -0.3, 0.7))
        lib.shoot(self.cam, self.tgt, cam_pos, (0, 0.0, 0), lens=40, fstop=8.0)
        for i, (it, (name, (x, y))) in enumerate(zip(self.items, self.SLOTS)):
            t0 = 0.12 + i * 0.3
            k = seg(t, t0, t0 + 0.42)
            land = Vector((x, y, 0.0))
            p = arc(self.from_[i], land, ease_out(k), 0.05) if k < 1 else land.copy()
            p.z += 0.004 * math.sin(t * 2.6 + i) * k + wob(t, t0 + 0.42, 22, 8) * 0.004
            it.location = p
            it.rotation_euler = (0.3 * (1 - k) * math.sin(i), 0.2 * (1 - k), (1 - ease_out(k)) * (2.5 + i) + 0.2 * i)
            it.hide_render = t < t0
            for c in it.children:
                c.hide_render = t < t0
            side = 1 if x >= 0 else -1
            anchor = Vector((x, y - 0.04, 0.03))
            pop_tag(self.tags[i], self.cam, t, t0 + 0.32, anchor)
            lib.set_leader(self.leads[i], land + Vector((0, -0.012, 0.012)), anchor + Vector((0, 0.008, 0)), seg(t, t0 + 0.3, t0 + 0.45))

    def events(self, D):
        ev = [{"t": 0, "type": "room", "dur": D}]
        for i in range(7):
            ev += [{"t": 0.12 + i * 0.3, "type": "whoosh", "gain": 0.45}, {"t": 0.54 + i * 0.3, "type": "place", "gain": 0.5}, {"t": 0.44 + i * 0.3, "type": "pop", "gain": 0.6}]
        return ev


# ---------------------------------------------------------------- 3. season the chicken
@shot("b_season", 2.0)
class Season:
    def build(self):
        self.M, self.cam, self.tgt = base_set((0, 0, 0.02), glow_at=(0, 0.8, 0.2))
        M = self.M
        self.board = self._board(M)
        self.cd = chicken_with_flakes(M, 5)
        self.cd["ch"].location = (0, 0, 0.037)

    def _board(self, M):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.009))
        b = bpy.context.object
        b.scale = (0.26, 0.18, 0.018)
        m = lib.principled("wood", srgb(0.6, 0.4, 0.24), rough=0.55, coat=0.2)[0]
        b.data.materials.append(m)
        b.modifiers.new("bevel", "BEVEL").width = 0.004
        return b

    def update(self, t, D):
        set_chicken(self.M, self.cd, 0, 0, 0)
        place_flakes(self.cd, visible=False)
        place_specks(self.cd, t, 0.1, 1.3)
        ch = self.cd["ch"]
        ch.rotation_euler = (0, 0, 0.4 + 0.15 * t)
        push = ease_io(seg(t, 0, D))
        lib.shoot(self.cam, self.tgt, vlerp((0.22, -0.55, 0.34), (0.17, -0.45, 0.27), push), (0, 0, 0.04), lens=40, fstop=4.0)

    def events(self, D):
        return [{"t": 0, "type": "room", "dur": D}, {"t": 0.1, "type": "rustle", "dur": 1.3}, {"t": 0.0, "type": "whoosh", "gain": 0.6}]


# ---------------------------------------------------------------- 4. dip in buttermilk
@shot("b_dip", 2.0)
class Dip:
    def build(self):
        self.M, self.cam, self.tgt = base_set((0, 0, 0.05), glow_at=(0, 0.8, 0.2))
        M = self.M
        self.bowl = lib.bowl(M, "milk_bowl", M.ceramic, 0.08, 0.055)
        self.milk = lib.liquid(M, "milk", 0.074, M.milk)
        self.milk.location.z = 0.042
        self.cd = chicken_with_flakes(M, 5)
        drop = lib.blob("drop_shape", M.milk, 1.0, 2, (1, 1, 1.3), 0.1, 3)
        self.drops = lib.Points("drops", 60, drop)
        self.drips = lib.Points("drips", 24, lib.blob("drip_shape", M.milk, 1.0, 2, (1, 1, 1.6), 0.0, 4))

    def update(self, t, D):
        ch = self.cd["ch"]
        tin, tout = 0.5, 1.15
        if t < tin:
            p = vlerp((0, 0, 0.16), (0, 0, 0.043), ease_in(seg(t, 0.1, tin)))
        elif t < tout:
            p = Vector((0, 0, 0.043 + 0.003 * wob(t, tin, 14, 4)))
        else:
            p = vlerp((0, 0, 0.043), (0, -0.01, 0.15), ease_io(seg(t, tout, 1.7)))
        ch.location = p
        ch.rotation_euler = (0.25 * seg(t, 0, tin) - 0.25 * seg(t, tout, 1.7), 0, 0.6)
        wet = smooth(seg(t, tin, tin + 0.2)) * 0.85
        set_chicken(self.M, self.cd, wet, 0, 0)
        place_flakes(self.cd, visible=False)
        place_specks(self.cd, None, visible=wet < 0.5)
        frame = bpy.context.scene.frame_current
        lib.set_wave(self.milk, 0.0025 if t > tin else 0.0, int(tin * lib.FPS), 0, 0)
        self.drops.set(*lib.ballistic(60, 7, t, tin, (0, 0, 0.045), power=1.0, life=0.7, size=0.0022, floor=-0.003))
        cos, sc, rots = [], [], []
        rnd = random.Random(3)
        for i in range(24):
            a, b, c = rnd.random(), rnd.random(), rnd.random()
            ph = (t - tout - a * 0.5) * 1.6
            if ph < 0 or t < tout:
                cos.append(p); sc.append(0.0); rots.append((0, 0, 0)); continue
            ph %= 1.0
            start = p + Vector(((b - 0.5) * 0.08, (c - 0.5) * 0.05, -0.014))
            cos.append(start + Vector((0, 0, -0.9 * ph * ph * 0.25)))
            sc.append(0.0018 * (1 - ph * 0.3) if start.z - 0.9 * ph * ph * 0.25 > 0.045 else 0.0)
            rots.append((0, 0, 0))
        self.drips.set(cos, sc, rots)
        lib.shoot(self.cam, self.tgt, (0.22, -0.55, 0.26), (0, 0, 0.075), lens=40, fstop=4.5)

    def events(self, D):
        return [{"t": 0, "type": "room", "dur": D}, {"t": 0.0, "type": "whoosh", "gain": 0.6}, {"t": 0.5, "type": "splash"}, {"t": 1.15, "type": "whoosh", "gain": 0.5}, {"t": 1.5, "type": "plop", "gain": 0.4}, {"t": 1.75, "type": "plop", "gain": 0.35}]


# ---------------------------------------------------------------- 5. coat in flour: flakes fly in and stick, the crust forms
@shot("b_coat", 2.6)
class Coat:
    def build(self):
        self.M, self.cam, self.tgt = base_set((0, 0, 0.05), glow_at=(0, 0.8, 0.2))
        M = self.M
        self.bowl = lib.bowl(M, "flour_bowl", M.ceramic_sage, 0.085, 0.05)
        self.mound = lib.disc("flour_mound", 0.078, 0.03, 96, 16, M.flour)
        for v in self.mound.data.vertices:
            r = math.hypot(v.co.x, v.co.y) / 0.078
            v.co.z = 0.03 + 0.012 * (1 - r * r) + 0.0015 * math.sin(v.co.x * 300) * math.cos(v.co.y * 270)
        self.cd = chicken_with_flakes(M, 5)
        self.puff1 = lib.Sprites("puffA", 8, (1, 0.99, 0.96, 1), 0.5, 1)
        self.puff2 = lib.Sprites("puffB", 8, (1, 0.99, 0.96, 1), 0.5, 2)
        self.dustf = lib.Points("flourdust", 160, lib.blob("fd_shape", M.flour, 1.0, 1, (1, 1, 1), 0.3, 6))

    def update(self, t, D):
        ch = self.cd["ch"]
        land1, flip0, land2, lift = 0.45, 1.0, 1.35, 1.9
        S = Vector((0, 0, 0.064))
        if t < land1:
            p, rx = vlerp((0, 0.0, 0.17), S, ease_in(seg(t, 0.1, land1))), 0.0
        elif t < flip0:
            p, rx = S + Vector((0, 0, 0.002 * wob(t, land1, 16, 6))), 0.0
        elif t < land2:
            s = seg(t, flip0, land2)
            p, rx = arc(S, S, s, 0.05), math.pi * ease_io(s)
        elif t < lift:
            p, rx = S.copy(), math.pi
        else:
            p, rx = vlerp(S, (0, -0.01, 0.13), ease_io(seg(t, lift, D))), math.pi - 0.4 * seg(t, lift, D)
        ch.location = p
        ch.rotation_euler = (rx, 0, 0.6)
        coat = smooth(seg(t, land1, 1.75))
        set_chicken(self.M, self.cd, 0.85 * (1 - coat), coat, 0, crust=coat)
        place_flakes(self.cd, t, land1, 1.75)
        place_specks(self.cd, None, visible=False)
        self.puff1.burst(t, land1, self.cam, S + Vector((0, 0, -0.01)), 1.0, 0.12, 0.06, 0.08)
        self.puff2.burst(t, land2, self.cam, S + Vector((0, 0, -0.01)), 1.0, 0.13, 0.07, 0.09)
        a = lib.ballistic(80, 11, t, land1, S, power=0.5, life=0.8, size=0.0016, floor=-0.03)
        b = lib.ballistic(80, 12, t, land2, S, power=0.55, life=0.8, size=0.0016, floor=-0.03)
        self.dustf.set(a[0] + b[0], a[1] + b[1], a[2] + b[2])
        push = ease_io(seg(t, 0, D))
        lib.shoot(self.cam, self.tgt, vlerp((0.22, -0.55, 0.28), (0.17, -0.46, 0.24), push), (0, 0, 0.075), lens=40, fstop=4.5)

    def events(self, D):
        return [{"t": 0, "type": "room", "dur": D}, {"t": 0.0, "type": "whoosh", "gain": 0.6}, {"t": 0.45, "type": "puff"}, {"t": 0.5, "type": "rustle", "dur": 1.2},
                {"t": 1.0, "type": "whoosh", "gain": 0.5}, {"t": 1.35, "type": "puff"}]


# ---------------------------------------------------------------- 6. into the hot oil: bubbles, steam, golden colour
@shot("b_fry", 3.0)
class Fry:
    def build(self):
        self.M, self.cam, self.tgt = base_set((0, 0, 0.07), glow_at=(0, 0.8, 0.2))
        M = self.M
        self.pot = lib.pot(M, R=0.15)
        self.oil = lib.liquid(M, "oil", 0.142, M.oil)
        self.oil.location.z = 0.062
        self.cd = chicken_with_flakes(M, 5)
        bub = lib.blob("bubble_shape", M.bubble, 1.0, 2, (1, 1, 0.8), 0.05, 1)
        self.bubbles = lib.Points("bubbles", 320, bub)
        self.spits = lib.Points("spits", 40, lib.blob("spit_shape", M.oil, 1.0, 1, (1, 1, 1), 0.1, 2))
        self.bits = bits_cloud(M, "floating_bits", 50, 4)
        self.steam = lib.Sprites("steam", 8, seed=4)

    def update(self, t, D):
        ch = self.cd["ch"]
        tin = 0.7
        oil_z = 0.062
        if t < tin:
            p = vlerp((0, -0.01, 0.17), (0, 0, oil_z - 0.004), ease_io(seg(t, 0.05, tin)))
        else:
            p = Vector((0, 0, oil_z - 0.008 + 0.0025 * math.sin(t * 6) + 0.004 * wob(t, tin, 12, 4)))
        ch.location = p
        ch.rotation_euler = (0.08, 0.05, 0.6 + 0.1 * t)
        fry = 0.3 + 0.6 * ease_out(seg(t, tin + 0.05, D + 0.1)) if t > tin else 0.0
        set_chicken(self.M, self.cd, 0, 1, fry)
        place_flakes(self.cd)
        place_specks(self.cd, None, visible=False)
        lib.set_wave(self.oil, 0.0018 if t > tin else 0.0, int(tin * lib.FPS))
        amount = 0.0 if t < tin else 1.4 * math.exp(-(t - tin) * 1.2) + 0.8
        rnd = random.Random(5)
        cos, sc, rots = [], [], []
        for i in range(320):
            a, b, c, d, e = (rnd.random() for _ in range(5))
            ph = (t * (1.3 + c * 2.6) + a) % 1.0
            if e < 0.75:
                ang = b * 2 * math.pi
                rim = 0.95 + 0.25 * d
                x, y = p.x + math.cos(ang) * 0.066 * rim, p.y + math.sin(ang) * 0.05 * rim
            else:
                ang, rr = b * 2 * math.pi, math.sqrt(d) * 0.135
                x, y = math.cos(ang) * rr, math.sin(ang) * rr
            s = amount * 0.005 * (0.35 + d) * math.sin(math.pi * ph)
            cos.append((x, y, oil_z + s * 0.2)); sc.append(s); rots.append((0, 0, a * 6))
        self.bubbles.set(cos, sc, rots)
        self.spits.set(*lib.ballistic(40, 8, t, tin, (0, 0, oil_z + 0.004), power=0.9, life=0.6, size=0.0015, floor=-0.01))
        bc, bs, br = lib.floaters(50, 9, t, (0, 0, oil_z + 0.001), (0.24, 0.24, 0.0), 0.0016, 0.0)
        self.bits.set(bc, [s * seg(t, tin, tin + 0.5) for s in bs], br)
        self.steam.rise(t, self.cam, (0, 0, oil_z + 0.02), amount=seg(t, tin, tin + 0.4) * 0.9, spread=0.16, height=0.14, size=0.08)
        push = ease_io(seg(t, 0, D))
        lib.shoot(self.cam, self.tgt, vlerp((0.1, -0.46, 0.44), (0.07, -0.3, 0.3), push), (0, 0.012, oil_z + 0.006), lens=30, fstop=4.5)

    def events(self, D):
        return [{"t": 0, "type": "room", "dur": D}, {"t": 0.0, "type": "whoosh", "gain": 0.6}, {"t": 0.7, "type": "sizzle", "dur": D - 0.7, "level": 1.0, "attack": 0.03},
                {"t": 0.7, "type": "bubbles", "dur": D - 0.7}, {"t": 0.7, "type": "splash", "gain": 0.4}]


# ---------------------------------------------------------------- 7. macro: golden crust out of the oil, 165 F label
@shot("b_crisp", 1.8)
class Crisp:
    def build(self):
        self.M, self.cam, self.tgt = base_set((0, 0, 0.1), glow_at=(0, 0.6, 0.2), fstop=2.2)
        M = self.M
        self.pot = lib.pot(M, R=0.15)
        self.oil = lib.liquid(M, "oil", 0.142, M.oil)
        self.oil.location.z = 0.062
        self.cd = chicken_with_flakes(M, 5)
        self.drips = lib.Points("oil_drips", 30, lib.blob("od_shape", M.oil, 1.0, 2, (1, 1, 1.5), 0.0, 3))
        self.steam = lib.Sprites("steam", 6, seed=6)
        self.tag = tag(M, "165°F / 74°C", 0.0095)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0012, depth=0.07)
        probe = bpy.context.object
        probe.data.materials.append(M.thermo)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0045, depth=0.04, vertices=24)
        body = bpy.context.object
        body.location.z = 0.052
        body.data.materials.append(M.bottle)
        bpy.ops.object.shade_smooth()
        self.probe = lib.group("probe", probe, body)

    def update(self, t, D):
        ch = self.cd["ch"]
        lift = ease_io(seg(t, 0, 0.9))
        p = vlerp((0, 0, 0.058), (0, 0, 0.115), lift)
        ch.location = p
        ch.rotation_euler = (0.35 * lift, 0.1, 0.6 + 0.5 * t)
        set_chicken(self.M, self.cd, 0, 1, lerp(0.88, 1.0, smooth(seg(t, 0, 1.0))))
        place_flakes(self.cd)
        place_specks(self.cd, None, visible=False)
        lib.set_wave(self.oil, 0.0012, 0)
        rnd = random.Random(8)
        cos, sc, rots = [], [], []
        for i in range(30):
            a, b, c = rnd.random(), rnd.random(), rnd.random()
            ph = ((t - a * 0.7) * 1.8) % 1.0 if t > 0.4 else -1
            start = p + Vector(((b - 0.5) * 0.09, (c - 0.5) * 0.06, -0.018))
            z = start.z - 0.9 * ph * ph * 0.06
            ok = ph >= 0 and z > 0.064
            cos.append((start.x, start.y, z)); sc.append(0.0014 if ok else 0.0); rots.append((0, 0, 0))
        self.drips.set(cos, sc, rots)
        self.steam.rise(t, self.cam, p + Vector((0, 0, 0.01)), amount=0.8, spread=0.08, height=0.1, size=0.06)
        stab = ease_out(seg(t, 0.85, 1.1))
        self.probe.location = p + Vector((0.045 - 0.02 * stab, -0.005, 0.02 + 0.03 * (1 - stab)))
        self.probe.rotation_euler = (0, -0.7, 0)
        self.probe.hide_render = t < 0.8
        for c in self.probe.children:
            c.hide_render = t < 0.8
        pop_tag(self.tag, self.cam, t, 1.05, p + Vector((0.0, -0.045, 0.058)))
        lib.shoot(self.cam, self.tgt, vlerp((0.17, -0.44, 0.16), (0.13, -0.36, 0.15), ease_io(seg(t, 0, D))), p + Vector((0, 0, 0.005)), lens=40, fstop=3.5)

    def events(self, D):
        return [{"t": 0, "type": "room", "dur": D}, {"t": 0, "type": "sizzle", "dur": D, "level": 0.6}, {"t": 0.0, "type": "whoosh", "gain": 0.5}, {"t": 0.88, "type": "crunch", "gain": 0.6}, {"t": 1.05, "type": "ding"}, {"t": 1.05, "type": "pop"}]


# ---------------------------------------------------------------- 8. assembly: each layer lands with a bounce
@shot("b_assemble", 2.8)
class Assemble:
    def build(self):
        self.M, self.cam, self.tgt = base_set((0, 0, 0.06), glow_at=(0, 0.8, 0.22))
        M = self.M
        plate = lib.lathe("plate", [(0, 0.0), (0.09, 0.0), (0.1, 0.004), (0.104, 0.009), (0.1, 0.01), (0.085, 0.004), (0, 0.004)], 96, M.ceramic_dark)
        plate.modifiers.new("sub", "SUBSURF").levels = 1
        self.root, self.L, self.cd = burger(M)
        self.root.location = (0, 0, 0.004)
        self.L["cheese"].data.shape_keys.key_blocks["melt"].value = 0.0

    def update(self, t, D):
        L = self.L
        times = {"bottom": (0.0, 0.3), "lettuce": (0.75, 1.15), "chicken": (1.1, 1.4), "cheese": (1.4, 1.62), "top": (1.95, 2.25)}
        for k, (a, b) in times.items():
            o = L[k]
            k01 = seg(t, a, b)
            o.location.z = REST[k] + (1 - ease_in(k01)) * 0.16
            sq = wob(t, b, 30, 9) * (0.15 if k in ("chicken", "top", "bottom") else 0.05)
            o.scale = (1 + sq * 0.5, 1 + sq * 0.5, 1 - sq)
            if k == "lettuce":
                o.rotation_euler = (0.5 * (1 - k01) * math.sin(t * 9), 0.4 * (1 - k01) * math.cos(t * 7), 0.4 * (1 - k01))
            vis = t >= a
            o.hide_render = not vis
            for c in o.children:
                c.hide_render = not vis
        fl = self.cd["flakes"].obj
        fl.hide_render = t < times["chicken"][0]
        L["sauce"].data.bevel_factor_end = ease_io(seg(t, 0.32, 0.8))
        L["sauce"].hide_render = t < 0.32
        L["cheese"].data.shape_keys.key_blocks["melt"].value = smooth(seg(t, 1.6, 2.3))
        set_chicken(self.M, self.cd, 0, 1, 1)
        ang = lerp(-0.5, 0.3, ease_io(seg(t, 0, D)))
        r = 0.62
        lib.shoot(self.cam, self.tgt, (math.sin(ang) * r, -math.cos(ang) * r, 0.25), (0, 0, 0.06), lens=40, fstop=5.0)

    def events(self, D):
        return [{"t": 0, "type": "room", "dur": D}, {"t": 0.3, "type": "place"}, {"t": 0.32, "type": "squirt", "dur": 0.5}, {"t": 0.8, "type": "rustle", "dur": 0.35},
                {"t": 1.4, "type": "thump"}, {"t": 1.62, "type": "plop"}, {"t": 2.25, "type": "place"}, {"t": 2.35, "type": "sparkle"}]


# ---------------------------------------------------------------- 9. exploded view: layers float apart, labels, back together
@shot("b_exploded", 3.0)
class Exploded:
    ORDER = [("top", "BRIOCHE BUN"), ("cheese", "MELTED CHEESE"), ("chicken", "CRISPY CHICKEN"), ("lettuce", "LETTUCE"), ("sauce", "SAUCE"), ("bottom", "TOASTED BUN")]

    def build(self):
        self.M, self.cam, self.tgt = base_set((0, 0, 0.12), counter=False, glow_at=(0, 0.75, 0.14))
        self.root, self.L, self.cd = burger(self.M)
        self.tags = [tag(self.M, name, 0.011) for _, name in self.ORDER]
        self.leads = [lib.leader(self.M, f"lead{i}") for i in range(len(self.ORDER))]
        self.dust = dust(self.M)
        self.crumbs = bits_cloud(self.M, "crumbs", 50, 3)

    def update(self, t, D):
        apart = ease_out(seg(t, 0.05, 0.8)) * (1 - ease_in(seg(t, 2.1, 2.6)))
        spread = {"bottom": -0.05, "sauce": -0.02, "lettuce": 0.005, "chicken": 0.045, "cheese": 0.09, "top": 0.13}
        self.root.location = (0, 0, 0.065)
        self.root.rotation_euler = (0, 0, 0.4 + 0.25 * t)
        self.L["cheese"].data.shape_keys.key_blocks["melt"].value = 1.0 - 0.65 * apart
        for k, o in self.L.items():
            o.location.z = REST[k] + spread[k] * apart
            sq = wob(t, 2.6, 30, 9) * 0.1
            o.scale = (1 + sq * 0.5, 1 + sq * 0.5, 1 - sq)
        set_chicken(self.M, self.cd, 0, 1, 1)
        ang = lerp(-0.7, 0.6, ease_io(seg(t, 0, D)))
        r = 0.85
        lib.shoot(self.cam, self.tgt, (math.sin(ang) * r, -math.cos(ang) * r, 0.17), (0, 0, 0.125), lens=40, fstop=6.0)
        bpy.context.view_layer.update()
        for i, (k, name) in enumerate(self.ORDER):
            o = self.L[k]
            c = o.matrix_world.translation + Vector((0, 0, 0.01))
            side = 1 if i % 2 == 0 else -1
            right = Vector((math.cos(ang), math.sin(ang), 0))
            at = c + right * side * 0.088
            show = seg(t, 0.55 + i * 0.1, 0.7 + i * 0.1) * (1 - seg(t, 2.0, 2.15))
            pop_tag(self.tags[i], self.cam, t, 0.55 + i * 0.1, at)
            if t > 2.0:
                s = 1 - seg(t, 2.0, 2.15)
                self.tags[i].scale = (max(s, 0.0001),) * 3
                self.tags[i].hide_render = s <= 0.001
                for ch in self.tags[i].children:
                    ch.hide_render = s <= 0.001
            lib.set_leader(self.leads[i], c + right * side * 0.045, at - right * side * 0.03, show)
        self.dust.set(*lib.floaters(40, 5, t, (0, 0.45, 0.2), (1.2, 0.3, 0.8), 0.003, 0.03))
        self.crumbs.set(*lib.floaters(50, 4, t, (0, 0, 0.14), (0.26, 0.2, 0.3), 0.002, 0.05))

    def events(self, D):
        return [{"t": 0, "type": "room", "dur": D}, {"t": 0.05, "type": "whoosh"}] + [{"t": 0.55 + i * 0.1, "type": "pop", "gain": 0.6} for i in range(6)] + \
            [{"t": 2.1, "type": "whoosh"}, {"t": 2.6, "type": "thump"}, {"t": 2.65, "type": "sparkle"}]


# ---------------------------------------------------------------- 10. hero reveal with the title
@shot("b_reveal", 2.8)
class Reveal:
    WORDS = [("THE ULTIMATE", 0.014, 0.3), ("CRISPY CHICKEN", 0.017, 0.62), ("BURGER", 0.024, 0.95)]

    def build(self):
        self.M, self.cam, self.tgt = base_set((0, 0, 0.12), counter=False, glow_at=(0, 0.75, 0.12))
        self.root, self.L, self.cd = burger(self.M)
        self.dust = dust(self.M)
        self.crumbs = bits_cloud(self.M, "crumbs", 70, 6)
        self.steam = lib.Sprites("steam", 6, seed=7)
        self.words = []
        for text, size, t0 in self.WORDS:
            cu = bpy.data.curves.new("title_" + text, "FONT")
            cu.body, cu.size, cu.extrude, cu.bevel_depth = text, size, size * 0.12, size * 0.025
            cu.align_x, cu.align_y = "CENTER", "CENTER"
            f = lib.font_file()
            if f:
                cu.font = f
            o = lib.link(bpy.data.objects.new("title_" + text, cu))
            cu.materials.append(self.M.gold if "CRISPY" in text else self.M.text)
            self.words.append((o, t0))

    def update(self, t, D):
        self.root.location = (0, 0, 0.055 + 0.003 * math.sin(t * 2))
        self.root.rotation_euler = (0.1, 0, 0.6 + t * 0.55)
        set_chicken(self.M, self.cd, 0, 1, 1)
        push = ease_io(seg(t, 0, D))
        cam_pos = vlerp((0, -0.68, 0.16), (0, -0.58, 0.15), push)
        lib.shoot(self.cam, self.tgt, cam_pos, (0, 0, 0.14), lens=40, fstop=5.0)
        for i, (o, t0) in enumerate(self.words):
            s = back_out(seg(t, t0, t0 + 0.32)) if t >= t0 else 0.0
            o.scale = (max(s, 0.0001),) * 3
            o.hide_render = s <= 0.001
            o.location = (0, -0.04, 0.275 - i * 0.034 - (0.006 if i == 2 else 0))
            lib.face_camera(o, self.cam)
            o.rotation_euler.rotate_axis("Z", wob(t, t0, 16, 5) * 0.12)
        self.steam.rise(t, self.cam, (0, 0, 0.15), amount=0.6, spread=0.06, height=0.08, size=0.06)
        self.dust.set(*lib.floaters(40, 5, t, (0, 0.45, 0.2), (1.2, 0.3, 0.8), 0.003, 0.03))
        self.crumbs.set(*lib.floaters(70, 6, t, (0, 0, 0.11), (0.26, 0.2, 0.22), 0.0022, 0.05))

    def events(self, D):
        return [{"t": 0, "type": "room", "dur": D}, {"t": 0, "type": "sizzle", "dur": D, "level": 0.12}, {"t": 0.0, "type": "whoosh"}] + \
            [{"t": t0, "type": "pop", "gain": 0.7} for _, _, t0 in self.WORDS] + [{"t": 1.0, "type": "sparkle"}, {"t": 1.3, "type": "crunch", "gain": 0.9}]
