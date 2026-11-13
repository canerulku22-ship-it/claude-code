"""Land rendering: countries as filled polygons, drawn with Pillow.

Polygons are rasterised at ``supersample``x resolution and box-filtered down,
which gives clean anti-aliased coastlines and borders. All ring vertices are
transformed with one numpy expression per frame; rings that are off screen or
smaller than a pixel are skipped.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from ..world import LOD_TOLERANCES, World
from .camera import Camera


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def shade(rgb, factor: float) -> tuple[int, int, int]:
    """Darken (<1) or lighten (>1, towards white) a colour."""
    if factor <= 1:
        return tuple(int(c * factor) for c in rgb)
    f = factor - 1
    return tuple(int(c + (255 - c) * f) for c in rgb)


class MapRenderer:
    def __init__(self, world: World, width: int, height: int, supersample: int, style: dict):
        self.world = world
        self.W, self.H = width, height
        self.k = width / 1080.0                    # reference px -> output px
        self.ss = max(1, int(supersample))
        self.land = hex_rgb(style["land"])
        self.border = hex_rgb(style["land_border"])
        self.highlight = hex_rgb(style["highlight"])
        self.codes = world.codes

    # ---- geometry --------------------------------------------------------
    def _project(self, cam: Camera, lod_index: int | None = None):
        """Return (lod, screen verts at ss resolution, visible ring indices)."""
        s = self.k * self.ss
        m_per_px = 1.0 / (cam.scale * self.k * self.ss)
        if lod_index is None:
            lod_index = 0
            for i, tol in enumerate(LOD_TOLERANCES):
                if tol <= m_per_px * 0.9:
                    lod_index = i
        lod = self.world.lods[lod_index]
        sc = cam.scale * s
        ox, oy = cam.ax * s, cam.ay * s
        pts = np.empty_like(lod.verts)
        pts[:, 0] = (lod.verts[:, 0] - cam.cx) * sc + ox
        pts[:, 1] = oy - (lod.verts[:, 1] - cam.cy) * sc
        b = lod.bbox
        x0 = (b[:, 0] - cam.cx) * sc + ox
        x1 = (b[:, 2] - cam.cx) * sc + ox
        y0 = oy - (b[:, 3] - cam.cy) * sc
        y1 = oy - (b[:, 1] - cam.cy) * sc
        Wss, Hss = self.W * self.ss, self.H * self.ss
        vis = (x1 >= -4) & (x0 <= Wss + 4) & (y1 >= -4) & (y0 <= Hss + 4) & ((x1 - x0) + (y1 - y0) > 1.2)
        return lod, pts, np.nonzero(vis)[0]

    def _rings(self, lod, pts, idx):
        """Yield (country code, is_hole, flat xy list) for visible rings in draw order."""
        starts, lengths, country, hole = lod.starts, lod.lengths, lod.country, lod.hole
        codes = self.codes
        for r in idx:
            s0 = starts[r]
            yield codes[country[r]], bool(hole[r]), pts[s0:s0 + lengths[r]].ravel().tolist()

    def _down(self, img: Image.Image) -> Image.Image:
        if self.ss == 1:
            return img
        return img.reduce(self.ss)

    # ---- public API -----------------------------------------------------------
    def land_layer(self, cam: Camera, fills: dict[str, tuple] | None = None,
                   owned: set[str] | None = None, empire_outline=(255, 255, 255)):
        """Render the land as an RGBA image (transparent sea).

        ``fills`` maps country code -> RGB (default muted grey); ``owned`` codes
        get darker borders between them and a bright outline around the empire."""
        fills = fills or {}
        owned = owned or set()
        lod, pts, idx = self._project(cam)
        Wss, Hss = self.W * self.ss, self.H * self.ss
        img = Image.new("RGBA", (Wss, Hss), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        rings = list(self._rings(lod, pts, idx))

        # Pass 1: fills in draw order (largest first) so enclaves land on top.
        for code, is_hole, xy in rings:
            if is_hole:
                draw.polygon(xy, fill=(0, 0, 0, 0))
            else:
                draw.polygon(xy, fill=fills.get(code, self.land) + (255,))

        # Pass 2: borders. Owned borders drawn last in a darker team shade.
        bw = max(1, round(1.4 * self.k * self.ss))
        owned_rings = []
        for code, is_hole, xy in rings:
            if code in owned:
                owned_rings.append((code, xy))
                continue
            col = shade(fills[code], 0.72) if code in fills else self.border
            draw.line(xy + xy[:2], fill=col + (255,), width=bw)
        for code, xy in owned_rings:
            draw.line(xy + xy[:2], fill=shade(fills.get(code, self.land), 0.62) + (255,), width=bw)

        out = self._down(img)
        if owned and owned_rings and empire_outline is not None:
            out = self._outline(out, self._mask_from(rings, owned), empire_outline)
        return out

    def _mask_from(self, rings, codes: set[str]) -> Image.Image:
        mask = Image.new("L", (self.W * self.ss, self.H * self.ss), 0)
        draw = ImageDraw.Draw(mask)
        for code, is_hole, xy in rings:
            inside = code in codes
            if is_hole:
                if inside:
                    draw.polygon(xy, fill=0)
            else:
                draw.polygon(xy, fill=255 if inside else 0)
        return self._down(mask)

    def mask(self, cam: Camera, codes) -> Image.Image:
        """Anti-aliased L mask of ``codes`` at output resolution."""
        codes = set(codes)
        lod, pts, idx = self._project(cam)
        return self._mask_from(list(self._rings(lod, pts, idx)), codes)

    def _outline(self, land: Image.Image, mask: Image.Image, colour) -> Image.Image:
        """Bright rim just outside the owned territory (and a soft glow)."""
        size = max(3, int(round(3.2 * self.k)) | 1)
        grown = mask.filter(ImageFilter.MaxFilter(size))
        rim = ImageChops.subtract(grown, mask)
        glow = grown.filter(ImageFilter.GaussianBlur(5 * self.k)).point(lambda v: v * 0.55)
        glow = ImageChops.subtract(glow, mask)
        layer = Image.new("RGBA", land.size, colour + (0,))
        layer.putalpha(ImageChops.lighter(rim, glow))
        return Image.alpha_composite(land, layer)
