"""
Production config for "Chef Cat's Pepperoni Pizza", a 3D animated cooking
film starring an original cartoon cat chef.

Everything recipe-specific lives here: ingredient line-up, step titles and
the end title.
"""

# ---------------------------------------------------------------- output ---
FPS = 30
RES_X, RES_Y = 1080, 1920           # final delivery, vertical 9:16
# Cycles renders at RES * RENDER_SCALE, post.py upscales to RES and adds the
# crisp 2D motion graphics at native resolution. Use 1.0 on a fast machine.
RENDER_SCALE = 0.6
SAMPLES = 10                        # Cycles samples (adaptive + OIDN denoise)
VIEW_TRANSFORM = "Khronos PBR Neutral"
EXPOSURE = -0.35

# Size of every 2D motion graphic (text, pills, arrows, dots) relative to the
# chicken-burger film. Smaller = more of the frame left to the food.
UI_SCALE = 0.7

# --------------------------------------------------------------- timeline ---
# (scene id, frames). Every length is a multiple of 15 frames so each cut
# lands on a beat of the 120 BPM soundtrack.
SHOTS = [
    ("S1_intro",        60),
    ("S2_ingredients", 105),
    ("S3_stretch",     105),
    ("S4_top",         135),
    ("S5_bake",        105),
    ("S6_slice",       105),
    ("S7_final",       105),
]
BPM = 120
MUSIC_GROOVE_FROM = "S2_ingredients"
MUSIC_BUILD_SHOT = "S6_slice"
MUSIC_FINAL_SHOT = "S7_final"
MUSIC_DUCK = {"S5_bake": 0.2}

# ------------------------------------------------------------ the recipe ---
# Ingredient line-up (Scene 2), read row by row in a 3 x 3 grid.
INGREDIENTS = [
    ("dough",     "PIZZA DOUGH"),
    ("oil",       "OLIVE OIL"),
    ("mozzarella", "MOZZARELLA"),
    ("pepperoni", "PEPPERONI"),
    ("garlic",    "GARLIC"),
    ("parmesan",  "PARMESAN"),
    ("oregano",   "OREGANO"),
    ("tomato",    "CRUSHED TOMATOES"),
    ("basil",     "BASIL"),
]

STEP_TITLES = {
    "stretch": ("01", "STRETCH"),
    "sauce":   ("02", "SAUCE"),
    "top":     ("03", "TOP"),
    "bake":    ("04", "BAKE"),
    "slice":   ("05", "SLICE"),
}

INTRO_WORDS = ["CRISPY.", "CHEESY.", "LOADED."]
FINAL_TEXT = ("CHEF CAT'S", "PEPPERONI", "PIZZA")

# ----------------------------------------------------------------- brand ---
BRAND = {
    "cream": (255, 244, 224),
    "red":   (200, 40, 30),
    "gold":  (245, 178, 46),
    "ink":   (20, 18, 16),
}
FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONT_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def shot_starts():
    """Global (1-based) start frame of every shot."""
    out, f = {}, 1
    for name, n in SHOTS:
        out[name] = f
        f += n
    return out


TOTAL_FRAMES = sum(n for _, n in SHOTS)
