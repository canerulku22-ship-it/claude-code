"""
Production config for "Seasoned Chicken Spaghetti", a 3D animated cooking film.

Everything recipe-specific lives here: ingredient line-up, step titles, the
optional sauce-simmer temperature graphic and the end title.
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
    ("S3_sear",        135),
    ("S4_sauce",       120),
    ("S5_boil",        105),
    ("S6_toss",        105),
    ("S7_final",       120),
]
BPM = 120
# Music: groove from GROOVE_FROM, a build-up during BUILD_SHOT, the payoff on
# FINAL_SHOT; music ducks under the loudest cooking sounds.
MUSIC_GROOVE_FROM = "S2_ingredients"
MUSIC_BUILD_SHOT = "S6_toss"
MUSIC_FINAL_SHOT = "S7_final"
MUSIC_DUCK = {"S3_sear": 0.32, "S4_sauce": 0.18}

# ------------------------------------------------------------ the recipe ---
# Ingredient line-up (Scene 2), read row by row in a 3 x 3 grid.
INGREDIENTS = [
    ("spaghetti", "SPAGHETTI"),
    ("chicken",   "CHICKEN BREAST"),
    ("seasoning", "SEASONING"),
    ("oil",       "OLIVE OIL"),
    ("garlic",    "GARLIC"),
    ("onion",     "ONION"),
    ("tomato",    "CRUSHED TOMATOES"),
    ("basil",     "BASIL"),
    ("parmesan",  "PARMESAN"),
]

STEP_TITLES = {
    "season": ("01", "SEASON"),
    "sear":   ("02", "SEAR"),
    "sauce":  ("03", "SAUCE"),
    "boil":   ("04", "BOIL"),
    "toss":   ("05", "TOSS"),
}

# Only show a cooking temperature if it is verified, e.g. "180°C".
SEAR_TEMPERATURE_LABEL = None

INTRO_WORDS = ["SEASONED.", "SAUCY.", "TWIRLED."]
FINAL_TEXT = ("SEASONED", "CHICKEN", "SPAGHETTI")

# ----------------------------------------------------------------- brand ---
BRAND = {
    "cream": (255, 244, 224),
    "red":   (214, 48, 34),
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
