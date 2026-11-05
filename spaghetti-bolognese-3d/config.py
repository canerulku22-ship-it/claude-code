"""
Production config for "The Classic Spaghetti Bolognese", a 3D animated
cooking film.

Everything recipe-specific lives here: ingredient line-up, step titles and
the end title.
"""

# ---------------------------------------------------------------- output ---
FPS = 30
RES_X, RES_Y = 1080, 1920           # final delivery, vertical 9:16
# Cycles renders at RES * RENDER_SCALE, post.py upscales to RES and adds the
# crisp 2D motion graphics at native resolution. Use 1.0 on a fast machine.
RENDER_SCALE = 0.6
SAMPLES = 12                        # Cycles samples (adaptive + OIDN denoise)
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
    ("S3_soffritto",   105),
    ("S4_ragu",        135),
    ("S5_boil",         90),
    ("S6_toss",         90),
    ("S7_final",       105),
]
BPM = 120
MUSIC_GROOVE_FROM = "S2_ingredients"
MUSIC_BUILD_SHOT = "S6_toss"
MUSIC_FINAL_SHOT = "S7_final"
MUSIC_DUCK = {"S3_soffritto": 0.28, "S4_ragu": 0.25}

# ------------------------------------------------------------ the recipe ---
# Ingredient line-up (Scene 2), read row by row in a 3 x 3 grid.
INGREDIENTS = [
    ("spaghetti", "SPAGHETTI"),
    ("mince",     "BEEF MINCE"),
    ("onion",     "ONION"),
    ("carrot",    "CARROT"),
    ("celery",    "CELERY"),
    ("garlic",    "GARLIC"),
    ("wine",      "RED WINE"),
    ("tomato",    "CRUSHED TOMATOES"),
    ("parmesan",  "PARMESAN"),
]

STEP_TITLES = {
    "soffritto": ("01", "SOFFRITTO"),
    "brown":     ("02", "BROWN"),
    "simmer":    ("03", "SIMMER"),
    "boil":      ("04", "BOIL"),
    "toss":      ("05", "TOSS"),
}

INTRO_WORDS = ["RICH.", "MEATY.", "SLOW-COOKED."]
FINAL_TEXT = ("THE CLASSIC", "SPAGHETTI", "BOLOGNESE")

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
