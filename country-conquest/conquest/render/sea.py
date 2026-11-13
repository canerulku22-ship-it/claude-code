"""Animated deep-blue sea, composited under the land layer.

Layers (all computed at reduced resolution with numpy, then upscaled):
gradient -> slow swell -> coastal ripples moving out from the shore ->
shallow-water glow along coasts -> soft drop shadow of the land -> vignette.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .maplayer import hex_rgb


def _rgb(hex_value: str) -> np.ndarray:
    return np.array(hex_rgb(hex_value), dtype=np.float32) / 255.0


class Sea:
    def __init__(self, width: int, height: int, style: dict):
        self.W, self.H = width, height
        self.k = width / 1080.0
        self.hw, self.hh = width // 2, height // 2       # ripple resolution
        self.qw, self.qh = width // 4, height // 4       # blur / swell resolution
        top, bottom = _rgb(style["sea_top"]), _rgb(style["sea_bottom"])
        y = np.linspace(0, 1, self.hh, dtype=np.float32)[:, None, None]
        self.gradient = (top * (1 - y) + bottom * y) * np.ones((1, self.hw, 1), np.float32)
        self.ripple = _rgb(style["sea_ripple"])
        self.glow = _rgb(style["coast_glow"])
        qy, qx = np.mgrid[0:self.qh, 0:self.qw].astype(np.float32) / (self.qw)
        self.qx, self.qy = qx * 6.283, qy * 6.283
        # Vignette: darken corners a little to focus the centre.
        vy, vx = np.mgrid[0:self.hh, 0:self.hw].astype(np.float32)
        d = ((vx / self.hw - 0.5) ** 2 * 1.4 + (vy / self.hh - 0.45) ** 2)
        self.vignette = (1.0 - np.clip(d * 0.9, 0, 0.42))[..., None]

    def _swell(self, t: float) -> np.ndarray:
        """Slow interfering sine waves: +-1 brightness field at quarter res."""
        w = (np.sin(self.qx * 2.0 + self.qy * 1.1 + t * 0.9)
             + np.sin(self.qx * -1.3 + self.qy * 2.6 - t * 0.7)
             + 0.6 * np.sin(self.qx * 4.1 - self.qy * 3.2 + t * 1.6))
        return w / 2.6

    def render(self, t: float, land_alpha: Image.Image) -> Image.Image:
        """Sea RGB image for time ``t`` given the land's alpha (output resolution)."""
        aq = land_alpha.resize((self.qw, self.qh), Image.BILINEAR)
        k = self.k
        near = np.asarray(aq.filter(ImageFilter.GaussianBlur(4.0 * k * 2)), np.float32) / 255.0
        far = np.asarray(aq.filter(ImageFilter.GaussianBlur(9.0 * k * 2)), np.float32) / 255.0
        shadow_src = aq.transform(aq.size, Image.AFFINE, (1, 0, 0, 0, 1, -2.0 * k * 2))
        shadow = np.asarray(shadow_src.filter(ImageFilter.GaussianBlur(3.0 * k * 2)), np.float32) / 255.0

        # Quarter-res fields -> half res (bilinear keeps them smooth).
        def up(a: np.ndarray) -> np.ndarray:
            img = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
            return np.asarray(img.resize((self.hw, self.hh), Image.BILINEAR), np.float32) / 255.0

        swell = up(self._swell(t) * 0.5 + 0.5) * 2 - 1
        far_h, near_h, shadow_h = up(far), up(near), up(shadow)

        col = self.gradient * (1.0 + 0.06 * swell[..., None])
        # Coastal ripples: contour lines of the blurred land mask, drifting outward.
        phase = far_h * 8.0 + t * 0.55
        tri = 1.0 - np.abs((phase % 1.0) - 0.5) * 2.0          # 0..1 peak mid-band
        reach = np.clip((far_h - 0.05) * 6.0, 0, 1)             # only near the coast
        lines = np.clip((tri - 0.80) / 0.20, 0, 1) * reach * (far_h < 0.55)
        col = col + (self.ripple - col) * (lines * 0.35)[..., None]
        # Shallow-water glow hugging the coast.
        glow = np.clip(near_h * 2.2, 0, 1) ** 1.5
        col = col + (self.glow - col) * (glow * 0.55)[..., None]
        # Drop shadow of the land onto the water.
        col = col * (1.0 - 0.35 * shadow_h)[..., None]
        col = col * self.vignette
        img = Image.fromarray(np.clip(col * 255, 0, 255).astype(np.uint8), "RGB")
        return img.resize((self.W, self.H), Image.BILINEAR)
