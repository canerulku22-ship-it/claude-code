"""Download and cache third-party assets.

Everything is fetched from the npm registry at a pinned version and checked
against the registry's sha512 integrity hash before use:

* Natural Earth 1:50m Admin-0 countries (public domain), as GeoJSON in
  ``@fireflysemantics/geojson``. If you prefer the official download, put
  ``ne_50m_admin_0_countries.zip`` (or the unzipped .shp) into
  ``assets/naturalearth/`` and it is used instead.
* ``flag-icons`` SVG flags (MIT licence).
* Lilita One display font (SIL Open Font License) from ``@fontsource/lilita-one``.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

from .paths import ASSETS

REGISTRY = "https://registry.npmjs.org"

# name, version, {member path in tarball -> destination relative to assets/};
# a member ending in "/" copies every file under that prefix.
PACKAGES = [
    ("@fireflysemantics/geojson", "1.0.1", {
        "package/medium-resolution.geo.json": "naturalearth/ne_50m_admin_0_countries.geojson",
    }),
    ("flag-icons", "7.6.0", {
        "package/flags/4x3/": "flags/4x3/",
        "package/LICENSE": "flags/LICENSE",
    }),
    ("@fontsource/lilita-one", "5.3.0", {
        "package/files/lilita-one-latin-400-normal.woff": "fonts/LilitaOne.woff",
        "package/LICENSE": "fonts/LilitaOne-OFL.txt",
    }),
]

NE_GEOJSON = ASSETS / "naturalearth" / "ne_50m_admin_0_countries.geojson"
FLAGS_DIR = ASSETS / "flags" / "4x3"
FONTS_DIR = ASSETS / "fonts"

# Fallbacks if the downloaded font is unavailable.
SYSTEM_FONTS = [
    "/usr/share/fonts/opentype/inter/Inter-Black.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
EMOJI_FONTS = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/System/Library/Fonts/Apple Color Emoji.ttc",
]


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "country-conquest-assets"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _fetch_package(name: str, version: str, members: dict[str, str]) -> None:
    meta = json.loads(_get(f"{REGISTRY}/{name}/{version}"))
    tarball = _get(meta["dist"]["tarball"])
    algo, _, expected = meta["dist"]["integrity"].partition("-")
    digest = base64.b64encode(hashlib.new(algo, tarball).digest()).decode()
    if digest != expected:
        raise RuntimeError(f"integrity check failed for {name}@{version}")

    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            for src, dst in members.items():
                if src.endswith("/") and member.name.startswith(src):
                    rel = member.name[len(src):]
                    if "/" in rel or rel.startswith("."):
                        continue  # flat directories only; never follow odd paths
                    target = ASSETS / dst / rel
                elif member.name == src:
                    target = ASSETS / dst
                else:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as fh, open(target, "wb") as out:
                    shutil.copyfileobj(fh, out)


def assets_present() -> bool:
    return (natural_earth_path() is not None and FLAGS_DIR.is_dir()
            and (FONTS_DIR / "LilitaOne.woff").exists())


def fetch_assets(force: bool = False) -> None:
    """Download every pinned package that is missing (or all of them with ``force``)."""
    checks = [NE_GEOJSON, FLAGS_DIR / "tr.svg", FONTS_DIR / "LilitaOne.woff"]
    for (name, version, members), check in zip(PACKAGES, checks):
        if check.exists() and not force:
            continue
        print(f"  downloading {name}@{version} ...")
        _fetch_package(name, version, members)
    print(f"  assets ready in {ASSETS}")


def natural_earth_path() -> Path | None:
    """Prefer an official Natural Earth shapefile if the user dropped one in."""
    folder = ASSETS / "naturalearth"
    for candidate in ("ne_50m_admin_0_countries.shp", "ne_50m_admin_0_countries.zip"):
        if (folder / candidate).exists():
            return folder / candidate
    return NE_GEOJSON if NE_GEOJSON.exists() else None


def font_path(name: str = "LilitaOne") -> str:
    for candidate in (FONTS_DIR / f"{name}.woff", FONTS_DIR / f"{name}.ttf", FONTS_DIR / f"{name}.otf"):
        if candidate.exists():
            return str(candidate)
    for candidate in SYSTEM_FONTS:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError("no bold font found; run: python conquest.py fetch-assets")


def emoji_font_path() -> str | None:
    for candidate in EMOJI_FONTS:
        if Path(candidate).exists():
            return candidate
    return None


def flag_svg(iso2: str) -> Path | None:
    path = FLAGS_DIR / f"{iso2.lower()}.svg"
    return path if path.exists() else None
