"""Character sprite pipeline: your AI art (or the placeholders) -> clean, normalised cut-outs.

For each character and expression:

1. Find the source image. If characters/<id>/neutral.png (or .jpg/.webp)
   exists, the character uses *your* art; otherwise the procedural
   placeholder set is used. Sets are never mixed, so a character never
   changes art style between expressions.
2. Remove the background with rembg (skipped if the image already has real
   transparency). If rembg is unavailable, a white-background flood fill is
   used instead.
3. Clean the alpha: drop faint haze and small stray islands, and pull in the
   edge by a pixel to remove the white fringe left by the generator.
4. Normalise: scale so the character's *core body* (rows at least 25% as wide
   as the widest row, which ignores raised arms, antennae and hat tips) is the
   same height for everyone (times the per-character `scale` in cast.json),
   then put the feet on a shared baseline with the body centred.

Results are cached in build/sprites/<id>/<expr>.png and only rebuilt when the
source file changes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageFilter

from . import config
from .cast import Cast, Character
from .placeholder_art import ensure_placeholders, placeholder_path

SPRITE_VERSION = "1"            # bump to force every sprite to rebuild
IMAGE_EXTS = (".png", ".webp", ".jpg", ".jpeg")
REMBG_MODEL = os.environ.get("RIZZ_REMBG_MODEL", "isnet-general-use")

_rembg_session = None


# --------------------------------------------------------------------------
# Finding source art
# --------------------------------------------------------------------------
def find_user_art(cid: str, expr: str) -> Path | None:
    """characters/<id>/<expr>.<ext>, accepting aliases such as 'in-love'."""
    folder = config.CHAR_ART_DIR / cid
    if not folder.is_dir():
        return None
    names = {expr} | {alias for alias, canon in config.EXPRESSION_ALIASES.items() if canon == expr}
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() in IMAGE_EXTS and f.stem.lower() in names:
            return f
    return None


def uses_user_art(cid: str) -> bool:
    return find_user_art(cid, "neutral") is not None


def source_for(cid: str, expr: str) -> Path | None:
    """The image an expression is built from, or None if this set lacks it."""
    if uses_user_art(cid):
        return find_user_art(cid, expr)
    p = placeholder_path(cid, expr)
    return p if p.exists() else None


# --------------------------------------------------------------------------
# Background removal + alpha cleanup
# --------------------------------------------------------------------------
def has_real_alpha(img: Image.Image) -> bool:
    if img.mode not in ("RGBA", "LA", "PA"):
        return False
    a = np.asarray(img.getchannel("A"))
    return (a < 250).mean() > 0.01


def remove_background(img: Image.Image) -> Image.Image:
    """Return an RGBA cut-out. Uses rembg, falling back to a white-key flood fill."""
    global _rembg_session
    if has_real_alpha(img):
        return img.convert("RGBA")
    try:
        from rembg import new_session, remove  # imported lazily: heavy and optional

        if _rembg_session is None:
            _rembg_session = new_session(REMBG_MODEL)
        return remove(img.convert("RGB"), session=_rembg_session, post_process_mask=True).convert("RGBA")
    except Exception as e:  # noqa: BLE001 - any rembg failure falls back
        print(f"    rembg unavailable ({e.__class__.__name__}: {e}); using white-background key")
        return white_key(img)


def white_key(img: Image.Image, tol: int = 28) -> Image.Image:
    """Flood-fill near-white pixels connected to the border and make them transparent."""
    from scipy import ndimage

    rgb = np.asarray(img.convert("RGB")).astype(int)
    near_white = (255 - rgb).max(axis=2) < tol
    labels, _ = ndimage.label(near_white)
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))) - {0}
    bg = np.isin(labels, list(border))
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    out = img.convert("RGBA")
    out.putalpha(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1)))
    return out


def clean_alpha(img: Image.Image, defringe: bool = True) -> Image.Image:
    """Remove faint haze and stray islands; optionally shave the outer pixel (white fringe)."""
    from scipy import ndimage

    a = np.asarray(img.getchannel("A")).copy()
    a[a < 12] = 0
    labels, n = ndimage.label(a > 0)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(a), labels, index=range(1, n + 1))
        keep = {i + 1 for i, s in enumerate(sizes) if s >= 0.02 * sizes.max()}
        a[~np.isin(labels, list(keep))] = 0
    m = Image.fromarray(a)
    if defringe:
        m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    out = img.copy()
    out.putalpha(m)
    return out


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------
def body_metrics(img: Image.Image) -> tuple[int, int, float]:
    """(core_top, feet_bottom, centre_x) of the opaque figure, in image pixels."""
    a = np.asarray(img.getchannel("A")) > 40
    rows = a.sum(axis=1)
    if rows.max() == 0:
        raise ValueError("image is fully transparent")
    filled = np.nonzero(rows)[0]
    core = np.nonzero(rows >= 0.25 * rows.max())[0]
    xs = np.arange(a.shape[1])
    centres = [(a[r] * xs).sum() / a[r].sum() for r in core]
    return int(core[0]), int(filled[-1]), float(np.median(centres))


def place_on_canvas(img: Image.Image, k: float, feet: int, cx: float) -> Image.Image:
    """Scale by k and position so `feet` lands on the baseline and `cx` on the centre line."""
    w, h = max(1, round(img.width * k)), max(1, round(img.height * k))
    # Resample in premultiplied alpha so edges don't pick up dark/white halos.
    scaled = img.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")
    dx = round(config.SPRITE_W / 2 - cx * k)
    dy = round(config.SPRITE_BASELINE - feet * k)
    canvas = Image.new("RGBA", (config.SPRITE_W, config.SPRITE_H), (0, 0, 0, 0))
    canvas.paste(scaled, (dx, dy))     # empty canvas: plain copy; paste() clips anything off-canvas
    return canvas


def normalise_transform(img: Image.Image, scale: float) -> tuple[float, int, float]:
    top, feet, cx = body_metrics(img)
    k = config.SPRITE_BODY_H * scale / max(1, feet - top)
    return k, feet, cx


# --------------------------------------------------------------------------
# Build + cache
# --------------------------------------------------------------------------
def sprite_path(cid: str, expr: str) -> Path:
    return config.SPRITE_CACHE / cid / f"{expr}.png"


def _stamp(src: Path, c: Character) -> dict:
    st = src.stat()
    return {"src": str(src), "mtime": st.st_mtime, "size": st.st_size, "scale": c.scale, "v": SPRITE_VERSION}


def build_sprites(cast: Cast, force: bool = False, only: list[str] | None = None,
                  log: Callable[[str], None] = print) -> dict[str, dict[str, Path]]:
    """Make sure every character has processed sprites. Returns {id: {expr: path}}."""
    need_placeholders = [c.id for c in cast.characters.values()
                         if not uses_user_art(c.id) and (not only or c.id in only)]
    if need_placeholders:
        ensure_placeholders(cast, only=need_placeholders, log=log)

    result: dict[str, dict[str, Path]] = {}
    for c in cast.characters.values():
        if only and c.id not in only:
            continue
        user = uses_user_art(c.id)
        out_dir = config.SPRITE_CACHE / c.id
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = out_dir / "manifest.json"
        manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
        result[c.id] = {}

        # Placeholders are drawn pre-registered, so they share the neutral's
        # transform (no jitter on swaps). User art is normalised per image.
        shared_t = None
        for expr in config.ALL_EXPRESSIONS:
            src = source_for(c.id, expr)
            dst = sprite_path(c.id, expr)
            if src is None:
                if dst.exists():
                    dst.unlink()            # art was removed: don't serve a stale sprite
                manifest.pop(expr, None)
                continue
            stamp = _stamp(src, c)
            if not force and manifest.get(expr) == stamp and dst.exists():
                result[c.id][expr] = dst
                continue
            log(f"  processing {c.id}/{expr} from {'your art' if user else 'placeholder'}")
            img = Image.open(src)
            img = clean_alpha(remove_background(img), defringe=user)
            if user:
                t = normalise_transform(img, c.scale)
            else:
                if shared_t is None:
                    neutral = Image.open(source_for(c.id, "neutral"))
                    shared_t = normalise_transform(neutral.convert("RGBA"), c.scale)
                t = shared_t
            place_on_canvas(img, *t).save(dst)
            manifest[expr] = stamp
            result[c.id][expr] = dst
        manifest_file.write_text(json.dumps(manifest, indent=1))

        if user:
            missing = [e for e in config.EXPRESSIONS if e not in result[c.id]]
            if missing:
                log(f"  ! {c.id}: no art yet for {', '.join(missing)} (falls back to neutral)")
    return result


# --------------------------------------------------------------------------
# Runtime access for the renderer
# --------------------------------------------------------------------------
class SpriteBank:
    """Loads processed sprites once and answers 'what image for this expression?'.

    Fallback rules when an expression is missing:
      <expr>_talking -> None (renderer uses a loudness jaw-bob instead)
      talking        -> None (same)
      blink          -> None (no blinking)
      anything else  -> neutral
    """

    def __init__(self, cast: Cast, scale: float = 1.0):
        self.cast = cast
        self.scale = scale              # e.g. 0.5 for --preview renders
        self._cache: dict[tuple[str, str], Image.Image | None] = {}

    def _load(self, cid: str, expr: str) -> Image.Image | None:
        key = (cid, expr)
        if key not in self._cache:
            p = sprite_path(cid, expr)
            if p.exists():
                im = Image.open(p).convert("RGBA")
                if self.scale != 1.0:
                    im = im.resize((round(im.width * self.scale), round(im.height * self.scale)), Image.LANCZOS)
                self._cache[key] = im
            else:
                self._cache[key] = None
        return self._cache[key]

    def get(self, cid: str, expr: str) -> Image.Image | None:
        im = self._load(cid, expr)
        if im is not None:
            return im
        if expr in ("talking", "blink") or expr.endswith("_talking"):
            return None
        return self._load(cid, "neutral")

    def talking_pair(self, cid: str, expr: str) -> tuple[Image.Image, Image.Image | None]:
        """(mouth-closed, mouth-open-or-None) images for a character speaking with `expr`."""
        closed = self.get(cid, expr)
        if expr == "neutral":
            return closed, self.get(cid, "talking")
        return closed, self.get(cid, f"{expr}_talking")
