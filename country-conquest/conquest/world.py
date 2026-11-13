"""The world map: countries, projected geometry, neighbour graph and team colours.

Geometry is loaded once with geopandas, projected to Miller cylindrical
(familiar "map" look, north up, no rotation when panning) and packed into flat
numpy arrays that the renderer can transform for a whole frame in one go. The
result is cached in ``assets/cache`` so later runs start instantly.
"""
from __future__ import annotations

import math
import pickle
from dataclasses import dataclass, field

import numpy as np

from . import assets
from .paths import CACHE

CACHE_VERSION = 5
MAP_CRS = "ESRI:54003"        # Miller cylindrical
AREA_CRS = "ESRI:54009"       # Mollweide (equal area) for km² figures
LOD_TOLERANCES = (0.0, 3000.0, 12000.0)   # metres; 0 = full Natural Earth detail

# Natural Earth "Country"-type features that are territories rather than
# countries you can battle. They are still drawn, just never picked.
TERRITORIES = {
    "ALA", "GGY", "IMN", "JEY", "HKG", "MAC", "ABW", "CUW", "SXM", "GRL",
    "FLK", "ESH", "ATC", "IOA",
}

# Short on-screen names (Natural Earth's English names are often long/formal).
NAME_OVERRIDES = {
    "USA": "USA", "CHN": "China", "COD": "DR Congo", "COG": "Congo",
    "CAF": "Central African Rep.", "BHS": "Bahamas", "GMB": "Gambia",
    "TLS": "Timor-Leste", "CZE": "Czechia", "CIV": "Ivory Coast",
    "BIH": "Bosnia", "VCT": "St Vincent", "PSE": "Palestine", "ARE": "UAE",
    "FSM": "Micronesia", "DOM": "Dominican Rep.", "GNQ": "Eq. Guinea",
    "TTO": "Trinidad & Tobago", "ATG": "Antigua & Barbuda", "KNA": "St Kitts & Nevis",
    "STP": "São Tomé", "SLB": "Solomon Is.", "MHL": "Marshall Is.",
    "PNG": "Papua New Guinea", "SWZ": "Eswatini", "CPV": "Cape Verde",
    "GBR": "UK", "KOR": "South Korea", "PRK": "North Korea", "LAO": "Laos",
    "RUS": "Russia", "SYR": "Syria", "IRN": "Iran", "VNM": "Vietnam",
    "MDA": "Moldova", "TZA": "Tanzania", "BOL": "Bolivia", "VEN": "Venezuela",
    "BRN": "Brunei", "KOS": "Kosovo", "MKD": "N. Macedonia",
}


@dataclass
class Country:
    code: str                 # ISO-3166 alpha-3 (Natural Earth adm0_a3 when ISO has none)
    iso2: str | None          # for the flag; None when there is no flag
    name: str                 # short display name
    ne_type: str              # Natural Earth "type" field
    area_km2: float
    anchor: tuple[float, float]           # projected point for pins/labels
    core_bbox: tuple[float, float, float, float]  # bbox of the main landmass(es)
    color: tuple[int, int, int]           # main team colour derived from the flag
    neighbours: set[str] = field(default_factory=set)
    sovereign_like: bool = True           # False for dependencies/territories
    palette: list = field(default_factory=list)   # alternative flag colours, best first


@dataclass
class PackedLOD:
    """All rings of all countries for one level of detail, in draw order."""
    verts: np.ndarray        # (N, 2) float64 projected metres
    starts: np.ndarray       # (M,) first vertex of each ring
    lengths: np.ndarray      # (M,) vertex count of each ring
    country: np.ndarray      # (M,) index into World.codes
    hole: np.ndarray         # (M,) bool: interior ring (enclave cut-out)
    bbox: np.ndarray         # (M, 4) minx, miny, maxx, maxy


class World:
    def __init__(self, countries: dict[str, Country], codes: list[str], lods: list[PackedLOD],
                 extent: tuple[float, float, float, float]):
        self.countries = countries
        self.codes = codes                     # draw order: largest area first
        self.index = {c: i for i, c in enumerate(codes)}
        self.lods = lods
        self.extent = extent

    def __getitem__(self, code: str) -> Country:
        return self.countries[code]

    def __contains__(self, code: str) -> bool:
        return code in self.countries

    # ---- rules helpers -------------------------------------------------
    def playable(self, cfg: dict) -> set[str]:
        """Countries the spinner may pick (and that may start a season)."""
        out = set()
        for c in self.countries.values():
            if c.sovereign_like and c.iso2 and c.area_km2 >= cfg.get("min_area_km2", 0):
                out.add(c.code)
        out |= {c for c in cfg.get("extra_playable", []) if c in self.countries}
        out -= set(cfg.get("extra_unplayable", []))
        return out

    def bbox_of(self, codes, core: bool = True) -> tuple[float, float, float, float]:
        boxes = np.array([self.countries[c].core_bbox for c in codes])
        return (boxes[:, 0].min(), boxes[:, 1].min(), boxes[:, 2].max(), boxes[:, 3].max())

    def distance_km(self, a: str, b: str) -> float:
        """Rough distance between two countries' anchors (for fallbacks/sorting)."""
        ax, ay = self.countries[a].anchor
        bx, by = self.countries[b].anchor
        return math.hypot(ax - bx, ay - by) / 1000.0


# ---------------------------------------------------------------------------
# Building / caching
# ---------------------------------------------------------------------------

def load_world(sea_km: float) -> World:
    """Load the cached world, building it from Natural Earth if needed."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"world_v{CACHE_VERSION}_sea{int(sea_km)}.pkl"
    if path.exists():
        with open(path, "rb") as fh:
            return pickle.load(fh)
    world = _build_world(sea_km)
    with open(path, "wb") as fh:
        pickle.dump(world, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return world


def _valid(v) -> bool:
    return isinstance(v, str) and v not in ("-99", "", "None")


def _build_world(sea_km: float) -> World:
    import geopandas as gpd
    import shapely
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.ops import polylabel

    from .render.flags import flag_palette

    src = assets.natural_earth_path()
    if src is None:
        raise FileNotFoundError("Natural Earth data missing; run: python conquest.py fetch-assets")
    print("  building world cache from", src.name, "(one-off, ~20s)")
    gdf = gpd.read_file(src)
    gdf.columns = [c.lower() if c != "geometry" else c for c in gdf.columns]
    gdf = gdf[gdf["adm0_a3"] != "ATA"].reset_index(drop=True)   # no Antarctica

    # Key = Natural Earth adm0_a3, except where that is not the ISO code (PSX -> PSE,
    # SDS -> SSD, ...) and the ISO code is not already used by another feature
    # (Australia's dependencies also carry iso "AUS").
    adm0 = set(gdf["adm0_a3"])
    codes, iso2s = [], []
    for _, row in gdf.iterrows():
        code, iso3 = row["adm0_a3"], row.get("iso_a3_eh")
        if _valid(iso3) and iso3 != code and iso3 not in adm0:
            code = iso3
        codes.append(code)
        iso2 = row.get("iso_a2_eh") if _valid(row.get("iso_a2_eh")) else None
        iso2s.append(iso2 if iso2 and assets.flag_svg(iso2) else None)
    gdf["code"], gdf["iso2"] = codes, iso2s
    gdf = gdf.drop_duplicates("code").reset_index(drop=True)

    proj = gdf.to_crs(MAP_CRS)
    areas = gdf.to_crs(AREA_CRS).area.values / 1e6
    order = np.argsort(-areas)                       # draw big countries first

    def parts(geom):
        return list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]

    # Levels of detail: coverage simplification keeps shared borders matched.
    geoms = proj.geometry.values
    lod_geoms = [geoms]
    for tol in LOD_TOLERANCES[1:]:
        try:
            lod_geoms.append(shapely.coverage_simplify(geoms, tol))
        except Exception:                            # not a perfect coverage: simplify per shape
            lod_geoms.append(shapely.simplify(geoms, tol, preserve_topology=True))

    lods = []
    for lg in lod_geoms:
        verts, starts, lengths, country, hole, bbox = [], [], [], [], [], []
        n = 0
        for draw_idx, gi in enumerate(order):
            geom = lg[gi]
            if geom is None or geom.is_empty:
                continue
            rings = []
            for poly in parts(geom):
                if not isinstance(poly, Polygon) or poly.is_empty:
                    continue
                rings.append((np.asarray(poly.exterior.coords)[:, :2], False))
            for poly in parts(geom):
                if isinstance(poly, Polygon):
                    rings += [(np.asarray(r.coords)[:, :2], True) for r in poly.interiors]
            for coords, is_hole in rings:
                if len(coords) < 4:
                    continue
                verts.append(coords)
                starts.append(n)
                lengths.append(len(coords))
                country.append(draw_idx)
                hole.append(is_hole)
                bbox.append((*coords.min(axis=0), *coords.max(axis=0)))
                n += len(coords)
        lods.append(PackedLOD(np.concatenate(verts), np.array(starts), np.array(lengths),
                              np.array(country), np.array(hole), np.array(bbox)))

    neighbours = _neighbours(gdf, sea_km)

    countries = {}
    for gi in order:
        row = gdf.iloc[gi]
        code = row["code"]
        geom = geoms[gi]
        ps = sorted(parts(geom), key=lambda p: -p.area)
        main = ps[0]
        core = [p for p in ps if p.area >= 0.25 * main.area or p.distance(main) < 400_000]
        core_bbox = shapely.MultiPolygon(core).bounds
        try:
            anchor_pt = polylabel(main, tolerance=2000)
        except Exception:
            anchor_pt = main.representative_point()
        ne_type = row.get("type", "")
        sovereign_like = (ne_type != "Dependency" and code not in TERRITORIES
                          and (_valid(row.get("iso_a3_eh")) or code == "KOS"))
        iso2 = row["iso2"] if isinstance(row["iso2"], str) else None
        countries[code] = Country(
            code=code,
            iso2=iso2,
            name=NAME_OVERRIDES.get(code, row.get("name_en") or row.get("name") or code),
            ne_type=ne_type,
            area_km2=float(areas[gi]),
            anchor=(anchor_pt.x, anchor_pt.y),
            core_bbox=tuple(core_bbox),
            color=flag_palette(iso2)[0] if iso2 else (150, 150, 160),
            neighbours=neighbours.get(code, set()),
            sovereign_like=sovereign_like,
            palette=flag_palette(iso2) if iso2 else [(150, 150, 160)],
        )
    codes_ordered = [gdf.iloc[gi]["code"] for gi in order]
    total = proj.total_bounds
    return World(countries, codes_ordered, lods, tuple(total))


def _neighbours(gdf, sea_km: float) -> dict[str, set[str]]:
    """Countries sharing a border, or within ``sea_km`` across open water.

    A non-touching pair only counts when the shortest gap between them is
    mostly sea, so a buffer never links two countries through a third one."""
    import shapely
    from pyproj import Geod
    from shapely.geometry import LineString
    from shapely.ops import nearest_points

    geod = Geod(ellps="WGS84")
    ll = shapely.simplify(gdf.to_crs("EPSG:4326").geometry.values, 0.01)
    tree = shapely.STRtree(ll)
    codes = list(gdf["code"])
    out: dict[str, set[str]] = {c: set() for c in codes}
    lat_deg = sea_km / 111.0
    for i, g in enumerate(ll):
        minx, miny, maxx, maxy = g.bounds
        lat = min(abs(miny), abs(maxy)) if miny * maxy > 0 else 0.0
        lon_deg = lat_deg / max(math.cos(math.radians(min(lat, 75))), 0.25)
        query = shapely.box(minx - lon_deg, miny - lat_deg, maxx + lon_deg, maxy + lat_deg)
        for j in tree.query(query):
            if j <= i:
                continue
            h = ll[j]
            if g.intersects(h):
                close = True
            else:
                p, q = nearest_points(g, h)
                close = geod.inv(p.x, p.y, q.x, q.y)[2] / 1000.0 <= sea_km
                if close:  # reject gaps that run across a third country's land
                    gap = LineString([p, q])
                    over_land = sum(ll[k].intersection(gap).length for k in tree.query(gap)
                                    if k not in (i, j))
                    close = over_land < 0.2 * gap.length
            if close:
                out[codes[i]].add(codes[j])
                out[codes[j]].add(codes[i])
    return out
