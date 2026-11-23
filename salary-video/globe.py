"""3D globe for the intro: a lit, textured sphere drawn with numpy.

Country shapes come from world-atlas (Natural Earth 1:50m), see data/LICENSE-world-atlas.
The equirectangular texture is drawn once and cached in .cache/.
"""
import json, math, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "countries-50m.json")
CACHE = os.path.join(HERE, ".cache")
TW, TH = 8192, 4096

OCEAN, GRID = (14, 44, 92), (24, 60, 116)
LAND, BORDER = (54, 84, 126), (112, 142, 184)
HIGHLIGHT, HIGHLIGHT_EDGE = (255, 199, 44), (255, 236, 170)
ATMOSPHERE = (90, 160, 255)


def load_countries(path=DATA):
    """[(name, [polygon, ...])], each polygon a list of rings of (lon, lat)."""
    topo = json.load(open(path, encoding="utf-8"))
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x, y = x + dx, y + dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(ids):
        pts = []
        for i in ids:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        return pts

    out = []
    for g in topo["objects"]["countries"]["geometries"]:
        polys = [g["arcs"]] if g["type"] == "Polygon" else g["arcs"] if g["type"] == "MultiPolygon" else []
        out.append((g.get("properties", {}).get("name", ""), [[ring(r) for r in p] for p in polys]))
    return out


def _px(lon, lat):
    return ((lon + 180) / 360 * TW, (90 - lat) / 180 * TH)


def _copies(ring, fill):
    """Pixel outlines for one ring. Longitudes are made continuous across the 180° line and the
    ring is drawn again shifted by 360° where it spills over; a filled ring that circles a pole
    (Antarctica) is closed through that pole."""
    r = [ring[0]]
    for lon, lat in ring[1:]:
        prev = r[-1][0]
        while lon - prev > 180: lon -= 360
        while lon - prev < -180: lon += 360
        r.append((lon, lat))
    if fill and abs(r[-1][0] - r[0][0]) > 180:
        pole = -90 if sum(p[1] for p in r) < 0 else 90
        r += [(r[-1][0], pole), (r[0][0], pole)]
    lons = [p[0] for p in r]
    shifts = [0] + ([360] if min(lons) < -180 else []) + ([-360] if max(lons) > 180 else [])
    return [[_px(lon + s, lat) for lon, lat in r] for s in shifts]


def build_texture(highlight):
    """Equirectangular map with `highlight` (a country name) in yellow; cached as .npy."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"globe-{highlight.lower().replace(' ', '_')}-{TW}.npy")
    if os.path.exists(path):
        return np.load(path, mmap_mode="r")
    im = Image.new("RGB", (TW, TH), OCEAN)
    d = ImageDraw.Draw(im)
    for lon in range(-180, 181, 15):
        d.line([_px(lon, -90), _px(lon, 90)], fill=GRID, width=3)
    for lat in range(-75, 76, 15):
        d.line([_px(-180, lat), _px(180, lat)], fill=GRID, width=3)
    countries = load_countries()
    for name, polys in countries:
        for poly in polys:
            ring = poly[0]
            if len(poly) > 1 and all(abs(lat) > 89.9 for _, lat in ring):
                ring = poly[1]  # Antarctica: outer ring is the pole itself, coast comes next
            for pts in _copies(ring, fill=True):
                d.polygon(pts, fill=HIGHLIGHT if name == highlight else LAND)
    for name, polys in countries:
        for poly in polys:
            for ring in poly:
                for pts in _copies(ring, fill=False):
                    d.line(pts, fill=HIGHLIGHT_EDGE if name == highlight else BORDER, width=3)
    tex = np.asarray(im, dtype=np.uint8)
    np.save(path, tex)
    return np.load(path, mmap_mode="r")


def country_point(name):
    """Centre of the bounding box of the country's largest polygon (lon, lat)."""
    best = None
    for n, polys in load_countries():
        if n != name:
            continue
        for poly in polys:
            xs, ys = zip(*poly[0])
            area = (max(xs) - min(xs)) * (max(ys) - min(ys))
            if best is None or area > best[0]:
                best = (area, ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2))
    if best is None:
        raise ValueError(f"no country named {name!r} in {DATA}")
    return best[1]


def project(lon, lat, lon0, lat0, cx, cy, R):
    """Screen position of (lon, lat) on a globe centred on (lon0, lat0), and whether it faces us."""
    lon, lat, lon0, lat0 = map(math.radians, (lon, lat, lon0, lat0))
    X, Y, Z = math.cos(lat) * math.sin(lon), math.sin(lat), math.cos(lat) * math.cos(lon)
    x = X * math.cos(lon0) - Z * math.sin(lon0)
    z1 = X * math.sin(lon0) + Z * math.cos(lon0)
    y = Y * math.cos(lat0) - z1 * math.sin(lat0)
    z = Y * math.sin(lat0) + z1 * math.cos(lat0)
    return cx + x * R, cy - y * R, z > 0


def draw(im, tex, cx, cy, R, lon0, lat0, alpha=1.0):
    """Draw the globe onto the RGB image `im` in place."""
    W, H = im.size
    x0, x1 = max(0, int(cx - R * 1.15)), min(W, int(cx + R * 1.15) + 1)
    y0, y1 = max(0, int(cy - R * 1.15)), min(H, int(cy + R * 1.15) + 1)
    if x0 >= x1 or y0 >= y1:
        return
    region = np.asarray(im.crop((x0, y0, x1, y1)), dtype=np.float32)
    xs = (np.arange(x0, x1, dtype=np.float32) + 0.5 - cx) / R
    ys = (cy - np.arange(y0, y1, dtype=np.float32) - 0.5) / R
    x, y = np.meshgrid(xs, ys)
    r2 = x * x + y * y
    # atmosphere: soft glow just outside the rim
    halo = np.clip(1 - (np.sqrt(r2) - 1) / 0.13, 0, 1) ** 2.2 * (r2 > 1)
    out = region + (np.array(ATMOSPHERE, np.float32) - region) * (halo[..., None] * 0.55 * alpha)
    inside = r2 <= 1
    if inside.any():
        xi, yi = x[inside], y[inside]
        z = np.sqrt(1 - xi * xi - yi * yi)
        la, lo = math.radians(lat0), math.radians(lon0)
        y1_ = yi * math.cos(la) + z * math.sin(la)
        z1_ = -yi * math.sin(la) + z * math.cos(la)
        X = xi * math.cos(lo) + z1_ * math.sin(lo)
        Z = -xi * math.sin(lo) + z1_ * math.cos(lo)
        lat = np.arcsin(np.clip(y1_, -1, 1))
        lon = np.arctan2(X, Z)
        u = (lon + math.pi) / (2 * math.pi) * TW - 0.5
        v = (math.pi / 2 - lat) / math.pi * TH - 0.5
        u0, v0 = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
        fu, fv = (u - u0)[:, None], (v - v0)[:, None]
        u0m, u1m = u0 % TW, (u0 + 1) % TW
        v0c, v1c = np.clip(v0, 0, TH - 1), np.clip(v0 + 1, 0, TH - 1)
        col = ((tex[v0c, u0m] * (1 - fu) + tex[v0c, u1m] * fu) * (1 - fv)
               + (tex[v1c, u0m] * (1 - fu) + tex[v1c, u1m] * fu) * fv)
        # light from the upper left, darker towards the limb, blue rim light
        L = np.array([-0.45, 0.55, 0.70], np.float32)
        L /= np.linalg.norm(L)
        diffuse = np.clip(xi * L[0] + yi * L[1] + z * L[2], 0, 1)
        shade = (0.38 + 0.82 * diffuse) * (0.72 + 0.28 * np.sqrt(z))
        col = col * shade[:, None]
        rim = ((1 - z) ** 3)[:, None]
        col = col + (np.array(ATMOSPHERE, np.float32) - col) * rim * 0.65
        edge = np.clip((1 - np.sqrt(r2[inside])) * R / 1.5, 0, 1)[:, None]  # anti-aliased rim
        a = edge * alpha
        out[inside] = out[inside] * (1 - a) + col * a
    im.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), (x0, y0))
